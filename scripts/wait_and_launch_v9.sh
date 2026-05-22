#!/usr/bin/env bash
# wait_and_launch_v9.sh — fire V9_continuity_chain after V4 finishes.
#
# Polls for benchmarks/V4_continuity/RADAR_LOVE_2/final.mp4 to land (size
# guard via MIN_MP4_BYTES). Then:
#   1. Restart ComfyUI (per PR #92 Stage 3a — V4 used T2V+I2V models;
#      V9 will also use both, so a clean VRAM state reduces leak risk).
#   2. Launch V9_continuity_chain on RADAR_LOVE_2.
#   3. Launch wait_and_analyze for V9.
#
# Both V4 and the new V9 use ``use_continuity=True`` and the chain-mode
# logic (PR #99). V4 was the BROKEN baseline (1-shot-per-scene); V9 is
# the FIXED single-chain version that proves whether I2V continuity can
# carry identity across shots.
#
# Usage (fire under nohup right after kicking off V4):
#   nohup bash scripts/wait_and_launch_v9.sh > /tmp/launch_v9.log 2>&1 &
#   disown $!
#
# Configurable env vars:
#   SCREENPLAY=RADAR_LOVE_2
#   V4_RUN_DIR=/home/user1-gpu/scenemachine_movies/benchmarks/V4_continuity
#   POLL_INTERVAL_S=60
#   MAX_WAIT_HOURS=24
#   MIN_MP4_BYTES=100000

set -u
set -o pipefail

SCREENPLAY="${SCREENPLAY:-RADAR_LOVE_2}"
V4_RUN_DIR="${V4_RUN_DIR:-/home/user1-gpu/scenemachine_movies/benchmarks/V4_continuity}"
V4_MP4="${V4_RUN_DIR}/${SCREENPLAY}/final.mp4"
POLL_INTERVAL_S="${POLL_INTERVAL_S:-60}"
MAX_WAIT_HOURS="${MAX_WAIT_HOURS:-24}"
MIN_MP4_BYTES="${MIN_MP4_BYTES:-100000}"

REPO=/home/user1-gpu/Desktop/grants_folder/SceneMachine
LOGS=/home/user1-gpu/scenemachine_movies/_logs
START_EPOCH=$(date +%s)

log() {
  echo "[$(date -Iseconds)] $*"
}

# ------------------------------------------------------------------
# Stage 1 — Wait for V4 final.mp4
# ------------------------------------------------------------------
log "STAGE 1: polling ${V4_MP4} every ${POLL_INTERVAL_S}s (mtime > ${START_EPOCH})"
deadline=$(( START_EPOCH + MAX_WAIT_HOURS * 3600 ))
while true; do
  if [[ -f "${V4_MP4}" ]]; then
    size=$(stat -c%s "${V4_MP4}" 2>/dev/null || echo 0)
    mtime=$(stat -c%Y "${V4_MP4}" 2>/dev/null || echo 0)
    if (( size >= MIN_MP4_BYTES )) && (( mtime > START_EPOCH )); then
      log "STAGE 1: V4 final.mp4 ready (${size} bytes, mtime=${mtime})"
      break
    fi
  fi
  if (( $(date +%s) >= deadline )); then
    log "STAGE 1 TIMEOUT after ${MAX_WAIT_HOURS}h"
    exit 3
  fi
  sleep "${POLL_INTERVAL_S}"
done

# ------------------------------------------------------------------
# Stage 2 — Restart ComfyUI for clean VRAM
# ------------------------------------------------------------------
log "STAGE 2: restarting ComfyUI to drop any pinned weights"
pkill -TERM -f "/opt/ai/comfyui/venv/bin/python main.py" 2>/dev/null || true
sleep 5
pkill -KILL -f "/opt/ai/comfyui/venv/bin/python main.py" 2>/dev/null || true

# Wait for VRAM to drop.
vram_deadline=$(( $(date +%s) + 60 ))
while (( $(date +%s) < vram_deadline )); do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
  if (( used < 2000 )); then
    log "STAGE 2: VRAM dropped to ${used} MiB"
    break
  fi
  sleep 2
done

CFY_LOG="${LOGS}/comfyui_v9_$(date +%Y-%m-%d).log"
( cd /opt/ai/comfyui && \
  nohup /opt/ai/comfyui/venv/bin/python main.py --listen 127.0.0.1 --port 8188 > "${CFY_LOG}" 2>&1 & disown )

# Wait for ComfyUI ready.
cfy_deadline=$(( $(date +%s) + 120 ))
while (( $(date +%s) < cfy_deadline )); do
  if curl -sf -m 2 http://127.0.0.1:8188/system_stats > /dev/null 2>&1; then
    log "STAGE 2: ComfyUI ready at $(date -Iseconds)"
    break
  fi
  sleep 2
done
if ! curl -sf -m 2 http://127.0.0.1:8188/system_stats > /dev/null 2>&1; then
  log "STAGE 2 FAILED: ComfyUI didn't come back within 120s"
  exit 4
fi

# ------------------------------------------------------------------
# Stage 3 — Launch V9_continuity_chain
# ------------------------------------------------------------------
V9_START_EPOCH=$(date +%s)
V9_LOG="${LOGS}/v9_run_$(date +%Y-%m-%d).log"
log "STAGE 3: launching V9_continuity_chain → ${V9_LOG}"
cd "${REPO}"

nohup python3 scripts/run_benchmark.py V9_continuity_chain --screenplay "${SCREENPLAY}" \
  > "${V9_LOG}" 2>&1 &
V9_PID=$!
disown ${V9_PID}
log "STAGE 3: V9 launched as PID ${V9_PID}"

# Give it a few seconds to start writing.
sleep 8
if ! ps -p ${V9_PID} > /dev/null; then
  log "STAGE 3 FAILED: V9 process died immediately; check ${V9_LOG}"
  tail -30 "${V9_LOG}" | sed 's/^/  /'
  exit 4
fi

# ------------------------------------------------------------------
# Stage 4 — Launch wait_and_analyze for V9
# ------------------------------------------------------------------
WA_LOG="${LOGS}/wait_and_analyze_v9_$(date +%Y-%m-%d).log"
log "STAGE 4: launching wait_and_analyze_V9 → ${WA_LOG}"
nohup bash scripts/wait_and_analyze.sh V9_continuity_chain \
  /home/user1-gpu/scenemachine_movies/benchmarks/V9_continuity_chain \
  > "${WA_LOG}" 2>&1 &
WA_PID=$!
disown ${WA_PID}
log "STAGE 4: wait_and_analyze_V9 launched as PID ${WA_PID}"

log "ALL STAGES COMPLETE — V9 chain is running"
log "  V9 PID: ${V9_PID}"
log "  V9 log: ${V9_LOG}"
log "  wait_and_analyze PID: ${WA_PID}"
log "  wait_and_analyze log: ${WA_LOG}"
log "  ETA V9 final.mp4: ~5h from now (47 shots × ~6:30 each)"
exit 0
