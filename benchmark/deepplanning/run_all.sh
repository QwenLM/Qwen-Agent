#!/bin/bash

# ============================================
# Unified Benchmark Runner
# Runs both Shopping and Travel Planning benchmarks
# Usage: bash run_all.sh
# ============================================

set -e  # Exit immediately if a command exits with a non-zero status

# Get the absolute path of the script directory
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

# ============================================
# Configuration
# ============================================

# Domains to run (space-separated): "shopping travel" or just "shopping"
DOMAINS="travel shopping"

# Model configuration (applies to all domains unless overridden)
# For a single model: BENCHMARK_MODEL="qwen-plus"
# For multiple models: BENCHMARK_MODEL="qwen-plus qwen3-max gpt-4o-2024-11-20"
BENCHMARK_MODEL="qwen-plus"

# ============================================
# Shopping Domain Configuration
# ============================================

# Test levels for shopping domain (space-separated)
SHOPPING_LEVELS="1 2 3"

# Number of parallel workers for shopping
SHOPPING_WORKERS=50

# Maximum LLM calls per sample for shopping
SHOPPING_MAX_LLM_CALLS=400

# Model for shopping domain (optional, defaults to BENCHMARK_MODEL)
SHOPPING_MODEL="${BENCHMARK_MODEL}"

# ============================================
# Travel Domain Configuration
# ============================================

# Model for travel domain (optional, defaults to BENCHMARK_MODEL)
TRAVEL_MODEL="${BENCHMARK_MODEL}"

# Language for travel domain: zh, en, or empty for both
TRAVEL_LANGUAGE=""

# Number of parallel workers for travel
TRAVEL_WORKERS=50

# Maximum LLM calls per sample for travel
TRAVEL_MAX_LLM_CALLS=400

# Start point for travel: inference, conversion, evaluation
TRAVEL_START_FROM="inference"

# Output directory for travel (optional, default: results/ in travelplanning directory)
TRAVEL_OUTPUT_DIR=""

# Verbose output for travel
TRAVEL_VERBOSE="false"

# Debug mode for travel
TRAVEL_DEBUG="false"

# ============================================
# Validate Configuration
# ============================================

# Check if models_config.json exists
if [ ! -f "$BASE_DIR/models_config.json" ]; then
    echo "❌ Error: models_config.json not found in $BASE_DIR"
    echo "   Please create models_config.json in the project root directory."
    exit 1
fi

# Check if required environment variables are set
if [ -f "$BASE_DIR/.env" ]; then
    echo "📝 Loading environment variables from .env"
    set -a
    source "$BASE_DIR/.env"
    set +a
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║              Unified Agent Benchmark Runner                        ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Domains:              $DOMAINS"
echo "  Default Model:        $BENCHMARK_MODEL"
echo ""
echo "Shopping Domain:"
echo "  Model:                ${SHOPPING_MODEL}"
echo "  Levels:               ${SHOPPING_LEVELS}"
echo "  Workers:              ${SHOPPING_WORKERS}"
echo "  Max LLM calls:        ${SHOPPING_MAX_LLM_CALLS}"
echo ""
echo "Travel Domain:"
echo "  Model:                ${TRAVEL_MODEL}"
echo "  Language:             ${TRAVEL_LANGUAGE}"
echo "  Workers:              ${TRAVEL_WORKERS}"
echo "  Max LLM calls:        ${TRAVEL_MAX_LLM_CALLS}"
echo "  Start from:           ${TRAVEL_START_FROM}"
echo ""

# ============================================
# Run Benchmarks
# ============================================

DOMAIN_LIST=($DOMAINS)
START_TIME=$(date +%s)

# Build list of unique models from both domains
MODELS_LIST=()
if [[ " ${DOMAIN_LIST[@]} " =~ " shopping " ]]; then
    for model in $SHOPPING_MODEL; do
        if [[ ! " ${MODELS_LIST[@]} " =~ " ${model} " ]]; then
            MODELS_LIST+=("$model")
        fi
    done
fi
if [[ " ${DOMAIN_LIST[@]} " =~ " travel " ]]; then
    for model in $TRAVEL_MODEL; do
        if [[ ! " ${MODELS_LIST[@]} " =~ " ${model} " ]]; then
            MODELS_LIST+=("$model")
        fi
    done
fi

for MODEL in "${MODELS_LIST[@]}"; do
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "🚀 Starting Benchmark for Model: ${MODEL}"
    echo "════════════════════════════════════════════════════════════════════"
    echo ""
    
    for DOMAIN in "${DOMAIN_LIST[@]}"; do
        if [ "$DOMAIN" = "shopping" ]; then
            DOMAIN_DIR="$BASE_DIR/shoppingplanning"
            DOMAIN_NAME="Shopping Planning"
            # Check if this model should run for shopping domain
            if [[ ! " ${SHOPPING_MODEL} " =~ " ${MODEL} " ]]; then
                echo "⚠️  Skipping ${DOMAIN_NAME} for model ${MODEL} (not in SHOPPING_MODEL list)"
                continue
            fi
            # Set shopping-specific parameters
            DOMAIN_MODEL="$MODEL"
            DOMAIN_LEVELS="$SHOPPING_LEVELS"
            DOMAIN_WORKERS="$SHOPPING_WORKERS"
            DOMAIN_MAX_LLM_CALLS="$SHOPPING_MAX_LLM_CALLS"
        elif [ "$DOMAIN" = "travel" ]; then
            DOMAIN_DIR="$BASE_DIR/travelplanning"
            DOMAIN_NAME="Travel Planning"
            # Check if this model should run for travel domain
            if [[ ! " ${TRAVEL_MODEL} " =~ " ${MODEL} " ]]; then
                echo "⚠️  Skipping ${DOMAIN_NAME} for model ${MODEL} (not in TRAVEL_MODEL list)"
                continue
            fi
            # Set travel-specific parameters
            DOMAIN_MODEL="$MODEL"
            DOMAIN_WORKERS="$TRAVEL_WORKERS"
            DOMAIN_MAX_LLM_CALLS="$TRAVEL_MAX_LLM_CALLS"
        else
            echo "⚠️  Warning: Unknown domain '$DOMAIN', skipping..."
            continue
        fi
        
        if [ ! -d "$DOMAIN_DIR" ]; then
            echo "⚠️  Warning: Domain directory not found: $DOMAIN_DIR, skipping..."
            continue
        fi
        
        echo ""
        echo "────────────────────────────────────────────────────────────────────"
        echo "🔹 Running ${DOMAIN_NAME} Benchmark"
        echo "────────────────────────────────────────────────────────────────────"
        if [ "$DOMAIN" = "shopping" ]; then
            echo "    Model:          ${DOMAIN_MODEL}"
            echo "    Levels:         ${DOMAIN_LEVELS}"
            echo "    Workers:        ${DOMAIN_WORKERS}"
            echo "    Max LLM calls:  ${DOMAIN_MAX_LLM_CALLS}"
        elif [ "$DOMAIN" = "travel" ]; then
            echo "    Model:          ${DOMAIN_MODEL}"
            echo "    Language:       ${TRAVEL_LANGUAGE}"
            echo "    Workers:        ${DOMAIN_WORKERS}"
            echo "    Max LLM calls:  ${DOMAIN_MAX_LLM_CALLS}"
            echo "    Start from:     ${TRAVEL_START_FROM}"
        fi
        echo "────────────────────────────────────────────────────────────────────"
        echo ""
        
        cd "$DOMAIN_DIR"
        
        # Note: models_config.json is automatically loaded from project root
        # Each domain's code will automatically find ../models_config.json
        
        # Export domain-specific environment variables
        export BENCHMARK_MODEL="$DOMAIN_MODEL"
        export BENCHMARK_WORKERS="$DOMAIN_WORKERS"
        export BENCHMARK_MAX_LLM_CALLS="$DOMAIN_MAX_LLM_CALLS"
        
        if [ "$DOMAIN" = "shopping" ]; then
            export BENCHMARK_LEVELS="$DOMAIN_LEVELS"
            export SHOPPING_AGENT_MODEL="$DOMAIN_MODEL"
        elif [ "$DOMAIN" = "travel" ]; then
            # Export BENCHMARK_LANGUAGE (including empty string for "both languages")
            export BENCHMARK_LANGUAGE="$TRAVEL_LANGUAGE"
            export BENCHMARK_START_FROM="$TRAVEL_START_FROM"
            export BENCHMARK_OUTPUT_DIR="$TRAVEL_OUTPUT_DIR"
            export BENCHMARK_VERBOSE="$TRAVEL_VERBOSE"
            export BENCHMARK_DEBUG="$TRAVEL_DEBUG"
            export TRAVEL_AGENT_MODEL="$DOMAIN_MODEL"
        fi
        
        # Run the domain-specific benchmark script
        bash run.sh
        EXIT_CODE=$?
        
        if [ $EXIT_CODE -ne 0 ]; then
            echo "❌ ${DOMAIN_NAME} benchmark failed for model ${MODEL}"
            exit 1
        fi
        
        echo ""
        echo "✅ ${DOMAIN_NAME} benchmark completed for ${MODEL}"
        echo ""
        
        cd "$BASE_DIR"
    done
    
    # Aggregate results across domains for this model
    echo ""
    echo "────────────────────────────────────────────────────────────────────"
    echo "📊 Aggregating Results for ${MODEL}"
    echo "────────────────────────────────────────────────────────────────────"
    echo ""
    
    # Pass travel output directory if specified
    if [ -n "$TRAVEL_OUTPUT_DIR" ]; then
        python aggregate_results.py --model_name "${MODEL}" --travel-output-dir "$TRAVEL_OUTPUT_DIR"
    else
        python aggregate_results.py --model_name "${MODEL}"
    fi
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "⚠️  Warning: Result aggregation failed for model ${MODEL}, continuing..."
    else
        echo "✅ Results aggregated for ${MODEL}"
    fi
    
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "✅ Model ${MODEL} completed all benchmarks"
    echo "════════════════════════════════════════════════════════════════════"
    echo ""
    
    # Sleep between model runs except for the last one
    if [ "${MODEL}" != "${MODELS[-1]}" ]; then
        echo "⏳ Sleeping 60s before next model..."
        sleep 60
    fi
done

# ============================================
# Final Summary
# ============================================

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    Benchmark Completed                             ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Total time: ${ELAPSED}s (${ELAPSED_MIN}m ${ELAPSED_SEC}s)"
echo "Results saved in:"
echo "  - shoppingplanning/result_report/"
echo "  - travelplanning/result_report/"
echo "  - aggregated_results/"
echo ""
echo "✅ All benchmarks completed successfully!"
echo ""

exit 0

