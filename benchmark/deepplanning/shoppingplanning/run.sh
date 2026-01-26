#!/bin/bash

# ============================================
# Shopping Benchmark Runner
# Usage: bash run.sh
# 
# Key Feature: Each run creates an isolated database copy with timestamp
# to allow multiple concurrent runs without interference.
# ============================================

set -e  # Exit immediately if a command exits with a non-zero status
cd "$(dirname "$0")"

# ============================================
# Configuration
# ============================================

# Set benchmark levels to run (space-separated): "1" or "1 2 3"
# Can be overridden by BENCHMARK_LEVELS or SHOPPING_LEVELS environment variable
TEST_LEVELS="${BENCHMARK_LEVELS:-${SHOPPING_LEVELS:-1 2 3}}"

# Number of parallel workers
# Can be overridden by BENCHMARK_WORKERS or SHOPPING_WORKERS environment variable
WORKERS="${BENCHMARK_WORKERS:-${SHOPPING_WORKERS:-50}}"

# Maximum LLM calls per sample
# Can be overridden by BENCHMARK_MAX_LLM_CALLS or SHOPPING_MAX_LLM_CALLS environment variable
MAX_LLM_CALLS="${BENCHMARK_MAX_LLM_CALLS:-${SHOPPING_MAX_LLM_CALLS:-400}}"

# Model configuration
# Can be overridden by BENCHMARK_MODEL or SHOPPING_AGENT_MODEL environment variable
# For a single model: SHOPPING_AGENT_MODEL="qwen-plus"
# For multiple models: SHOPPING_AGENT_MODEL="qwen-plus qwen3-max gpt-4o-2024-11-20"
SHOPPING_AGENT_MODEL="${BENCHMARK_MODEL:-${SHOPPING_AGENT_MODEL:-qwen-plus}}"
BASE_DIR=$(dirname "$0")

# ============================================
# Helper Functions
# ============================================

# Generate a unique run ID for database isolation
generate_run_id() {
    echo "$(date +%Y%m%d%H%M%S)_$$_${RANDOM}"
}

# ============================================
# Run shopping benchmark evaluation
# ============================================

MODELS=($SHOPPING_AGENT_MODEL)
LEVELS=($TEST_LEVELS)

for MODEL in "${MODELS[@]}"; do
    export SHOPPING_AGENT_MODEL="$MODEL"
    
    for TEST_LEVEL in "${LEVELS[@]}"; do
        # Always cd to BASE_DIR before execution to ensure correct relative paths
        cd "$BASE_DIR"

        # Generate unique run ID for this execution
        RUN_ID=$(generate_run_id)
        
        # Create isolated database directory with unique name
        # This allows multiple concurrent runs without interference
        DATABASE_RUN_DIR="database_run_${MODEL}_level${TEST_LEVEL}_${RUN_ID}"
        
        echo ""
        echo "🚀 Starting Shopping Benchmark"
        echo "   Level: ${TEST_LEVEL}"
        echo "   Model: ${SHOPPING_AGENT_MODEL}"
        echo "   Workers: $WORKERS"
        echo "   Max LLM calls: $MAX_LLM_CALLS"
        echo "   Database: ${DATABASE_RUN_DIR}"
        echo ""
        
        # Create isolated database copy for this run
        rm -rf "${DATABASE_RUN_DIR}"
        mkdir -p "${DATABASE_RUN_DIR}"
        cp -r database_level${TEST_LEVEL}/* "${DATABASE_RUN_DIR}/"
        echo "📁 Created isolated database: ${DATABASE_RUN_DIR}"

        # Run inference with the isolated database directory
        python run.py --workers $WORKERS --level ${TEST_LEVEL} --max-llm-calls $MAX_LLM_CALLS --database-dir "${DATABASE_RUN_DIR}"
        EXIT_CODE=$?
        if [ $EXIT_CODE -ne 0 ]; then
            echo "❌ Inference failed for model ${SHOPPING_AGENT_MODEL} level ${TEST_LEVEL}"
            # Clean up failed run directory
            rm -rf "${DATABASE_RUN_DIR}"
            exit 1
        fi

        # Move/rename the database to final output folder (instead of copying)
        echo "<<<< Starting Evaluation >>>>"
        OUTPUT_FOLDER=database_${SHOPPING_AGENT_MODEL}_level${TEST_LEVEL}_$(date +%Y%m%d%H%M)
        mkdir -p database_infered
        mv "${DATABASE_RUN_DIR}" "database_infered/${OUTPUT_FOLDER}"
        echo "<<<< Database saved to: database_infered/${OUTPUT_FOLDER} >>>>"

        # Run evaluation pipeline
        python evaluation/evaluation_pipeline.py --database_dir "${OUTPUT_FOLDER}" 

        echo "✅ Model ${SHOPPING_AGENT_MODEL} Level ${TEST_LEVEL} finished."
        
        # Sleep 10s between level runs except for the last one
        if [ "${TEST_LEVEL}" != "${LEVELS[-1]}" ]; then
            echo "Sleeping 10s before next level..."
            sleep 10
        fi
    done
    
    # Calculate overall statistics for this model across all levels
    echo ""
    echo "<<<< Calculating Overall Statistics for ${SHOPPING_AGENT_MODEL} >>>>"
    python evaluation/score_statistics.py --model_name "${SHOPPING_AGENT_MODEL}"
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
        echo "⚠️  Warning: Statistics calculation failed for model ${SHOPPING_AGENT_MODEL}, continuing..."
    else
        echo "✅ Statistics calculation completed for ${SHOPPING_AGENT_MODEL}"
    fi
    echo ""
    
    # Sleep 60s between model runs except for the last one
    if [ "${MODEL}" != "${MODELS[-1]}" ]; then
        echo "Sleeping 60s before next model..."
        sleep 60
    fi
done

echo ""
echo "✅ All models completed."
exit 0
