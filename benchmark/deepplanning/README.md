# DeepPlanning Benchmark

A comprehensive benchmark for evaluating AI agents' planning capabilities across multiple domains.

## 📋 Overview

This benchmark evaluates AI agents on complex planning tasks across two domains:

- **Travel Planning**: Evaluate agents on travel itinerary planning tasks
- **Shopping Planning**: Evaluate agents on e-commerce shopping tasks

**Flexible Execution:**
- **Unified Run (Recommended)**: You can run both domains together using the unified orchestrator. This documentation focuses on this unified workflow to help you reproduce the experimental results reported in our paper.
- **Independent Run**: Each domain can also be run independently. For domain-specific details, please refer to their respective documentation:
  - [`travelplanning/readme.md`](travelplanning/readme.md) - Travel domain details
  - [`shoppingplanning/README.md`](shoppingplanning/README.md) - Shopping domain details

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
# Create and activate conda environment
conda create -n deepplanning python=3.10 -y
conda activate deepplanning
pip install -r requirements.txt
```

### Step 2: Download Data Files
First, download the required data files from [HuggingFace Dataset](https://huggingface.co/datasets/Qwen/DeepPlanning) and place them in the project:

**Shopping Planning:**
- `shoppingplanning/database_zip/database_level1.tar.gz` - Level 1 shopping database
- `shoppingplanning/database_zip/database_level2.tar.gz` - Level 2 shopping database
- `shoppingplanning/database_zip/database_level3.tar.gz` - Level 3 shopping database

**Travel Planning:**
- `travelplanning/database/database_zh.zip` - Chinese database 
- `travelplanning/database/database_en.zip` - English database


- In `shoppingplanning/database_zip/`: put `database_level1.tar.gz`, `database_level2.tar.gz`, and `database_level3.tar.gz`.
- In `travelplanning/database/`: put `database_zh.zip` and `database_en.zip`.


### Step 3: Extract Database Files

After downloading, extract the compressed databases:

```bash
# Extract shopping databases
cd shoppingplanning/database_zip
tar -xzf database_level1.tar.gz -C ..
tar -xzf database_level2.tar.gz -C ..
tar -xzf database_level3.tar.gz -C ..
cd ../..

# Extract travel databases
cd travelplanning/database
unzip database_zh.zip    # Chinese database (flights, hotels, restaurants, attractions)
unzip database_en.zip    # English database
cd ../..
```

### Step 4: Configure Models

Edit `models_config.json` in the project root to add your model configurations:

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
**Important Note about `qwen-plus`:**
- The `qwen-plus` configuration is **required** because it's used by default in the conversion stage (`evaluation/convert_report.py`) in travel domain to parse and format agent-generated travel plans.
- If you want to use a different model for conversion, you can modify the `conversion_model` variable in `travelplanning/evaluation/convert_report.py`.

### Step 5: Set API Keys

Create a `.env` file in the project root (use `.env.example` as template):

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### Step 6: Run the Unified Benchmark

Edit `run_all.sh` to configure your run:

```bash
# Configuration in run_all.sh
DOMAINS="travel shopping"          # Domains to run
BENCHMARK_MODEL="qwen-plus"        # Default model for all domains

# Shopping domain configuration
SHOPPING_MODEL="${BENCHMARK_MODEL}"  # Model(s) for shopping
SHOPPING_LEVELS="1 2 3"             # Levels to run
SHOPPING_WORKERS=50                 # Parallel workers
SHOPPING_MAX_LLM_CALLS=400          # Max LLM calls per sample

# Travel domain configuration
TRAVEL_MODEL="${BENCHMARK_MODEL}"    # Model(s) for travel
TRAVEL_LANGUAGE=""                   # Language (zh/en/empty for both)
TRAVEL_WORKERS=50                    # Parallel workers
TRAVEL_MAX_LLM_CALLS=400             # Max LLM calls per sample
TRAVEL_START_FROM="inference"        # Start point: inference, conversion, evaluation
TRAVEL_OUTPUT_DIR=""                 # Output directory (optional)
TRAVEL_VERBOSE="false"               # Verbose output
TRAVEL_DEBUG="false"                  # Debug mode
```

Then run:

```bash
bash run_all.sh
```

**What it does:**
1. Runs each model on all specified domains sequentially
2. For **Travel domain**: runs both language versions (Chinese and English)
3. For **Shopping domain**: runs all difficulty levels (1 → 2 → 3)
4. Generates per-domain statistics in domain-specific result folders
5. Aggregates results across domains and calculates overall scores
6. Saves aggregated results in `aggregated_results/{model_name}_aggregated.json`

## 📊 Understanding Results

### Result File Locations

**Travel Domain:**
- Evaluation results: `travelplanning/results/{model}_{language}/evaluation/evaluation_summary.json`
- Converted plans: `travelplanning/results/{model}_{language}/converted_plans/`
- Trajectories: `travelplanning/results/{model}_{language}/trajectories/`

**Shopping Domain:**
- Per-level results: `shoppingplanning/result_report/summary_report_{model}_{level}_{timestamp}.json`
- Overall statistics: `shoppingplanning/result_report/{model}_statistics.json`
- Inference outputs: `shoppingplanning/database_infered/`



**Aggregated Results (Both Domains):**
- Cross-domain aggregation: `aggregated_results/{model}_aggregated.json`

**For detailed domain-specific metrics and result interpretation:**
- **Shopping Domain**: See [Shopping Results Documentation](shoppingplanning/README.md#step-7-view-results) for detailed explanation of match_rate, weighted_average_case_score, and per-level statistics
- **Travel Domain**: See [Travel Results Documentation](travelplanning/readme.md#step-7-view-results) for detailed explanation of composite_score, case_acc, commonsense_score, and personalized_score

### Aggregated Results Format

After running all benchmarks, view the aggregated results:

```bash
cat aggregated_results/{MODEL}_aggregated.json
```

**Example Output:**
```json
{
  "model_name": "qwen-plus",
  "aggregation_time": "2026-01-05T15:30:00.000000",
  "domains": {
    "shopping": {
      "total_cases": 120,
      "successful_cases": 17,
      "successful_rate": 0.1417,
      "match_rate": 0.6209,
      "weighted_average_case_score": 0.1417,
      "valid": true,
      "levels_completed": [1, 2, 3]
    },
    "travel": {
      "total_cases": 240,
      "successful_cases": 238,
      "successful_rate": 0.9917,
      "composite_score": 0.2813,
      "case_acc": 0.0,
      "commonsense_score": 0.4292,
      "personalized_score": 0.1333,
      "valid": true,
      "languages_completed": ["zh", "en"],
      "language_details": {
        "zh": {
          "composite_score": 0.2813,
          "case_acc": 0.0,
          "commonsense_score": 0.4292,
          "personalized_score": 0.1333
        },
        "en": {
          "composite_score": 0.2850,
          "case_acc": 0.0,
          "commonsense_score": 0.4300,
          "personalized_score": 0.1350
        }
      }
    }
  },
  "overall": {
    "total_cases": 360,
    "successful_cases": 255,
    "successful_rate": 0.5667,
    "valid": true,
    "domains_completed": ["shopping", "travel"],
    "num_domains": 2,
    "shopping_match_rate": 0.6209,
    "shopping_weighted_average_case_score": 0.1417,
    "travel_composite_score": 0.2813,
    "travel_case_acc": 0.0,
    "travel_commonsense_score": 0.4292,
    "travel_personalized_score": 0.1333,
    "avg_acc": 0.0708
  }
}
```

**Key Metrics Overview:**

**Shopping Domain:**
- **`match_rate`** ⭐: Percentage of expected items correctly matched (main paper metric)
- **`weighted_average_case_score`** ⭐: Average case completion score (main paper metric)

**Travel Domain:**
- **`composite_score`** ⭐: Weighted combination of commonsense and personalized scores (main paper metric)
- **`case_acc`** ⭐: Percentage of cases passing all constraints (main paper metric)
- `commonsense_score`: Score for commonsense constraint satisfaction
- `personalized_score`: Score for personalized requirement satisfaction

**Cross-Domain:**
- **`avg_acc`** ⭐: Average of shopping `weighted_average_case_score` and travel `case_acc` - **Primary cross-domain metric**

---


## 📄 License

Please refer to individual domain directories for license information.

