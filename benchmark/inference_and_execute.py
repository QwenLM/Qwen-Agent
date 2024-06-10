import argparse
import json
import logging
import os
from parser import ReActParser

import prettytable
import tqdm
from code_interpreter import code_interpreter
from config import get_model, get_react_parser, get_react_prompt, model_path_map
from datasets import load_dataset
from metrics.code_execution import eval_code_execution_rate
from metrics.gsm8k import eval_gsm8k_acc, is_correct
from metrics.visualization import eval_visualization_acc
from utils.code_utils import replace_upload_fname
from utils.data_utils import load_jsonl

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO,
)

WORK_DIR = os.getenv('CODE_INTERPRETER_WORK_DIR', '/tmp/workspace')
os.makedirs(WORK_DIR, exist_ok=True)
os.system(f'cp -r upload_file_clean {WORK_DIR}/upload_file')
os.system('cp -r upload_file_clean ./upload_file')

global_eval_result = {
    'code_executability': {
        'math': None,
        'visualization': None,
        'general': None,
    },
    'code_correctness': {
        'math': None,
        'visualization-hard': None,
        'visualization-easy': None,
    }
}


def llm_with_plugin(args, query, item=None, exec_limit=3):
    exec_count = 0

    # Build ReAct prompt
    upload_fname_list = item['input_file_path'] if item and 'input_file_path' in item else []
    lang = item['lang'] if item and 'lang' in item else 'en'
    react_prompt_obj = get_react_prompt(args.model, query, lang, upload_fname_list)
    planning_prompt = react_prompt_obj.build_prompt()

    # Execute the code when providing the first action in the query
    if '<|im_start|>' in query:
        _, prepend_code, __ = ReActParser().parse_latest_plugin_call(query)
        prepend_code = replace_upload_fname(prepend_code, upload_fname_list)
        call_tool(_, [prepend_code], clear=(exec_count == 0))
        exec_count += 1
        exec_limit += 1

    # Inference and execute
    text = ''
    while exec_count < exec_limit:
        stop_words_list = react_prompt_obj.get_stop_words_list()
        output = text_completion(args.llm, planning_prompt + text, stop_words=stop_words_list)

        if args.gen_only:
            text += output
            break

        react_parser = get_react_parser(args.model)
        action, action_input, output = react_parser.parse_latest_plugin_call(output)
        if action:
            action_input = replace_upload_fname(action_input, upload_fname_list)
            observation = call_tool(action, [action_input], clear=(exec_count == 0))
            output += react_prompt_obj.build_observation(observation)
            text += output
            exec_count += 1
            if 'error:' in observation or 'Traceback' in observation:
                break
        else:
            text += output
            break
    return text


def text_completion(llm, input_text, stop_words=[]):
    logging.info('Generating'.center(60, '='))
    logging.info('Input'.center(60, '-'))
    logging.info(input_text)

    output = llm.generate(input_text, stop_words)

    logging.info('Output'.center(60, '-'))
    logging.info(output)
    return output


def call_tool(plugin_name, plugin_args_list, clear=False):
    # Relax constraints on plugin name.
    logging.info('Call code interpreter'.center(60, '='))
    obs = code_interpreter(plugin_args_list, clear=clear)
    logging.info(obs)
    return obs


def process_code_interpreter(item, writer):
    query = item['query']
    exec_limit = 3 if 'visualization' in item['tags'] else 1
    response = llm_with_plugin(args=args, query=query, item=item, exec_limit=exec_limit)
    item['gen'] = response

    writer.write(json.dumps(item, ensure_ascii=False) + '\n')
    writer.flush()


def process_gsm8k(doc, writer):
    context = doc['question']
    completion = llm_with_plugin(args=args, query=context)
    acc = is_correct(completion, doc['answer'])
    doc['completion'] = completion
    doc['acc'] = acc

    writer.write(json.dumps(doc, ensure_ascii=False) + '\n')
    writer.flush()


def sequential_processing(args, data_list, process_func, writer):
    for item in tqdm.tqdm(data_list):
        process_func(item, writer)


process_func_map = {'gsm8k': process_gsm8k, 'visualization': process_code_interpreter}


def gather_eval_result(model_name):
    for metric in global_eval_result:
        logging.info(metric)
        table = prettytable.PrettyTable()
        table.field_names = ['model'] + list(global_eval_result[metric].keys())
        row_data = [model_name]
        for item in global_eval_result[metric].values():
            item = str(item) if not item else str(round(item, 2))
            row_data.append(item)
        table.add_row(row_data)
        logging.info('\n' + str(table))


def eval_metrics(args, test_set, full_output_fname):
    # metrics
    assert os.path.exists(full_output_fname), f'Not Found File {full_output_fname}.'
    inference_res = load_jsonl(full_output_fname)
    assert len(inference_res) == len(test_set), f'There are still {len(test_set)-len(inference_res)} cases left.'

    abs_output_fname = os.path.join(os.path.dirname(os.path.abspath(__file__)), full_output_fname)
    if args.task == 'gsm8k':
        math_code_correctness = eval_gsm8k_acc(abs_output_fname)
        global_eval_result['code_correctness'].update(math_code_correctness)
    else:
        code_executability = eval_code_execution_rate(abs_output_fname, args.task, args.model)
        global_eval_result['code_executability'].update(code_executability)
        if args.task in ['all_ci', 'visualization'] and not args.eval_code_exec_only:
            visualization_code_correctness = eval_visualization_acc(abs_output_fname, args.model, args.vis_judger)
            global_eval_result['code_correctness'].update(visualization_code_correctness)


def main(args):
    current_dir = os.getcwd()
    os.makedirs(args.output_path, exist_ok=True)
    full_output_fname = os.path.join(args.output_path, (args.output_fname or f'{args.task}_{args.model}_res.jsonl'))

    if not os.path.exists(full_output_fname):
        with open(full_output_fname, 'w'):
            logging.info(f'Create file {full_output_fname} done.')

    # build data
    if args.task == 'gsm8k':
        dataset = load_dataset('gsm8k', 'main')
        test_set = dataset['test']
    else:
        eval_data_path = os.path.join(args.input_path, args.input_fname)
        test_set = [item for item in load_jsonl(eval_data_path) if args.task in item['tags']]
    logging.info(f'Test set: {len(test_set)}')

    if args.eval_only:
        eval_metrics(args, test_set, full_output_fname)
    else:
        key = 'question' if args.task == 'gsm8k' else 'query'
        cache_question = [item[key] for item in load_jsonl(full_output_fname)] if not args.force else []
        data_list = [item for item in test_set if item[key] not in cache_question]
        logging.info(f'Left cases: {len(data_list)}')

        # inference
        writer_mode = 'w' if args.force else 'a'
        f_output = open(full_output_fname, writer_mode, encoding='utf-8')
        process_func = process_func_map.get(args.task, process_code_interpreter)
        sequential_processing(args, data_list, process_func, f_output)
        f_output.close()

        # evaluate
        if not args.gen_exec_only:
            eval_metrics(args, test_set, full_output_fname)

    os.chdir(current_dir)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='qwen-14b-chat', choices=list(model_path_map.keys()))
    parser.add_argument('--task', type=str, default='all', choices=['all', 'gsm8k', 'visualization', 'general'])
    parser.add_argument('--output-path', type=str, default='output_data')
    parser.add_argument('--input-path', type=str, default='eval_data')
    parser.add_argument('-o', '--output-fname', type=str, default='')
    parser.add_argument('-i', '--input-fname', type=str, default='eval_code_interpreter_v1.jsonl')
    parser.add_argument('-f', '--force', action='store_true', default=False)
    parser.add_argument('--eval-only', action='store_true', default=False)
    parser.add_argument('--eval-code-exec-only', action='store_true', default=False)
    parser.add_argument('--gen-exec-only', action='store_true', default=False)
    parser.add_argument('--gen-only', action='store_true', default=False)
    parser.add_argument('--vis-judger',
                        type=str,
                        default="'gpt-4-vision-preview'",
                        choices=['gpt-4-vision-preview', 'qwen-vl-chat', 'qwen-vl-plus'])
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    if not args.eval_only:
        args.llm = get_model(args.model)
        logging.info(f'Init {args.model} done.')

    if args.task == 'all':
        for key in ['gsm8k', 'visualization', 'general']:
            args.task = key
            main(args)
    else:
        main(args)
    gather_eval_result(args.model)
