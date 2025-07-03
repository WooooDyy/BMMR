import os
import ast
import json
import asyncio
import aiofiles
import pandas as pd
from tqdm import tqdm
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm_asyncio

# Add color output functions
def print_colored(text, color="white"):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")

def print_separator(char="=", length=60):
    print(char * length)

def print_header(title):
    print_separator()
    print_colored(f"  {title}", "cyan")
    print_separator()

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
                    temperature=0,
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
    
    base_url = config["base_url"]
    model = config["model"]
    timeout = config["timeout"]
    api_key = config["api_key"]
    concurrency = config["concurrency"]
    test_data_path = config["test_data_path"]
    
    print_header("BMMR API Evaluation Started")
    
    # test_data_path = "./dataset/bmmr.tsv"
    file_name = test_data_path.split("/")[-1].split(".")[0]
    dataset = pd.read_csv(test_data_path, sep='\t', converters={'image': ast.literal_eval}).to_dict('records')
    dataset = dataset[:]
    print_colored(f"✓ Dataset file loaded: {file_name}", "green")

    print_colored(f"📊 Total data count: {len(dataset)}", "blue")

    
    
    model_name = model.split("/")[-1]
    
    saved_dataset_path = f"./output/{file_name}_{model_name}_greedy.jsonl"
    print_colored(f"💾 Output file path: {saved_dataset_path}", "magenta")
    
    if not os.path.exists(f"./output"):
        os.makedirs(f"./output")
        print_colored("✓ Output directory created", "green")
    
    # Initialize save file
    async with aiofiles.open(saved_dataset_path, "a") as f:
        await f.write("")

    try:
        async with aiofiles.open(saved_dataset_path, "r") as f:
            handled_data = await f.readlines()
            handled_ids = {json.loads(line)["id"] + "_" + str(json.loads(line)["cot"]) for line in handled_data}
            print_colored(f"✓ Processed data: {len(handled_ids)}", "green")
    except FileNotFoundError:
        handled_ids = set()
        print_colored("ℹ️ No processed data file found, starting from scratch", "yellow")
    
    dataset = [d for d in dataset if d["id"] + "_" + str(d["cot"]) not in handled_ids]
    print_colored(f"⏳ Data to be processed: {len(dataset)}", "yellow")

    print_separator("-", 40)
    print_colored(f"🤖 Model: {model}", "cyan")
    print_colored(f"🔗 API URL: {base_url}", "cyan")
    print_colored(f"🔑 API Key: {api_key[:10]}...", "cyan")
    print_colored(f"⚡ Concurrency: {concurrency}", "cyan")
    print_colored(f"⏱️ Timeout: {timeout}s", "cyan")
    print_separator("-", 40)
    
    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    semaphore = asyncio.Semaphore(concurrency)
    
    tasks = []
    for data in dataset:
        tasks.append(request_vllm(data, semaphore, client, model, saved_dataset_path, max_retries=6, timeout=timeout))

    print_colored("🚀 Starting API request processing...", "green")
    with tqdm(total=len(tasks), desc="Processing requests") as pbar:
        for coro in tqdm_asyncio.as_completed(tasks):
            try:
                await coro
            except Exception as e:
                print_colored(f"❌ Task failed: {str(e)}", "red")
            finally:
                pbar.update()
    
    print_header("API Evaluation Completed")
    print_colored("✅ All data processing completed!", "green")
    print_colored(f"📄 Results saved to: {saved_dataset_path}", "blue")

if __name__ == "__main__":
    asyncio.run(main())