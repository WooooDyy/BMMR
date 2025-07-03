import re
import json
import pandas as pd
from grade import math_equal
import os

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

def print_results_table(rating_df):
    print_colored("\n📊 Evaluation Results:", "cyan")
    print_separator("-", 50)
    
    # Print header
    columns = rating_df.columns.tolist()
    header = " | ".join([f"{col:>10}" for col in columns])
    print_colored(header, "white")
    print_separator("-", len(header))
    
    # Print data
    for index, row in rating_df.iterrows():
        values = [f"{row[col]:>10.4f}" if isinstance(row[col], float) else f"{row[col]:>10}" for col in columns]
        print(" | ".join(values))
    
    print_separator("-", 50)

def dump(data, f):

    def dump_json(data, pth):
        json.dump(data, open(pth, 'w'), indent=4, ensure_ascii=False)

    def dump_jsonl(data, f):
        lines = [json.dumps(x, ensure_ascii=False) for x in data]
        with open(f, 'w', encoding='utf8') as fout:
            fout.write('\n'.join(lines))
    def dump_xlsx(data, f, **kwargs):
        data.to_excel(f, index=False, engine='xlsxwriter')


    handlers = dict(json=dump_json, jsonl=dump_jsonl, xlsx=dump_xlsx)
    suffix = f.split('.')[-1]
    return handlers[suffix](data, f)

def load_file(file_name):
    if file_name.endswith('.jsonl'):
        with open(file_name, 'r') as f:
            return [json.loads(line) for line in f]
    elif file_name.endswith('.json'):
        with open(file_name, 'r') as f:
            return json.load(f)

def extract_boxed_content(text):
    result = []
    i = 0
    pattern = r'\boxed{'
    len_pattern = len(pattern)
    
    while i < len(text):
        # 搜索模式 \boxed{
        if text[i:i+len_pattern] == pattern:
            start = i + len_pattern
            brace_level = 1
            content = []
            i = start
            
            while i < len(text) and brace_level > 0:
                if text[i] == '{':
                    brace_level += 1
                elif text[i] == '}':
                    brace_level -= 1
                if brace_level > 0:
                    content.append(text[i])
                i += 1
            
            if brace_level == 0:
                result.append(''.join(content))
        else:
            i += 1
    if len(result) == 0:
        return ['No Answer']
    return result
def extract_text(input_string):
    pattern = r'\\text{(.*?)}'
    matches = re.findall(pattern, input_string)
    return matches

def extract_uppercase(s):
    uppercase_letters = [char for char in s if char.isupper()]
    return uppercase_letters




SUBSTITUTIONS = [
    ('an ', ''), ('a ', ''), ('.$', '$'), ('\\$', ''), (r'\ ', ''), ('\%', '%'),
    (' ', ''), ('mbox', 'text'), (',\\text{and}', ','),
    ('\\text{and}', ','), ('\\text{m}', '\\text{}')
]
REMOVED_EXPRESSIONS = [
    'square', 'ways', 'integers', 'dollars', 'mph', 'inches', 'ft',
    'hours', 'km', 'units', '\\ldots', 'sue', 'points', 'feet',
    'minutes', 'digits', 'cents', 'degrees', 'cm', 'gm', 'pounds',
    'meters', 'meals', 'edges', 'students', 'childrentickets', 'multiples',
    '\\text{s}', '\\text{.}', '\\text{\ns}', '\\text{}^2',
    '\\text{}^3', '\\text{\n}', '\\text{}', r'\mathrm{th}',
    r'^\circ', r'^{\circ}', r'\;', r',\!', '{,}', '"', '\\dots'
]

def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def normalize_final_answer(final_answer: str) -> str:
    """Normalize a final answer to a quantitative reasoning question."""
    final_answer = str(final_answer).split('=')[-1]

    for before, after in SUBSTITUTIONS:
        final_answer = final_answer.replace(before, after)
    for expr in REMOVED_EXPRESSIONS:
        final_answer = final_answer.replace(expr, '')

    # Extract answer that is in LaTeX math, is bold,
    # is surrounded by a box, etc.
    final_answer = re.sub(r'(.*?)(\$)(.*?)(\$)(.*)', '$\\3$', final_answer)
    final_answer = re.sub(r'(\\text\{)(.*?)(\})', '\\2', final_answer)
    final_answer = re.sub(r'(\\textbf\{)(.*?)(\})', '\\2', final_answer)
    final_answer = re.sub(r'(\\overline\{)(.*?)(\})', '\\2', final_answer)
    final_answer = re.sub(r'(\\boxed\{)(.*)(\})', '\\2', final_answer)

    # Normalize shorthand TeX:
    # \fracab -> \frac{a}{b}
    # \frac{abc}{bef} -> \frac{abc}{bef}
    # \fracabc -> \frac{a}{b}c
    # \sqrta -> \sqrt{a}
    # \sqrtab -> sqrt{a}b
    final_answer = re.sub(
        r'(frac)([^{])(.)', 'frac{\\2}{\\3}', final_answer)
    final_answer = re.sub(
        r'(sqrt)([^{])', 'sqrt{\\2}', final_answer)
    final_answer = final_answer.replace('$', '')

    # Normalize 100,000 -> 100000
    if final_answer.replace(',', '').isdigit():
        final_answer = final_answer.replace(',', '')

    return final_answer

def open_end_verify(ref, cand):
    gt_ans = ref
    if type(gt_ans) is list:
        gt_ans = gt_ans[0]
    gt_ans = normalize_final_answer(gt_ans)
    if len(gt_ans)==0:
        return False

    ans = extract_boxed_content(cand)[-1]
    ans = normalize_final_answer(ans)
    
    raw_judge = False
    if not raw_judge:
        raw_judge = math_equal(gt_ans,ans)
    
    return raw_judge



def multichoice_verify(ref, cand):
    correct_cnt = 0
    correct_ness = []
    gt_ans = ref
    if len(gt_ans)==0:
        return False
    if type(gt_ans) is str:
        gt_ans = gt_ans.replace("'", "\"")
        gt_ans = json.loads(gt_ans)
    ans = extract_uppercase(extract_boxed_content(cand.split('Answer###')[-1])[0])
    choice_correct_cnt = 0
    if len(gt_ans) == 1 and gt_ans[0].startswith('[') and gt_ans[0].endswith(']'):
        gt_ans = gt_ans[0]
        gt_ans = gt_ans.replace("'", "\"")
        gt_ans = json.loads(gt_ans)
    if len(ans) == len(gt_ans):
        for c in ans:
            if c in gt_ans:
                choice_correct_cnt+=1
        correct_cnt += choice_correct_cnt/len(gt_ans)
    if choice_correct_cnt/len(gt_ans) == 1:
        correct_ness.append(True)
    else:
        correct_ness.append(False)
        
    return correct_ness[0]






def merge_rating(data):
        
    df = pd.DataFrame(data)
    
    df['acc'] = df.apply(lambda x: x['acc'], axis=1)
    
    metrics = ['acc']
    cot_true_df = df[df['cot'] == True]
    cot_true_metrics = {
        'acc': [cot_true_df[metrics].mean().values[0]]
    }
    
    cot_false_df = df[df['cot'] == False]
    cot_false_metrics = {
        'acc': [cot_false_df[metrics].mean().values[0]]
    }

    cot_lang_df = df[df['cot'] == True].groupby('language')[metrics].mean()
    cot_lang_metrics = {
        'acc': cot_lang_df['acc'].values
    }

    df['category_id'] = df['category_id'].apply(lambda x: eval(x) if isinstance(x, str) else x)
    df['category_id'] = df['category_id'].apply(lambda x: x[0][:2])
    
    cot_df = df[df['cot'] == True]
    category_id_df = cot_df.groupby('category_id')[metrics].mean()
    category_id_metrics = {
        'acc': category_id_df['acc'].values
    }
    

    result_dict = {
        'CoT': cot_true_metrics['acc'],
        'no_CoT': cot_false_metrics['acc'], 
        'En': [cot_lang_metrics['acc'][0]],
        'Zh': [cot_lang_metrics['acc'][1]]
    }
    id2name = {"02": "Arts",
               "03": "Soc. Sci.", 
               "04": "Bus.",
               "05": "Nat. Sci.",
               "06": "ICTs",
               "07": "Eng.",
               "08": "Agri.",
               "09": "Health",
               "11": "UnClassified"}

    for cat_id, score in zip(category_id_df.index, category_id_metrics['acc']):
        if cat_id != "11":
            result_dict[f'{id2name[cat_id]}'] = [score]
    result_df = pd.DataFrame(result_dict)

    return result_df


def evaluate(eval_file):
    print_header("Starting Evaluation")
    print_colored(f"📂 Evaluation file: {eval_file}", "blue")
    
    refer_based_metrics_output_file = eval_file.replace('.jsonl', '_reference_based_metrics.jsonl')

    data = load_file(eval_file)
    print_colored(f"📊 Loaded data count: {len(data)}", "green")

    for i, d in enumerate(data):
        ref = d["answer"]
        cand = d["model_answer"]
        task_type = d["task_type"]
        if task_type == None:
            task_type = 'open_end'
        if task_type == "open_end":
            acc_score = open_end_verify(ref, cand)
        elif task_type == "mc":
            acc_score = multichoice_verify(ref, cand)
        d["acc"] = acc_score

    dump(data, refer_based_metrics_output_file)
    print_colored(f"💾 Detailed results saved: {refer_based_metrics_output_file}", "magenta")
    
    rating = merge_rating(data)
    
    print_results_table(rating)
    
    output_file = eval_file.replace('.jsonl', '_final_rating.xlsx')
    dump(rating, output_file)
    print_colored(f"📈 Evaluation report saved: {output_file}", "green")
    
    return rating



if __name__ == '__main__':
    print_header("BMMR Evaluation System")
    
    with open('./src/config.json', 'r') as f:
        config = json.load(f)

    model = config['model']
    test_data_path = config['test_data_path']

    file_name = test_data_path.split("/")[-1].split(".")[0]
    model_name = model.split("/")[-1]
    eval_file = f"./output/{file_name}_{model_name}_greedy.jsonl"
    
    print_colored(f"🔍 Target file: {eval_file}", "blue")
    
    if not os.path.exists(eval_file):
        print_colored(f"❌ Error: File does not exist {eval_file}", "red")
        print_colored("💡 Please run API evaluation first to generate result file", "yellow")
        exit(1)
    
    try:
        evaluate(eval_file)
        print_header("Evaluation Completed")
        print_colored("🎉 All evaluation tasks completed!", "green")
    except Exception as e:
        print_colored(f"❌ Error occurred during evaluation: {str(e)}", "red")
        exit(1)