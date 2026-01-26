#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Model from models_config.json
# Can be overridden by BENCHMARK_MODEL environment variable
MODEL="${BENCHMARK_MODEL:-${TRAVEL_AGENT_MODEL:-qwen-plus}}"

# Language: zh, en, or empty for both
# Can be overridden by BENCHMARK_LANGUAGE environment variable
# Use - instead of :- to allow empty string (empty means both languages)
LANGUAGE="${BENCHMARK_LANGUAGE-zh}"

# Parallel workers
# Can be overridden by BENCHMARK_WORKERS environment variable
WORKERS="${BENCHMARK_WORKERS:-40}"

# Max LLM calls per task
# Can be overridden by BENCHMARK_MAX_LLM_CALLS environment variable
MAX_LLM_CALLS="${BENCHMARK_MAX_LLM_CALLS:-400}"

# Start point: inference, conversion, evaluation
# Can be overridden by BENCHMARK_START_FROM environment variable
START_FROM="${BENCHMARK_START_FROM:-inference}"

# Output directory
# Can be overridden by BENCHMARK_OUTPUT_DIR environment variable
OUTPUT_DIR="${BENCHMARK_OUTPUT_DIR:-}"

# Verbose mode
# Can be overridden by BENCHMARK_VERBOSE environment variable
VERBOSE="${BENCHMARK_VERBOSE:-false}"

# Debug mode
# Can be overridden by BENCHMARK_DEBUG environment variable
DEBUG="${BENCHMARK_DEBUG:-false}"


               

read -ra MODELS <<< "$MODEL"
TOTAL=${#MODELS[@]}

# Set language display
if [ -z "$LANGUAGE" ]; then
    LANGUAGE_DISPLAY="zh + en (both languages)"
else
    LANGUAGE_DISPLAY="$LANGUAGE"
fi

# ---------------- Concurrent Execution Mode ----------------
LOG_DIR=$(mktemp -d)

# Trap Ctrl+C signal, cleanup background processes and temp directory
trap "echo '🛑 Caught Ctrl+C, stopping all tasks...'; pkill -P $$; rm -rf $LOG_DIR; exit 1" INT

declare -a PIDS
declare -A PID_TO_MODEL

echo "================================"
echo "🚀 Starting Concurrent Evaluation"
echo "Total Models in config: ${#MODELS[@]}"
echo "Language: $LANGUAGE_DISPLAY"
echo "Workers: $WORKERS"
echo "Start From: $START_FROM"
echo "================================"
echo ""

# ---------------- Pre-check missing IDs and filter completed models ----------------
declare -a MODELS_TO_RUN
declare -A MODEL_SKIP_REASON
declare -A MODEL_START_FROM  # Record which step each model should start from

if [ "$START_FROM" == "inference" ]; then
    echo "🔍 Pre-check: Detecting missing reports and converted plans for each model..."
    echo ""
    
    for MODEL_NAME in "${MODELS[@]}"; do
        SHOULD_SKIP=false
        SKIP_REASON=""
        MODEL_START="inference"  # Default start from inference
        
        if [ -z "$LANGUAGE" ]; then
            # Check both languages
            ZH_REPORTS_MISSING=0
            EN_REPORTS_MISSING=0
            ZH_PLANS_MISSING=0
            EN_PLANS_MISSING=0
            
            for LANG in "zh" "en"; do
                if [ -n "$OUTPUT_DIR" ]; then
                    REPORTS_DIR="$OUTPUT_DIR/${MODEL_NAME}_${LANG}/reports"
                    PLANS_DIR="$OUTPUT_DIR/${MODEL_NAME}_${LANG}/converted_plans"
                else
                    REPORTS_DIR="results/${MODEL_NAME}_${LANG}/reports"
                    PLANS_DIR="results/${MODEL_NAME}_${LANG}/converted_plans"
                fi
                
                # Check reports
                if [ -d "$REPORTS_DIR" ]; then
                    REPORTS_MISSING=$(python3 -c "
import sys
from pathlib import Path
reports_dir = Path('$REPORTS_DIR')
existing_ids = set()
for f in reports_dir.glob('id_*.txt'):
    try:
        id_num = int(f.stem.split('_')[1])
        existing_ids.add(id_num)
    except:
        pass
missing_ids = sorted(set(range(120)) - existing_ids)
print(len(missing_ids))
")
                else
                    REPORTS_MISSING=120
                fi
                
                # Check converted_plans
                if [ -d "$PLANS_DIR" ]; then
                    PLANS_MISSING=$(python3 -c "
import sys
from pathlib import Path
plans_dir = Path('$PLANS_DIR')
existing_ids = set()
for f in plans_dir.glob('id_*_converted.json'):
    try:
        id_num = int(f.stem.split('_')[1])
        existing_ids.add(id_num)
    except:
        pass
missing_ids = sorted(set(range(120)) - existing_ids)
print(len(missing_ids))
")
                else
                    PLANS_MISSING=120
                fi
                
                # Display status
                if [ "$REPORTS_MISSING" -eq 0 ] && [ "$PLANS_MISSING" -eq 0 ]; then
                    echo "  ✅ $MODEL_NAME ($LANG): All complete (reports + plans)"
                elif [ "$REPORTS_MISSING" -eq 0 ] && [ "$PLANS_MISSING" -gt 0 ]; then
                    echo "  📝 $MODEL_NAME ($LANG): Reports ✅ | Plans: $PLANS_MISSING missing"
                elif [ "$REPORTS_MISSING" -gt 0 ]; then
                    echo "  📝 $MODEL_NAME ($LANG): Reports: $REPORTS_MISSING missing | Plans: $PLANS_MISSING missing"
                fi
                
                if [ "$LANG" == "zh" ]; then
                    ZH_REPORTS_MISSING=$REPORTS_MISSING
                    ZH_PLANS_MISSING=$PLANS_MISSING
                else
                    EN_REPORTS_MISSING=$REPORTS_MISSING
                    EN_PLANS_MISSING=$PLANS_MISSING
                fi
            done
            
            # Decide whether to skip and which step to start from
            if [ "$ZH_REPORTS_MISSING" -eq 0 ] && [ "$EN_REPORTS_MISSING" -eq 0 ] && \
               [ "$ZH_PLANS_MISSING" -eq 0 ] && [ "$EN_PLANS_MISSING" -eq 0 ]; then
                # All complete, skip
                SHOULD_SKIP=true
                SKIP_REASON="Both zh and en have all reports and plans"
            elif [ "$ZH_REPORTS_MISSING" -eq 0 ] && [ "$EN_REPORTS_MISSING" -eq 0 ]; then
                # Reports complete but plans missing, start from conversion
                MODEL_START="conversion"
            else
                # Reports missing, start from inference
                MODEL_START="inference"
            fi
        else
            # Check specified language
            if [ -n "$OUTPUT_DIR" ]; then
                REPORTS_DIR="$OUTPUT_DIR/${MODEL_NAME}_${LANGUAGE}/reports"
                PLANS_DIR="$OUTPUT_DIR/${MODEL_NAME}_${LANGUAGE}/converted_plans"
            else
                REPORTS_DIR="results/${MODEL_NAME}_${LANGUAGE}/reports"
                PLANS_DIR="results/${MODEL_NAME}_${LANGUAGE}/converted_plans"
            fi
            
            # Check reports
            if [ -d "$REPORTS_DIR" ]; then
                REPORTS_MISSING=$(python3 -c "
import sys
from pathlib import Path
reports_dir = Path('$REPORTS_DIR')
existing_ids = set()
for f in reports_dir.glob('id_*.txt'):
    try:
        id_num = int(f.stem.split('_')[1])
        existing_ids.add(id_num)
    except:
        pass
missing_ids = sorted(set(range(120)) - existing_ids)
print(len(missing_ids))
")
            else
                REPORTS_MISSING=120
            fi
            
            # Check converted_plans
            if [ -d "$PLANS_DIR" ]; then
                PLANS_MISSING=$(python3 -c "
import sys
from pathlib import Path
plans_dir = Path('$PLANS_DIR')
existing_ids = set()
for f in plans_dir.glob('id_*_converted.json'):
    try:
        id_num = int(f.stem.split('_')[1])
        existing_ids.add(id_num)
    except:
        pass
missing_ids = sorted(set(range(120)) - existing_ids)
print(len(missing_ids))
")
            else
                PLANS_MISSING=120
            fi
            
            # Display status
            if [ "$REPORTS_MISSING" -eq 0 ] && [ "$PLANS_MISSING" -eq 0 ]; then
                echo "  ✅ $MODEL_NAME: All complete (reports + plans)"
                SHOULD_SKIP=true
                SKIP_REASON="All reports and plans exist for language $LANGUAGE"
            elif [ "$REPORTS_MISSING" -eq 0 ] && [ "$PLANS_MISSING" -gt 0 ]; then
                echo "  📝 $MODEL_NAME: Reports ✅ | Plans: $PLANS_MISSING missing"
                MODEL_START="conversion"
            elif [ "$REPORTS_MISSING" -gt 0 ]; then
                echo "  📝 $MODEL_NAME: Reports: $REPORTS_MISSING missing | Plans: $PLANS_MISSING missing"
                MODEL_START="inference"
            fi
        fi
        
        # Decide whether to add to run list
        if [ "$SHOULD_SKIP" = true ]; then
            MODEL_SKIP_REASON[$MODEL_NAME]="$SKIP_REASON"
        else
            MODELS_TO_RUN+=("$MODEL_NAME")
            MODEL_START_FROM[$MODEL_NAME]="$MODEL_START"
        fi
    done
    echo ""
    
    # If there are skipped models, display information
    if [ ${#MODEL_SKIP_REASON[@]} -gt 0 ]; then
        echo "⏭️  Skipping models (already complete):"
        for MODEL_NAME in "${!MODEL_SKIP_REASON[@]}"; do
            echo "   - $MODEL_NAME: ${MODEL_SKIP_REASON[$MODEL_NAME]}"
        done
        echo ""
    fi
else
    # If not starting from inference, run all models
    MODELS_TO_RUN=("${MODELS[@]}")
    for MODEL_NAME in "${MODELS[@]}"; do
        MODEL_START_FROM[$MODEL_NAME]="$START_FROM"
    done
fi

# Update total count
TOTAL=${#MODELS_TO_RUN[@]}

if [ $TOTAL -eq 0 ]; then
    echo "✅ All models are already complete. Nothing to run!"
    exit 0
fi

# Count models starting from different steps
INFERENCE_COUNT=0
CONVERSION_COUNT=0
for MODEL_NAME in "${MODELS_TO_RUN[@]}"; do
    if [ "${MODEL_START_FROM[$MODEL_NAME]}" == "conversion" ]; then
        CONVERSION_COUNT=$((CONVERSION_COUNT + 1))
    else
        INFERENCE_COUNT=$((INFERENCE_COUNT + 1))
    fi
done

echo "================================"
echo "📊 Will run $TOTAL models (skipped ${#MODEL_SKIP_REASON[@]})"
if [ $INFERENCE_COUNT -gt 0 ]; then
    echo "   - From inference: $INFERENCE_COUNT models"
fi
if [ $CONVERSION_COUNT -gt 0 ]; then
    echo "   - From conversion: $CONVERSION_COUNT models (reports complete, only convert plans)"
fi
echo "================================"
echo ""

# ---------------- Auto-fix permissions (simple method) ----------------
if [ -n "$OUTPUT_DIR" ] && [ -d "$OUTPUT_DIR" ]; then
    echo "🔧 Fixing permissions for output directory..."
    chmod -R u+rwX "$OUTPUT_DIR" 2>/dev/null || true
    echo "   ✅ Permissions fixed"
    echo ""
fi

# Start all models concurrently
for i in "${!MODELS_TO_RUN[@]}"; do
    MODEL_NAME="${MODELS_TO_RUN[$i]}"
    LOG_FILE="$LOG_DIR/${MODEL_NAME}.log"
    
    # Get the starting step for this model
    MODEL_START="${MODEL_START_FROM[$MODEL_NAME]:-$START_FROM}"
    
    echo "[STARTED] $MODEL_NAME (start-from: $MODEL_START) ($(date '+%Y-%m-%d %H:%M:%S'))"
    echo "   📝 Log: $LOG_FILE"
    
    (
        python run.py \
            --model "$MODEL_NAME" \
            --workers $WORKERS \
            --max-llm-calls $MAX_LLM_CALLS \
            --start-from "$MODEL_START" \
            ${LANGUAGE:+--language "$LANGUAGE"} \
            ${OUTPUT_DIR:+--output-dir "$OUTPUT_DIR"} \
            ${VERBOSE:+--verbose} \
            ${DEBUG:+--debug} > "$LOG_FILE" 2>&1
        
        echo $? > "$LOG_DIR/${MODEL_NAME}.exit"
    ) &
    
    PID=$!
    PIDS+=($PID)
    PID_TO_MODEL[$PID]="$MODEL_NAME"
done

echo ""
echo "All models started, waiting for completion..."
echo ""

# ---------------- Wait for tasks to complete and print in real-time ----------------
COMPLETED=0
SUCCESS=0
FAILED=0
FAILED_MODELS=()
declare -A PROCESSED_PIDS

while [ $COMPLETED -lt $TOTAL ]; do
    # Poll check each process status
    for PID in "${PIDS[@]}"; do
        # Skip already processed PIDs
        if [ -n "${PROCESSED_PIDS[$PID]}" ]; then
            continue
        fi
        
        # Check if process is still running
        if ! kill -0 $PID 2>/dev/null; then
            # Process ended, mark as processed
            PROCESSED_PIDS[$PID]=1
            
            MODEL_NAME="${PID_TO_MODEL[$PID]}"
            if [ -n "$MODEL_NAME" ]; then
                # Wait for process to fully end and get exit code
                wait $PID 2>/dev/null
                EXIT_CODE=$?
                
                # Also try to read from file (fallback)
                if [ -f "$LOG_DIR/${MODEL_NAME}.exit" ]; then
                    FILE_EXIT_CODE=$(cat "$LOG_DIR/${MODEL_NAME}.exit")
                    if [ -n "$FILE_EXIT_CODE" ]; then
                        EXIT_CODE=$FILE_EXIT_CODE
                    fi
                fi
                
                COMPLETED=$((COMPLETED + 1))
                
                if [ "$EXIT_CODE" -eq 0 ]; then
                    SUCCESS=$((SUCCESS + 1))
                    echo "[$COMPLETED/$TOTAL] ✅ $MODEL_NAME - Completed Successfully ($(date '+%H:%M:%S'))"
                    
                    # Extract summary from log if available
                    LOG_FILE="$LOG_DIR/${MODEL_NAME}.log"
                    if [ -f "$LOG_FILE" ]; then
                        # Try to extract "Model 'xxx' | Language 'xxx' completed" line
                        COMPLETION_LINE=$(grep -E "Model.*Language.*completed" "$LOG_FILE" | tail -n 1)
                        if [ -n "$COMPLETION_LINE" ]; then
                            echo "   $COMPLETION_LINE"
                        fi
                    fi
                else
                    FAILED=$((FAILED + 1))
                    FAILED_MODELS+=("$MODEL_NAME")
                    echo "[$COMPLETED/$TOTAL] ❌ $MODEL_NAME - Failed (exit code: $EXIT_CODE) ($(date '+%H:%M:%S'))"
                    echo "   See log: $LOG_DIR/${MODEL_NAME}.log"
                fi
            fi
        fi
    done
    
    # Avoid high CPU usage, brief sleep
    if [ $COMPLETED -lt $TOTAL ]; then
        sleep 1
    fi
done

echo ""

# ---------------- Summary ----------------
echo "================================"
echo "📊 BATCH EVALUATION SUMMARY"
echo "Total: $TOTAL | Success: $SUCCESS | Failed: $FAILED"
if [ $FAILED -gt 0 ]; then
    echo "Failed models: ${FAILED_MODELS[*]}"
    echo ""
    echo "Log directory: $LOG_DIR"
else
    # Clean up temp directory
    rm -rf $LOG_DIR
fi
echo "================================"
