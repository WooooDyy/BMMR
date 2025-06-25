import os
import ast
import json
import asyncio
import aiofiles
import pandas as pd
from tqdm import tqdm
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm_asyncio

async def request_vllm(data, sem, client, model, saved_dataset_path, max_retries=6, timeout=120):
    question = data["question"]
    image = data["image"]
    text_content = {"type": "text", "text": question}
    image_content = []
    for i in range(len(image)):
        image_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image[i]}"}})
    conversations = [{"role": "user", "content": [text_content, *image_content]}]
    id = data["id"]
    retries = 0
    while retries < max_retries:
        try:
            async with sem:
                response = await client.chat.completions.create(
                    model=model,
                    messages=conversations,
                    timeout=timeout,
                    temperature=0 
                )
                answers = [choice.message.content for choice in response.choices]
                # answers = "A"
                data["model_answer"] = answers[0]
                del data["image"]

                async with aiofiles.open(saved_dataset_path, "a") as f:
                    await f.write(json.dumps(data, ensure_ascii=False) + "\n")
                return

        except Exception as e:
            print(f"id: {id} Processing failed, retry {retries + 1}/{max_retries}: {e}")
            retries += 1
            await asyncio.sleep(2 ** retries)  # Exponential backoff strategy
    return

async def main():
    with open('./src/config.json', 'r') as f:
        config = json.load(f)
    
    ip = config["ip"]
    port = config["port"]
    model = config["model"]
    timeout = config["timeout"]
    api_key = config["api_key"]
    concurrency = config["concurrency"]
    test_data_path = config["test_data_path"]
    
    # test_data_path = "./dataset/bmmr.tsv"
    file_name = test_data_path.split("/")[-1].split(".")[0]
    dataset = pd.read_csv(test_data_path, sep='\t', converters={'image': ast.literal_eval}).to_dict('records')
    dataset = dataset[:]
    print("Dataset file loaded:", file_name)

    print("Total number of data: ", len(dataset))

    if port == "":
        base_url = f"http://{ip}/v1"
    else:
        base_url = f"http://{ip}:{port}/v1"
    
    model_name = model.split("/")[-1]
    
    saved_dataset_path = f"./output/{file_name}_{model_name}_greedy.jsonl"
    print("Target file to save: ", saved_dataset_path)
    if not os.path.exists(f"./output"):
        os.makedirs(f"./output")
    # Initialize save file
    async with aiofiles.open(saved_dataset_path, "a") as f:
        await f.write("")

    try:
        async with aiofiles.open(saved_dataset_path, "r") as f:
            handled_data = await f.readlines()
            handled_ids = {json.loads(line)["id"] + "_" + str(json.loads(line)["cot"]) for line in handled_data}
            print("Number of processed data: ", len(handled_ids))
    except FileNotFoundError:
        handled_ids = set()
    
    dataset = [d for d in dataset if d["id"] + "_" + str(d["cot"]) not in handled_ids]
    print("Number of unprocessed data:", len(dataset))

    print("model: ", model)
    print("api_key: ", api_key)
    print("base_url: ", base_url)
    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    semaphore = asyncio.Semaphore(concurrency)
    
    tasks = []
    for data in dataset:
        tasks.append(request_vllm(data, semaphore, client, model, saved_dataset_path, max_retries=6, timeout=timeout))

    with tqdm(total=len(tasks), desc="Processing requests") as pbar:
        for coro in tqdm_asyncio.as_completed(tasks):
            try:
                await coro
            except Exception as e:
                print(f"Task failed: {str(e)}")
            finally:
                pbar.update()
    print("All data processing completed")


if __name__ == "__main__":
    asyncio.run(main())