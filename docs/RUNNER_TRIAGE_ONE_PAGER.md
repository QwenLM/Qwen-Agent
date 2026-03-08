# Runner Triage (One Pager)

Use this when a self-hosted run hangs, loses communication, or times out.

## 1) Confirm runner is online

```bash
cd /Users/ahjan/Qwen-Agent/actions-runner
./svc.sh status
```

If not started:

```bash
./svc.sh stop || true
./svc.sh start
./svc.sh status
```

## 2) Check latest runner errors

```bash
cd /Users/ahjan/Qwen-Agent/actions-runner
tail -n 120 _diag/$(ls -t _diag | head -n 1)
```

If you see repeated `BrokerServer`, `timed out`, or `Operation canceled`, treat as network instability and restart runner service.

## 3) Check LM Studio health before any heavy job

```bash
curl -sS http://127.0.0.1:1234/v1/models | head -c 400; echo
time curl -sS http://127.0.0.1:1234/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3-14b","messages":[{"role":"user","content":"ok"}],"max_tokens":8,"temperature":0.0}'
```

If chat completion takes too long or fails, restart LM Studio and retry.

## 4) Run smallest proof first

1. `Audiobook regression` with `full_golden=false`.
2. Single locale shard (`locale=zh-TW`).
3. Full matrix only after both pass.

## 5) Never overlap heavy jobs

Run only one heavy class at a time:

- `Audiobook regression` full-golden
- `Audiobook scheduled (Qwen-only)` comparator step
- `Locale max-agents run` in translate mode

Hard enforcement now exists:
- LM lock (`scripts/lm_studio_lock.py`) for heavy/medium workloads
- UTC windows (`config/runner/heavy_windows.yaml`) checked by `scripts/runner/heavy_window_guard.py`

## 6) If scheduled run fails from runner disconnect

1. Restart runner service.
2. Verify LM health and warmup.
3. Re-run manual dispatch of the same workflow once.
4. If second attempt fails, switch to shard runs and capture artifact links.

## 7) Evidence required after fix

- Run URL(s)
- Artifact digest(s)
- Commit SHA used
- Note whether failure was runner, network, or LM stall

## 8) Current heavy windows (UTC)

- `regression`: `03:00–10:00`
- `localization`: `15:00–23:00`
- `scheduled_comparator`: `00:00–03:00` and `12:00–15:00`
