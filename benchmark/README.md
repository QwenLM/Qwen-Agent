# Code Interpreter Benchmark

## Introduction
To assess LLM's ability to use the Python Code Interpreter for tasks such as mathematical problem solving, data visualization, and other general-purpose tasks such as file handling and web scraping, we have created and open-sourced a benchmark specifically designed for evaluating these capabilities.

### Metrics
The metrics are divided into two parts: code executability and code correctness.
- Code executability: evaluating the ability of the LLM-generated code to be executed.
- Code correctness: evaluating whether the LLM-generated code runs correctly.

### Domain
When evaluating the code executability, we further divide it into three specific domains: `Math`, `Visualization`, `General problem-solving`.
In terms of code correctness, we calculate accuracy rates for `Math` and `Visualization`.

## Results
<table>
    <tr>
        <th colspan="4" align="center">Executable Rate of Generated Code (%)</th>
    </tr>
    <tr>
        <th align="center">Model</th><th align="center">Math↑</th><th align="center">Visualization↑</th><th align="center">General↑</th>
    </tr>
    <tr>
        <td>GPT-4</td><td align="center">91.9</td><td align="center">85.9</td><td align="center">82.8</td>
    </tr>
    <tr>
        <td>GPT-3.5</td><td align="center">89.2</td><td align="center">65.0</td><td align="center">74.1</td>
    </tr>
    <tr>
        <td>LLaMA2-7B-Chat</td>
        <td align="center">41.9</td>
        <td align="center">33.1</td>
        <td align="center">24.1 </td>
    </tr>
    <tr>
        <td>LLaMA2-13B-Chat</td>
        <td align="center">50.0</td>
        <td align="center">40.5</td>
        <td align="center">48.3 </td>
    </tr>
    <tr>
        <td>CodeLLaMA-7B-Instruct</td>
        <td align="center">85.1</td>
        <td align="center">54.0</td>
        <td align="center">70.7 </td>
    </tr>
    <tr>
        <td>CodeLLaMA-13B-Instruct</td>
        <td align="center">93.2</td>
        <td align="center">55.8</td>
        <td align="center">74.1 </td>
    </tr>
    <tr>
        <td>InternLM-7B-Chat-v1.1</td>
        <td align="center">78.4</td>
        <td align="center">44.2</td>
        <td align="center">62.1 </td>
    </tr>
    <tr>
        <td>InternLM-20B-Chat</td>
        <td align="center">70.3</td>
        <td align="center">44.2</td>
        <td align="center">65.5 </td>
    </tr>
    <tr>
        <td>Qwen-7B-Chat</td>
        <td align="center">82.4</td>
        <td align="center">64.4</td>
        <td align="center">67.2 </td>
    </tr>
    <tr>
        <td>Qwen-14B-Chat</td>
        <td align="center">89.2</td>
        <td align="center">84.1</td>
        <td align="center">65.5</td>
    </tr>
</table>

<table>
    <tr>
        <th colspan="4" align="center">Accuracy of Code Execution Results (%)</th>
    </tr>
    <tr>
        <th align="center">Model</th><th align="center">Math↑</th><th align="center">Visualization-Hard↑</th><th align="center">Visualization-Easy↑</th>
    </tr>
    <tr>
        <td>GPT-4</td><td align="center">82.8</td><td align="center">66.7</td><td align="center">60.8</td>
    </tr>
    <tr>
        <td>GPT-3.5</td><td align="center">47.3</td><td align="center">33.3</td><td align="center">55.7</td>
    </tr>
    <tr>
        <td>LLaMA2-7B-Chat</td>
        <td align="center">3.9</td>
        <td align="center">14.3</td>
        <td align="center">39.2 </td>
    </tr>
    <tr>
        <td>LLaMA2-13B-Chat</td>
        <td align="center">8.3</td>
        <td align="center">8.3</td>
        <td align="center">40.5 </td>
    </tr>
    <tr>
        <td>CodeLLaMA-7B-Instruct</td>
        <td align="center">14.3</td>
        <td align="center">26.2</td>
        <td align="center">60.8 </td>
    </tr>
    <tr>
        <td>CodeLLaMA-13B-Instruct</td>
        <td align="center">28.2</td>
        <td align="center">27.4</td>
        <td align="center">62.0 </td>
    </tr>
    <tr>
        <td>InternLM-7B-Chat-v1.1</td>
        <td align="center">28.5</td>
        <td align="center">4.8</td>
        <td align="center">40.5 </td>
    </tr>
    <tr>
        <td>InternLM-20B-Chat</td>
        <td align="center">34.6</td>
        <td align="center">21.4</td>
        <td align="center">45.6 </td>
    </tr>
    <tr>
        <td>Qwen-7B-Chat</td>
        <td align="center">41.9</td>
        <td align="center">40.5</td>
        <td align="center">54.4 </td>
    </tr>
    <tr>
        <td>Qwen-14B-Chat</td>
        <td align="center">58.4</td>
        <td align="center">53.6</td>
        <td align="center">59.5</td>
    </tr>
</table>


## Usage

### Installation

```shell
git clone https://github.com/QwenLM/Qwen-Agent.git
cd benchmark
pip install -r requirements.txt
```

### Dataset Download
```shell
cd benchmark
wget https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/benchmark_code_interpreter_data.zip
unzip benchmark_code_interpreter_data.zip
mkdir eval_data
mv eval_code_interpreter_v1.jsonl eval_data/
```

### Evaluation
To reproduce the comprehensive results of benchmark, you can run the following script:

```Shell
python inference_and_execute.py --model {model_name}
```

{model_name}:
- qwen-1.8b-chat
- qwen-7b-chat
- qwen-14b-chat
- llama-2-7b-chat
- llama-2-13b-chat
- codellama-7b-instruct
- codellama-13b-instruct
- internlm-7b-chat-1.1
- internlm-20b-chat

The benchmark will run the test cases and generate the performance results. The results will be saved in the `output_data` directory.

**Notes**:
Please install `simhei.ttf` font for proper display in matplotlib when evaluating visualization task. You can do this by preparing `simhei.ttf` (which can be found on any Windows PC) and then running the following code snippet:
```python
import os
import matplotlib
target_font_path = os.path.join(
    os.path.abspath(
        os.path.join(matplotlib.matplotlib_fname(), os.path.pardir)),
        'fonts', 'ttf', 'simhei.ttf')
os.system(f'cp simhei.ttf {target_font_path}')
font_list_cache = os.path.join(matplotlib.get_cachedir(), 'fontlist-*.json')
os.system(f'rm -f {font_list_cache}')
```

#### Code Executable Rate
```Shell
python inference_and_execute.py --task {task_name} --model {model_name}
```

{task_name}:
- `all_ci`: All tasks including Math / Visualization / General problem-solving
- `visualization`: Visualization task
- `math`: Math task
- `general`: General problem-solving task


#### Code Correctness Rate
```Shell
python inference_and_execute.py --task {task_name} --model {model_name}
```

{task_name}:
- `visualization`: Visualization task
- `gsm8k`: Math task


## Configuration
The inference_and_exec.py file contains the following configurable options:

- `--model`: The model to test which can be one of `qwen-14b-chat`, `qwen-7b-chat`, `qwen-1.8b-chat`, `qwen-7b-chat`, `llama-2-7b-chat`, `llama-2-13b-chat`, `codellama-7b-instruct`, `codellama-13b-instruct`, `internlm-7b-chat-1.1`, `internlm-20b-chat`.
- `--task`: The test task which can be one of `all`, `all_ci`, `visualization`, `math`, `general`, `gsm8k`.
- `--output-path`: The path for saving evaluation result.
- `--input-path`: The path for placing evaluation data.
- `--output-fname`: The file name for evaluation result.
- `--input-fname`: The file name for evaluation data.
- `--force`: Force generation and will overwrite the cached results.
- `--eval-only`: Only calculate evaluation metrics without re-inference.
- `--eval-code-exec-only`: Only evaluate code executable rate
- `--gen-exec-only`: Only generate and execuate code without calculating evaluation metrics.
- `--gen-only`: Only generate without execuating code and calculating evaluation metrics.
