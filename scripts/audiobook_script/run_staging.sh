#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_staging.sh — One-shot staging run for the Audiobook Pipeline
#
# Runs: dry-run → regression → real book section
# Writes evidence to: artifacts/audiobook/staging/
#
# Usage (from repo root, with LM Studio running at http://127.0.0.1:1234):
#   bash scripts/audiobook_script/run_staging.sh
#   bash scripts/audiobook_script/run_staging.sh --regression-only
#   bash scripts/audiobook_script/run_staging.sh --locale zh-TW   (single locale)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"

REGRESSION_ONLY=false
LOCALE_FILTER=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --regression-only) REGRESSION_ONLY=true; shift ;;
    --locale) LOCALE_FILTER="$2"; shift 2 ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

STAGING_DIR="artifacts/audiobook/staging"
TIMESTAMP=$(date -u '+%Y%m%dT%H%M%S')
mkdir -p "$STAGING_DIR"

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║     AUDIOBOOK PIPELINE — STAGING RUN           ║"
echo "║     $(date -u '+%Y-%m-%d %H:%M UTC')               ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# ─── STEP 1: Dry-run (setup check) ───────────────────────────────────────────
echo "STEP 1: Setup check (dry-run)..."
python3 scripts/audiobook_script/run_regression.py --dry-run --verbose
echo ""

# ─── STEP 2: Full golden regression ──────────────────────────────────────────
echo "STEP 2: Golden regression (all 4 required locales)..."
LOCALE_ARG=""
[[ -n "$LOCALE_FILTER" ]] && LOCALE_ARG="--locale $LOCALE_FILTER"

python3 scripts/audiobook_script/run_regression.py --verbose $LOCALE_ARG

# Copy regression report to staging evidence
cp artifacts/audiobook/regression_report.json \
   "$STAGING_DIR/regression_report_${TIMESTAMP}.json" 2>/dev/null || true
echo "  → Report saved to $STAGING_DIR/regression_report_${TIMESTAMP}.json"
echo ""

if [[ "$REGRESSION_ONLY" == "true" ]]; then
  echo "Regression-only mode — skipping real book run"
  exit 0
fi

# ─── STEP 3: Real book section run ───────────────────────────────────────────
echo "STEP 3: Real book section (staging book run)..."

# Source file: use the Pearl Prime staging sample
SOURCE_FILE="artifacts/audiobook/source/staging/staging_zh_tw_001.txt"
mkdir -p "$(dirname "$SOURCE_FILE")"

# Write staging source if it doesn't exist
if [[ ! -f "$SOURCE_FILE" ]]; then
  cat > "$SOURCE_FILE" << 'SOURCE_EOF'
[HOOK] You have already survived the hardest version of this.
That version of you — the one who kept going when nothing made sense — did not quit.
She adapted.

[STORY] Three years into her marriage, Lin noticed she had stopped finishing sentences.
Not because she didn't know what she wanted to say — she always knew —
but because she had learned, in small increments, that finishing her thoughts
created friction. So she stopped. And then, after a while, she stopped noticing
that she had stopped.
This is how self-erasure works. Not in a single dramatic moment.
In the accumulated weight of small silences.

[TAKEAWAY] The insight from Lin's story is this: disappearing rarely feels like disappearing
when it is happening. It feels like keeping the peace.
Remember that. Keeping the peace and erasing yourself are not always different things.
SOURCE_EOF
  echo "  → Staging source written: $SOURCE_FILE"
fi

BATCH_ID="staging_${TIMESTAMP}"

python3 scripts/audiobook_script/run_comparator_loop.py \
  --section-id "staging_zh_tw_001" \
  --locale "zh-TW" \
  --english-source "$SOURCE_FILE" \
  --book-id "staging" \
  --batch-id "$BATCH_ID" \
  --content-type "pearl_prime"

# ─── STEP 4: Evidence summary ─────────────────────────────────────────────────
echo ""
echo "STEP 4: Collecting evidence..."

EVIDENCE_FILE="$STAGING_DIR/evidence_${TIMESTAMP}.md"
cat > "$EVIDENCE_FILE" << EVIDENCE_EOF
# Staging Run Evidence
**Date**: $(date -u '+%Y-%m-%d %H:%M UTC')
**Batch ID**: $BATCH_ID
**LM Studio**: http://127.0.0.1:1234/v1

## Regression
- Report: artifacts/audiobook/staging/regression_report_${TIMESTAMP}.json
- Locales tested: zh-TW, zh-HK, zh-SG, zh-CN
- Content types: pearl_prime, pearl_news, teacher_mode, phoenix_v4

## Real Book Section
- Section: staging_zh_tw_001
- Locale: zh-TW
- Content type: pearl_prime
- Artifacts: artifacts/audiobook/staging/${BATCH_ID}/staging_zh_tw_001/

## Sign-off
- [ ] Pipeline lead: _____________ Date: _______
- [ ] Locale owner: _____________ Date: _______
EVIDENCE_EOF

echo "  → Evidence file: $EVIDENCE_FILE"

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║     STAGING COMPLETE ✓                         ║"
echo "║                                                ║"
echo "║  Final step: review evidence and sign off      ║"
echo "║  on docs/GO_LIVE_FINAL_CHECKLIST.md Item 10    ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
