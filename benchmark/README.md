## Code Interpreter Benchmark

### Introduction
The benchmark is blabla.

### Data
{table}

### Installation
```shell
git clone <repository_url>
pip install -r requirements.txt
mkdir <your workspace>/upload_file
```

### Usage
1. Download the dataset
```shell
wget <data_url>
```
2. Evaluate by executing the following command:
```Shell
export CODE_INTERPRETER_WORK_DIR="{your workspace}"
python inference_and_execute.py --task all_ci --model {model_name} -f
python inference_and_execute.py --task gsm8k --model {model_name} -f
```
3. The benchmark will run the test cases and generate the performance results. The results will be saved in the `output_data` directory.

#### Code Execute Rate
```Shell
python inference_and_execute.py --task {task_name} --model {model_name} -f
```
Task:
- all_ci: all tasks for Math/Visualization/General
- ci_plot/visualization: Visualization task
- ci_math_code: Math task

Model:
- gpt-4
- gpt-3.5-turbo-0613
- qwen-14b-chat
- qwen-7b-chat-1.1
- qwen-1.8b-chat
- qwen-7b-chat
- llama-2-7b-chat
- llama-2-13b-chat
- codellama-7b-instruct
- codellama-13b-instruct
- internlm

#### Code Correctness Rate
```Shell
python inference_and_execute.py --task {task_name} --model {model_name} -f
```

Task:
- ci_plot/visualization: Visualization task
- GSM8K: Math task

Model:
- gpt-4
- gpt-3.5-turbo-0613
- qwen-14b-chat
- qwen-7b-chat-1.1
- qwen-1.8b-chat
- qwen-7b-chat
- llama-2-7b-chat
- llama-2-13b-chat
- codellama-7b-instruct
- codellama-13b-instruct
- internlm

### Configuration
The inference_and_exec.py file contains the following configurable options:

`--model`: The model to test which can be one of 'gpt-4', 'gpt-3.5-turbo-0613', 'qwen-14b-chat', 'qwen-7b-chat-1.1', 'qwen-1.8b-chat', 'qwen-7b-chat', 'llama-2-7b-chat', 'llama-2-13b-chat', 'codellama-7b-instruct', 'codellama-13b-instruct', 'internlm'.
`--task`: The test task which one can be one of 'gsm8k', 'visualization', 'all_ci', 'ci_plot', 'ci_math_code', 'ci_open_questions'.
`--output-path`: The path for saving evaluation result.
`--input-path`: The path for placing evaluation data.
`--output-fname`: The file name for evaluation result.
`--input-fname`: The file name for evaluation data.
`--force`: Force generation and will overwrite the cached results.
`--eval-only`: Only calculate evaluation metrics without re-inference.
`--eval-code-exec-only`:
`--gen-exec-only`: Only generate and execuate code without calculating evaluation metrics.
`--gen-only`: Only generate without execuating code and calculating evaluation metrics.


### Results
{table}
