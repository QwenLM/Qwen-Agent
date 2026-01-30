## 🛠️ Quick Start

This domain can be run as part of the unified benchmark or independently.

### Step 1: Install Dependencies

**Note:** The unified environment is set up in the project root directory.

```bash
# Navigate to project root (if you're in travelplanning/)
cd ..

# Create a new conda environment (recommended Python 3.10)
conda create -n deepplanning python=3.10 -y

# Activate the environment
conda activate deepplanning

# Install all required packages from the unified requirements.txt
pip install -r requirements.txt

# Return to travelplanning directory
cd travelplanning
```

### Step 2: Download Data Files

**Required Files:**
- `database/database_zh.zip` - Chinese database
- `database/database_en.zip` - English database

**Download from:** [HuggingFace Dataset](https://huggingface.co/datasets/Qwen/DeepPlanning)

First, download the required data files from HuggingFace and place them in the project:

- In `travelplanning/database/`: put `database_zh.zip` and `database_en.zip`.



### Step 3: Extract Database Files

After downloading, extract the compressed travel databases:

```bash
# Navigate to the database directory
cd database

# Extract both language databases
unzip database_zh.zip    # Chinese database (flights, hotels, restaurants, attractions)
unzip database_en.zip    # English database

# Return to travelplanning directory
cd ..
```


### Step 4: Configure Model Settings

**Note:** Model configuration is shared across all domains and located in the project root.

Edit `models_config.json` in the **project root directory** (one level up from travelplanning/):

```json
{
  "models": {
    "qwen-plus": {
      "model_name": "qwen-plus",
      "model_type": "openai",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key_env": "DASHSCOPE_API_KEY"
    },
    "gpt-4o-2024-11-20": {
      "model_name": "gpt-4o-2024-11-20",
      "model_type": "openai",
      "base_url": "https://api.openai.com/v1/models",
      "api_key_env": "OPENAI_API_KEY"
    }
  }
}
```

**Important Note about `qwen-plus`:**
- The `qwen-plus` configuration is **required** because it's used by default in the conversion stage (`evaluation/convert_report.py`) to parse and format agent-generated travel plans.
- If you want to use a different model for conversion, you can modify the `conversion_model` variable in `evaluation/convert_report.py`.

**Supported Model Types:**
- `openai`: OpenAI and compatible models (GPT-4, Qwen, DeepSeek, etc.)

### Step 5: Set API Keys

**Note:** API keys are configured in the project root directory.

Create a `.env` file in the **project root directory** or set environment variables:

```bash
# Option 1: Create .env file in project root
# Navigate to project root
cd ..
cp .env.example .env
# Edit .env and add your API keys

# Option 2: Set environment variables directly
export DASHSCOPE_API_KEY="your_dashscope_api_key"
export OPENAI_API_KEY="your_openai_api_key"
```

### Step 6: Run the Benchmark

#### Using Shell Script with Environment Variables (Recommended)

Set environment variables to configure the run:

```bash
BENCHMARK_MODEL="qwen-plus" \
BENCHMARK_LANGUAGE="" \
BENCHMARK_WORKERS=10 \
BENCHMARK_MAX_LLM_CALLS=400 \
BENCHMARK_START_FROM="inference" \
BENCHMARK_OUTPUT_DIR="" \
bash run.sh
```

**Available Environment Variables:**
- `BENCHMARK_MODEL`: Model name from models_config.json
- `BENCHMARK_LANGUAGE`: Language version (zh, en, or empty for both)
- `BENCHMARK_WORKERS`: Number of parallel workers
- `BENCHMARK_MAX_LLM_CALLS`: Maximum LLM calls per task
- `BENCHMARK_START_FROM`: Start point (inference, conversion, evaluation)
- `BENCHMARK_OUTPUT_DIR`: Custom output directory
- `BENCHMARK_VERBOSE`: Enable verbose output (true/false)
- `BENCHMARK_DEBUG`: Enable debug mode (true/false)


**Or edit default values in `run.sh` for permanent changes:**

Find and modify these lines in `run.sh` (change the values after `:-`):

```bash
MODEL="${BENCHMARK_MODEL:-${TRAVEL_AGENT_MODEL:-qwen-plus}}"  # Change qwen-plus
LANGUAGE="${BENCHMARK_LANGUAGE:-zh}"                           # Change zh
WORKERS="${BENCHMARK_WORKERS:-40}"                            # Change 40
MAX_LLM_CALLS="${BENCHMARK_MAX_LLM_CALLS:-400}"              # Change 400
START_FROM="${BENCHMARK_START_FROM:-inference}"               # Change inference
OUTPUT_DIR="${BENCHMARK_OUTPUT_DIR:-}"                        # Set custom path
```

Then simply run:

```bash
bash run.sh
```

**Smart Caching & Resume Functionality:**

When using `run.sh` with `START_FROM="inference"`, the script automatically:

1. **Checks existing results** for the same model name to avoid redundant work
2. **Scans the `reports/` folder** first to find missing report files (e.g., `id_0_report.txt`, `id_1_report.txt`, etc.)
3. **Scans the `converted_plans/` folder** to find missing converted plan files (e.g., `id_0_converted.json`, `id_1_converted.json`, etc.)
4. **Identifies missing task IDs** (out of 120 total tasks: IDs 0-119)
5. **Automatically determines the starting step:**
   - If reports are complete but converted plans are missing → starts from `conversion`
   - If reports are missing → starts from `inference`
   - If both are complete → skips the model entirely

This allows you to safely interrupt and resume long-running evaluations without losing progress.

## 🔄 Understanding the Pipeline

The benchmark runs in three stages:

#### Stage 1: Inference (Agent Planning)
**What it does:** 
- Loads travel planning tasks from `data/travelplanning_query_{lang}.json`
- Calls the LLM agent to generate travel plans
- Agent uses tools to query database (flights, hotels, restaurants, attractions)
- Saves agent trajectories and execution logs
- Generates human-readable reports following the required format

**Output:**
```
results/{model}_{lang}/
├── trajectories/     # Agent execution traces
│   └── id_0_trajectory.json
└── reports/          # Human-readable reports
    └── id_0_report.txt
```

#### Stage 2: Conversion (Plan Parsing)
**What it does:**
- Uses an LLM (default: `qwen-plus`, configurable) to convert plans
- **Parses Markdown-formatted travel plans** from agent output
- **Converts to standardized JSON format** for automated evaluation
- Stores converted plans in `converted_plans/` directory
- Validates plan structure and completeness

**Why conversion is needed:** The agent generates human-readable plans in Markdown format, but the evaluation code requires structured JSON data to automatically score compliance with constraints and calculate metrics.

**Output:**
```
results/{model}_{lang}/
├── converted_plans/  # Structured travel plans
│   └── id_0_converted.json
```


#### Stage 3: Evaluation
**What it does:**
- Checks delivery rate (was a plan generated?)
- Evaluates commonsense score (8 dimensions)
- Validates personalized constraints
- Calculates final scores

**Output:**
```
results/{model}_{lang}/
└── evaluation/
    ├── evaluation_summary.json      # Overall metrics and statistics
    ├── id_0_score.json              # Individual task scores
    ├── id_1_score.json
    └── ...                           # One score file per task
```

## 📊 Viewing Results

#### Overall Statistics

```bash
cat results/{model}_{lang}/evaluation/evaluation_summary.json
```

**Example Output:**
```json
{
  "total_test_samples": 120,
  "evaluation_success_count": 115,
  "metrics": {
    "delivery_rate": 0.958,
    "commonsense_score": 0.875,
    "personalized_score": 0.742,
    "composite_score": 0.809,
    "case_acc": 0.683
  }
}
```

#### Per-Task Details

```bash
# View detailed score for a specific task
cat results/{model}_{lang}/evaluation/id_0_score.json


# View human-readable report for a specific task
cat results/{model}_{lang}/reports/id_0_report.txt
```

#### Error Analysis

The summary includes error statistics showing common failure patterns:

```json
"error_statistics": [
  {
    "rank": 1,
    "error_type": "[Hard] train_seat_status",
    "count": 15,
    "affected_samples": ["0", "12", "25", ...]
  }
]
```