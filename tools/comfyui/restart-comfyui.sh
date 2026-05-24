#!/usr/bin/env bash
# restart-comfyui.sh — kill + restart ComfyUI for clean VRAM.
#
# Matches the Stage 3a pattern from scripts/post_v8_sequencer.sh (PR
# #92): SIGTERM → SIGKILL → wait for VRAM drop → relaunch → wait for
# /system_stats 200. Use when switching workflow types (Animate→T2V
# in particular) leaves model weights pinned and the next request
# OOMs.
#
# Prefer ``systemctl --user restart comfyui`` if the systemd unit is
# installed and running; this script is a fallback for when the unit
# isn't installed or when you want the explicit VRAM-drop polling.

set -u
set -o pipefail

log() {
  echo "[$(date -Iseconds)] $*"
}

log "killing any running ComfyUI process"
pkill -TERM -f "/opt/ai/comfyui/venv/bin/python main.py" 2>/dev/null || true
sleep 5
pkill -KILL -f "/opt/ai/comfyui/venv/bin/python main.py" 2>/dev/null || true

log "waiting for VRAM to drop below 2 GiB (cuda contexts release on process exit)"
deadline=$(( $(date +%s) + 60 ))
while (( $(date +%s) < deadline )); do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
  if (( used < 2000 )); then
    log "VRAM dropped to ${used} MiB"
    break
  fi
  sleep 2
done

# Prefer the systemd unit if installed.
if systemctl --user is-enabled comfyui >/dev/null 2>&1; then
  log "systemd unit detected — using systemctl --user restart"
  systemctl --user restart comfyui
else
  log "systemd unit not installed — launching directly via nohup"
  LOG=/home/user1-gpu/scenemachine_movies/_logs/comfyui_$(date +%Y-%m-%d).log
  ( cd /opt/ai/comfyui && \
    nohup /opt/ai/comfyui/venv/bin/python main.py --listen 127.0.0.1 --port 8188 \
      > "${LOG}" 2>&1 & disown )
fi

log "waiting for /system_stats to return 200 (cold boot ~15-25s)"
cfy_deadline=$(( $(date +%s) + 120 ))
while (( $(date +%s) < cfy_deadline )); do
  if curl -sf -m 2 http://127.0.0.1:8188/system_stats > /dev/null 2>&1; then
    log "ComfyUI ready"
    nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader
    exit 0
  fi
  sleep 2
done
log "TIMEOUT — ComfyUI didn't return within 120s"
exit 4
