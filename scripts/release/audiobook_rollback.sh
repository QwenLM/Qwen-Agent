#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# audiobook_rollback.sh — Audiobook Pipeline Rollback Script
#
# Usage:
#   scripts/release/audiobook_rollback.sh --batch-id <batch_id>
#   scripts/release/audiobook_rollback.sh --batch-id <batch_id> --dry-run
#   scripts/release/audiobook_rollback.sh --clear-queue
#   scripts/release/audiobook_rollback.sh --help
#
# What this does:
#   1. Archives the specified batch's artifacts to artifacts/audiobook/_rollback_archive/
#   2. Removes the batch directory from artifacts/audiobook/
#   3. Removes all manual_review_queue entries for this batch
#   4. Writes a rollback log entry to artifacts/audiobook/rollback_log.jsonl
#   5. Optionally clears the entire manual review queue (--clear-queue)
#
# Does NOT:
#   - Delete source files (artifacts/audiobook/source/ is never touched)
#   - Modify any config or prompt files
#   - Affect other batches
#
# Requires: bash 3.2+, jq (for queue manipulation)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ARTIFACTS_DIR="$REPO_ROOT/artifacts/audiobook"
ROLLBACK_ARCHIVE="$ARTIFACTS_DIR/_rollback_archive"
QUEUE_FILE="$ARTIFACTS_DIR/manual_review_queue.json"
ROLLBACK_LOG="$ARTIFACTS_DIR/rollback_log.jsonl"

BATCH_ID=""
DRY_RUN=false
CLEAR_QUEUE=false

# ─── Argument parsing ─────────────────────────────────────────────────────────
usage() {
  echo "Usage:"
  echo "  $0 --batch-id <batch_id>           Roll back a specific batch"
  echo "  $0 --batch-id <batch_id> --dry-run Preview what would be done"
  echo "  $0 --clear-queue                   Clear the manual review queue only"
  echo "  $0 --help                          Show this help"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --batch-id)    BATCH_ID="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=true; shift ;;
    --clear-queue) CLEAR_QUEUE=true; shift ;;
    --help|-h)     usage ;;
    *) echo "Unknown argument: $1"; usage ;;
  esac
done

if [[ -z "$BATCH_ID" && "$CLEAR_QUEUE" == "false" ]]; then
  echo "ERROR: --batch-id is required (or use --clear-queue)"
  usage
fi

# ─── Helpers ─────────────────────────────────────────────────────────────────
log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"; }
dry() { if [[ "$DRY_RUN" == "true" ]]; then echo "  [DRY RUN] $*"; else eval "$*"; fi; }

# ─── Clear queue only ─────────────────────────────────────────────────────────
if [[ "$CLEAR_QUEUE" == "true" ]]; then
  log "Clearing manual review queue..."
  if [[ -f "$QUEUE_FILE" ]]; then
    COUNT=$(python3 -c "import json; q=json.load(open('$QUEUE_FILE')); print(len(q))" 2>/dev/null || echo "?")
    log "  Queue has $COUNT entries"
    if [[ "$DRY_RUN" == "true" ]]; then
      log "  [DRY RUN] Would write empty array to $QUEUE_FILE"
    else
      echo "[]" > "$QUEUE_FILE"
      log "  ✓ Queue cleared"
      ENTRY="{\"action\":\"clear_queue\",\"timestamp_utc\":\"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\",\"entries_cleared\":$COUNT}"
      echo "$ENTRY" >> "$ROLLBACK_LOG"
      log "  ✓ Log entry written to $ROLLBACK_LOG"
    fi
  else
    log "  Queue file not found — nothing to clear"
  fi
  exit 0
fi

# ─── Batch rollback ───────────────────────────────────────────────────────────
log "═══════════════════════════════════════════"
log "AUDIOBOOK BATCH ROLLBACK"
log "Batch: $BATCH_ID"
log "Dry run: $DRY_RUN"
log "Repo: $REPO_ROOT"
log "═══════════════════════════════════════════"

BATCH_DIR="$ARTIFACTS_DIR/$BATCH_ID"

# 1. Check batch exists
if [[ ! -d "$BATCH_DIR" ]]; then
  log "WARNING: Batch directory not found: $BATCH_DIR"
  log "Nothing to archive. Proceeding with queue cleanup only."
else
  # 2. Archive batch
  ARCHIVE_TARGET="$ROLLBACK_ARCHIVE/${BATCH_ID}_$(date -u '+%Y%m%dT%H%M%S')"
  log "Archiving batch to: $ARCHIVE_TARGET"
  if [[ "$DRY_RUN" == "true" ]]; then
    log "  [DRY RUN] Would move $BATCH_DIR → $ARCHIVE_TARGET"
    SECTION_COUNT=$(find "$BATCH_DIR" -name "status.json" 2>/dev/null | wc -l | tr -d ' ')
    log "  [DRY RUN] $SECTION_COUNT section(s) would be archived"
  else
    mkdir -p "$ROLLBACK_ARCHIVE"
    mv "$BATCH_DIR" "$ARCHIVE_TARGET"
    SECTION_COUNT=$(find "$ARCHIVE_TARGET" -name "status.json" 2>/dev/null | wc -l | tr -d ' ')
    log "  ✓ Archived $SECTION_COUNT section(s)"
  fi
fi

# 3. Remove batch entries from manual review queue
if [[ -f "$QUEUE_FILE" ]]; then
  BEFORE=$(python3 -c "import json; q=json.load(open('$QUEUE_FILE')); print(len(q))" 2>/dev/null || echo "0")
  if [[ "$DRY_RUN" == "true" ]]; then
    WOULD_REMOVE=$(python3 -c "
import json
q=json.load(open('$QUEUE_FILE'))
removed=[x for x in q if x.get('batch_id','')=='$BATCH_ID']
print(len(removed))
" 2>/dev/null || echo "?")
    log "  [DRY RUN] Would remove $WOULD_REMOVE entries for batch $BATCH_ID from queue (queue has $BEFORE entries)"
  else
    python3 << PYEOF
import json, pathlib
qf = pathlib.Path("$QUEUE_FILE")
q = json.loads(qf.read_text())
remaining = [x for x in q if x.get("batch_id", "") != "$BATCH_ID"]
removed = len(q) - len(remaining)
qf.write_text(json.dumps(remaining, indent=2, ensure_ascii=False))
print(f"  Removed {removed} queue entries for batch $BATCH_ID ({len(remaining)} remaining)")
PYEOF
    log "  ✓ Queue updated"
  fi
else
  log "  Queue file not found — no queue cleanup needed"
fi

# 4. Write rollback log
if [[ "$DRY_RUN" == "false" ]]; then
  mkdir -p "$(dirname "$ROLLBACK_LOG")"
  ENTRY="{\"action\":\"rollback\",\"batch_id\":\"$BATCH_ID\",\"timestamp_utc\":\"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\",\"operator\":\"$USER\",\"archive_path\":\"${ARCHIVE_TARGET:-N/A}\"}"
  echo "$ENTRY" >> "$ROLLBACK_LOG"
  log "  ✓ Rollback log entry written"
fi

log ""
if [[ "$DRY_RUN" == "true" ]]; then
  log "DRY RUN COMPLETE — no changes made"
  log "Remove --dry-run to execute the rollback"
else
  log "✓ ROLLBACK COMPLETE"
  log "  Batch $BATCH_ID has been archived and removed from queue"
  log "  Source files (artifacts/audiobook/source/) were NOT touched"
  log "  To re-run: python scripts/audiobook_script/run_comparator_loop.py --batch-id new_batch_$(date +%Y%m%d) ..."
fi
