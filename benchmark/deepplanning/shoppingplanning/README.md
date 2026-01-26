## 🛠️ Quick Start

This domain can be run as part of the unified benchmark or independently.

### Step 1: Install Dependencies

**Note:** The unified environment is set up in the project root directory.

```bash
# Navigate to project root (if you're in shoppingplanning/)
cd ..

# Create a new conda environment (recommended Python 3.10)
conda create -n deepplanning python=3.10 -y

# Activate the environment
conda activate deepplanning

# Install all required packages from the unified requirements.txt
pip install -r requirements.txt

# Return to shoppingplanning directory
cd shoppingplanning
```

### Step 2: Download Data Files

**Required Files:**
- `database_zip/database_level1.tar.gz` - Level 1 shopping database
- `database_zip/database_level2.tar.gz` - Level 2 shopping database
- `database_zip/database_level3.tar.gz` - Level 3 shopping database

**Download from:** [HuggingFace Dataset](https://huggingface.co/datasets/Qwen/DeepPlanning)

First, download the required data files from HuggingFace and place them in the project:

- In `shoppingplanning/database_zip/`: put `database_level1.tar.gz`, `database_level2.tar.gz`, and `database_level3.tar.gz`.

### Step 3: Extract Database Files

After downloading, extract the compressed shopping databases:

```bash
# Extract database files for all levels
cd database_zip
tar -xzf database_level1.tar.gz -C ..
tar -xzf database_level2.tar.gz -C ..
tar -xzf database_level3.tar.gz -C ..
cd ..
```

### Step 4: Configure Model Settings

**Note:** Model configuration is shared across all domains and located in the project root.

Edit `models_config.json` in the **project root directory** (one level up from shoppingplanning/):

```json
{
  "models": {
    "qwen-plus": {
      "model_name": "qwen-plus",
      "model_type": "openai",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key_env": "DASHSCOPE_API_KEY",
      "temperature": 0.0
    },
    "gpt-4o-2024-11-20": {
      "model_name": "gpt-4o-2024-11-20",
      "model_type": "openai",
      "base_url": "https://api.openai.com/v1/models",
      "api_key_env": "OPENAI_API_KEY",
      "temperature": 0.0
    }
  }
}
```

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
SHOPPING_AGENT_MODEL="qwen-plus" \
SHOPPING_LEVELS="1 2 3" \
SHOPPING_WORKERS=50 \
SHOPPING_MAX_LLM_CALLS=400 \
bash run.sh
```

**Available Environment Variables:**
- `SHOPPING_AGENT_MODEL`: Model name(s) from models_config.json (space-separated for multiple models)
- `SHOPPING_LEVELS`: Levels to run (space-separated, e.g., "1 2 3")
- `SHOPPING_WORKERS`: Number of parallel workers
- `SHOPPING_MAX_LLM_CALLS`: Maximum LLM calls per sample

**Or edit default values in `run.sh` for permanent changes:**

Find and modify these lines in `run.sh` (change the values after the last `:-`):

```bash
TEST_LEVELS="${BENCHMARK_LEVELS:-${SHOPPING_LEVELS:-1 2 3}}"           # Change levels
WORKERS="${BENCHMARK_WORKERS:-${SHOPPING_WORKERS:-50}}"                # Change workers  
MAX_LLM_CALLS="${BENCHMARK_MAX_LLM_CALLS:-${SHOPPING_MAX_LLM_CALLS:-400}}"  # Change max LLM calls
SHOPPING_AGENT_MODEL="${BENCHMARK_MODEL:-${SHOPPING_AGENT_MODEL:-qwen-plus}}"  # Change model
```

Then simply run:

```bash
bash run.sh
```

**How it works:**
1. Creates an **isolated database copy** with unique timestamp for each run (e.g., `database_run_qwen-plus_level1_20250105143022_12345/`). This allows multiple concurrent runs without interference.
2. Runs agent inference for all specified models across all levels (sequentially: level 1 → 2 → 3)
3. Moves inference results to `database_infered/` after completion
4. Runs evaluation pipeline for each level
5. Generates evaluation reports in `result_report/` for each level (reports are **always saved**, even if model is invalid)
6. Calculates overall statistics across all levels for each model and saves to `result_report/{model_name}_statistics.json`

**Note on concurrent runs:** Each run uses an isolated database directory, so you can safely run multiple benchmarks simultaneously (e.g., testing different models in parallel).


## 🔄 Understanding the Pipeline

The benchmark runs in two main stages:

#### Stage 1: Inference (Agent Planning)
**What it does:** 
- Loads shopping planning tasks from `data/level_{level}_query_meta.json`
- Calls the LLM agent to generate shopping plans
- Agent uses tools to query database (search products, filter, add to cart, etc.)
- Saves agent trajectories and execution logs in `database/case_{id}/`

**Output:**
```
database/
├── case_0/
│   ├── messages.json          # Agent execution traces
│   ├── cart.json              # Final shopping cart
│   └── validation_cases.json  # Ground truth
├── case_1/
│   └── ...
└── ...
```

#### Stage 2: Evaluation
**What it does:**
- Compares agent-generated carts with ground truth
- Calculates accuracy scores (product matching, coupon matching)
- Validates case completion
- Generates evaluation reports

**Output:**
```
result_report/database_{MODEL}_level{LEVEL}_{TIMESTAMP}/
├── summary_report.json        # Overall metrics and statistics
├── case_0_report.json         # Individual case detailed reports
├── case_1_report.json
└── ...                        # One report file per case
```

## 📊 Viewing Results

#### Cross-Level Statistics (Overall Score)

After running all levels for a model, the script automatically calculates overall statistics across all levels. This provides a comprehensive view of model performance across different difficulty levels.

```bash
# View overall statistics for a model
cat result_report/{MODEL}_statistics.json
```

**Example Output:**
```json
{
  "model_name": "qwen-plus",
  "statistics_time": "2026-01-05T12:30:45.123456",
  "levels": {
    "level_1": {
      "folder_name": "database_qwen-plus_level1_202601051200",
      "total_cases": 50,
      "successful_cases": 45,
      "failed_cases": 5,
      "total_matched_products": 200,
      "total_expected_products": 210,
      "total_extra_products": 10,
      "average_case_score": 0.90,
      "overall_match_rate": 0.952,
      "incomplete_cases": 0,
      "incomplete_rate": 0.0,
      "valid": true
    },
    "level_2": {
      "folder_name": "database_qwen-plus_level2_202601051300",
      "total_cases": 50,
      "successful_cases": 30,
      "failed_cases": 20,
      "total_matched_products": 150,
      "total_expected_products": 180,
      "total_extra_products": 25,
      "average_case_score": 0.60,
      "overall_match_rate": 0.833,
      "incomplete_cases": 2,
      "incomplete_rate": 0.04,
      "valid": true
    },
    "level_3": {
      "folder_name": "database_qwen-plus_level3_202601051400",
      "total_cases": 50,
      "successful_cases": 20,
      "failed_cases": 30,
      "total_matched_products": 100,
      "total_expected_products": 200,
      "total_extra_products": 40,
      "average_case_score": 0.40,
      "overall_match_rate": 0.500,
      "incomplete_cases": 5,
      "incomplete_rate": 0.10,
      "valid": true
    }
  },
  "total": {
    "total_cases": 150,
    "successful_cases": 95,
    "failed_cases": 55,
    "total_matched_products": 450,
    "total_expected_products": 590,
    "total_extra_products": 75,
    "successful_rate": 0.6333,
    "match_rate": 0.7627,
    "weighted_average_case_score": 0.6333,
    "incomplete_cases": 7,
    "incomplete_rate": 0.0467,
    "valid": true,
    "levels_completed": [1, 2, 3]
  }
}
```

**Key Metrics Explained:**
- **`successful_rate`**: Overall percentage of cases that achieved perfect scores (all products and coupons matched)
- **`match_rate`** ⭐: Overall percentage of expected products that were correctly matched. **This is the main metric reported in the paper.**
- **`weighted_average_case_score`** ⭐: Average case score weighted by the number of cases in each level. **This is the main metric reported in the paper.**
- **`levels_completed`**: List of levels included in the statistics
- **`valid`**: Whether the model is considered valid (incomplete_rate ≤ 10% for all levels)

**Note:** Evaluation reports are **always saved** regardless of the `valid` status. This allows for debugging and analysis even when a model has high incomplete rates (e.g., due to early termination or errors). The `valid` flag in the report indicates whether the results should be considered reliable for benchmarking.

#### Level Statistics

```bash
cat result_report/database_{MODEL}_level{LEVEL}_{TIMESTAMP}/summary_report.json
```

**Example Output:**
```json
{
  "evaluation_time": "2026-01-04T12:09:18.522300",
  "overall_statistics": {
    "total_cases": 50,
    "successful_cases": 11,
    "failed_cases": 39,
    "average_score": 0.22,
    "average_case_score": 0.22,
    "max_score": 1.0,
    "min_score": 0.0,
    "total_matched_products": 152,
    "total_expected_products": 215,
    "total_extra_products": 54,
    "overall_match_rate": 0.707,
    "incomplete_cases": 0,
    "incomplete_rate": 0.0,
    "valid": true
  },
  "case_results": [
    {
      "case_name": "case_1",
      "success": false,
      "score": 0.8,
      "matched_count": 4,
      "expected_count": 5,
      "extra_products_count": 1,
      "case_score": 0.0,
      "is_completed": true
    }
  ],
  "detailed_results": [...]
}
```

#### Per-Case Details

```bash
# View detailed report for a specific case
cat result_report/database_{MODEL}_level{LEVEL}_{TIMESTAMP}/case_0_report.json

```

**Example Case Report:**
```json
{
  "case_name": "case_1",
  "evaluation_time": "2026-01-04T12:09:18.174467",
  "summary": {
    "score": 0.8,
    "matched_count": 4,
    "expected_count": 5,
    "extra_products_count": 1,
    "coupon_score": 0.0
  },
  "query": "User shopping query...",
  "matched_products": ["706395e1", "3b5b2e0e", ...],
  "matched_coupons": [],
  "ground_truth_coupons": [],
  "unmatched_ground_truth_products": [...],
  "extra_products": [...],
  "ground_truth_products": [...]
}
```

## 📝 Notes

- The benchmark automatically manages database initialization per run
- Results are backed up to `database_infered/` after each model inference
- Evaluation reports are saved to `result_report/`
- The script supports running multiple models sequentially with automatic delays between runs

