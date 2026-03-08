#!/usr/bin/env bash
set -euo pipefail

# Safe cleanup for self-hosted runner diagnostics + old batch artifacts.
# Intended for scheduled maintenance.

RUNNER_DIR="${RUNNER_DIR:-/Users/ahjan/Qwen-Agent/actions-runner}"
REPO_DIR="${REPO_DIR:-/Users/ahjan/phoenix_omega/Qwen-Agent}"
DIAG_KEEP_DAYS="${DIAG_KEEP_DAYS:-14}"
ARTIFACT_KEEP_DAYS="${ARTIFACT_KEEP_DAYS:-14}"

echo "[cleanup] start ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[cleanup] runner_dir=$RUNNER_DIR repo_dir=$REPO_DIR"
echo "[cleanup] diag_keep_days=$DIAG_KEEP_DAYS artifact_keep_days=$ARTIFACT_KEEP_DAYS"

if [ -d "$RUNNER_DIR/_diag" ]; then
  find "$RUNNER_DIR/_diag" -type f -name '*.log' -mtime "+${DIAG_KEEP_DAYS}" -print -delete
fi

if [ -d "$REPO_DIR/artifacts/localization/batch_runs" ]; then
  find "$REPO_DIR/artifacts/localization/batch_runs" -mindepth 1 -maxdepth 1 -type d -mtime "+${ARTIFACT_KEEP_DAYS}" -print -exec rm -rf {} +
fi

if [ -d "$REPO_DIR/artifacts/audiobook" ]; then
  find "$REPO_DIR/artifacts/audiobook" -mindepth 1 -maxdepth 1 -type d -mtime "+${ARTIFACT_KEEP_DAYS}" -print -exec rm -rf {} +
fi

echo "[cleanup] done"
