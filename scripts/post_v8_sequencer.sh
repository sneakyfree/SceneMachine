#!/usr/bin/env bash
# post_v8_sequencer.sh — chain V8 completion → Qwen-resume → V3_llm_prompts
# → V3 audio mux, fully autonomous.
#
# Closes the "1 then 2 then 3" loop Grant requested at 02:40 AM 2026-05-18:
#   1. V8_hybrid_routing (running NOW under nohup, ETA ~10:30 AM)
#   2. V3_llm_prompts (gated on V8 finishing + Qwen completing)
#   3. Phase 2 audio mux on V3 output (gated on V3 finishing)
#
# Without this sequencer each step needs a human to notice the prior is
# done. With it, fire-and-forget for the whole chain.
#
# Stages:
#   1. WAIT for V8 final.mp4 mtime > script-start time
#      (already polled by wait_and_analyze_V8 separately, but that script
#       owns the scorecard generation; this script owns the next experiment
#       trigger.)
#   2. RUN qwen --resume on the freed GPU. Fails loud on non-zero exit.
#      Verifies the resulting JSON has at least 47 scenes (no partial).
#   3. RUN V3_llm_prompts benchmark. Standard wallclock ~8h.
#   4. WAIT for V3 final.mp4 mtime > stage-3-start time. Size guard
#      MIN_MP4_BYTES same as wait_and_analyze.sh.
#   5. RUN add_audio_to_movie.py with V3's final.mp4 + the now-complete
#      Qwen prompts JSON. Outputs V3_with_audio.mp4.
#   6. Optionally: same for V8 once both are complete + a comparison run.
#
# Usage (fire under nohup right after kicking off V8):
#   nohup bash scripts/post_v8_sequencer.sh > /tmp/post_v8_sequencer.log 2>&1 &
#   disown $!
#
# Configurable via env vars:
#   SCREENPLAY=RADAR_LOVE_2
#   SHOTS=47
#   V8_RUN_DIR=/home/user1-gpu/scenemachine_movies/benchmarks/V8_hybrid_routing
#   V3_RUN_DIR=/home/user1-gpu/scenemachine_movies/benchmarks/V3_llm_prompts
#   QWEN_JSON=/home/user1-gpu/scenemachine_movies/llm_prompts/RADAR_LOVE_2/qwen2.5-72b.json
#   POLL_INTERVAL_S=60
#   MAX_WAIT_HOURS=24
#   MIN_MP4_BYTES=100000
#   OLLAMA_MODEL=qwen2.5:72b-instruct-q6_K

set -u
set -o pipefail

SCREENPLAY="${SCREENPLAY:-RADAR_LOVE_2}"
SHOTS="${SHOTS:-47}"
V8_RUN_DIR="${V8_RUN_DIR:-/home/user1-gpu/scenemachine_movies/benchmarks/V8_hybrid_routing}"
V3_RUN_DIR="${V3_RUN_DIR:-/home/user1-gpu/scenemachine_movies/benchmarks/V3_llm_prompts}"
QWEN_JSON="${QWEN_JSON:-/home/user1-gpu/scenemachine_movies/llm_prompts/${SCREENPLAY}/qwen2.5-72b.json}"
POLL_INTERVAL_S="${POLL_INTERVAL_S:-60}"
MAX_WAIT_HOURS="${MAX_WAIT_HOURS:-24}"
MIN_MP4_BYTES="${MIN_MP4_BYTES:-100000}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:72b-instruct-q6_K}"

V8_MP4="${V8_RUN_DIR}/${SCREENPLAY}/final.mp4"
V3_MP4="${V3_RUN_DIR}/${SCREENPLAY}/final.mp4"
V8_AUDIO_OUT="${V8_RUN_DIR}/${SCREENPLAY}/V8_with_audio.mp4"
V3_AUDIO_OUT="${V3_RUN_DIR}/${SCREENPLAY}/V3_with_audio.mp4"

REPO=/home/user1-gpu/Desktop/grants_folder/SceneMachine
PY_SM=python3
PY_TTS=/home/user1-gpu/chatterbox-test/venv/bin/python

START_EPOCH=$(date +%s)

log() {
  echo "[$(date -Iseconds)] $*"
}

wait_for_fresh_mp4() {
  local path="$1"
  local label="$2"
  local since_epoch="$3"
  log "${label}: polling ${path} every ${POLL_INTERVAL_S}s (need mtime > ${since_epoch})"
  local deadline=$(( $(date +%s) + MAX_WAIT_HOURS * 3600 ))
  while true; do
    if [[ -f "${path}" ]]; then
      local size mtime
      size=$(stat -c%s "${path}" 2>/dev/null || echo 0)
      mtime=$(stat -c%Y "${path}" 2>/dev/null || echo 0)
      if (( size >= MIN_MP4_BYTES )) && (( mtime > since_epoch )); then
        log "${label}: ready (${size} bytes, mtime=${mtime})"
        return 0
      fi
    fi
    if (( $(date +%s) >= deadline )); then
      log "${label}: TIMEOUT after ${MAX_WAIT_HOURS}h"
      return 3
    fi
    sleep "${POLL_INTERVAL_S}"
  done
}

# ------------------------------------------------------------------
# Stage 1 — Wait for V8 to land
# ------------------------------------------------------------------
log "STAGE 1: waiting for V8 to complete"
if ! wait_for_fresh_mp4 "${V8_MP4}" "V8 final.mp4" "${START_EPOCH}"; then
  log "stage 1 failed"
  exit 3
fi
V8_DONE_EPOCH=$(date +%s)

# Give wait_and_analyze.sh a head start to grab the GPU for SCF / CLIP.
# Tiny pause so the auto-analysis runs before Qwen reloads the GPU.
sleep 30
log "STAGE 1: V8 done; pausing 30s so wait_and_analyze_V8 owns CLIP first"

# ------------------------------------------------------------------
# Stage 2 — Resume Qwen on freed GPU
# ------------------------------------------------------------------
log "STAGE 2: resuming Qwen prompts -> ${QWEN_JSON}"
cd "${REPO}" || exit 4

# pull the script if not on this branch's working tree (we're firing
# from main usually; script lives on PR #68 branch)
if [[ ! -f scripts/generate_llm_prompts.py ]]; then
  git checkout feat/llm-prompt-pipeline -- scripts/generate_llm_prompts.py 2>/dev/null \
    || { log "could not pull generate_llm_prompts.py"; exit 4; }
fi

if ! "${PY_SM}" scripts/generate_llm_prompts.py \
    --screenplay "${SCREENPLAY}" \
    --model "${OLLAMA_MODEL}" \
    --out "${QWEN_JSON}" \
    --resume; then
  log "STAGE 2 FAILED: Qwen --resume returned non-zero"
  exit 4
fi

# Verify the JSON has all SHOTS scenes (i.e. resume actually filled in
# the missing ones). Refuse to launch V3 against a partial JSON since
# the harness consumer fails loud anyway.
scenes_count=$("${PY_SM}" -c "import json,sys; d=json.load(open('${QWEN_JSON}')); print(len(d.get('scenes',{})))")
if (( scenes_count < SHOTS )); then
  log "STAGE 2 FAILED: ${QWEN_JSON} has ${scenes_count} scenes, need >= ${SHOTS}"
  exit 4
fi
log "STAGE 2: Qwen JSON complete (${scenes_count} scenes)"

# ------------------------------------------------------------------
# Stage 3 — Run V3_llm_prompts
# ------------------------------------------------------------------
V3_START_EPOCH=$(date +%s)
log "STAGE 3: launching V3_llm_prompts benchmark"

# pull run_benchmark.py if not present (V3 preset doesn't strictly need
# anything beyond main, since use_llm_prompts is a v0-baseline-era
# field; only the consumer block from PR #68 is needed and that's the
# generate_llm_prompts.py JSON load).
if ! grep -q "llm_prompts_map" scripts/run_benchmark.py 2>/dev/null; then
  log "STAGE 3 WARN: scripts/run_benchmark.py lacks the LLM-prompts consumer "
  log "STAGE 3 WARN: pulling it from feat/llm-prompt-pipeline"
  git checkout feat/llm-prompt-pipeline -- scripts/run_benchmark.py 2>/dev/null \
    || { log "STAGE 3 FAILED: could not pull harness consumer"; exit 4; }
fi

if ! "${PY_SM}" scripts/run_benchmark.py V3_llm_prompts \
    --screenplay "${SCREENPLAY}"; then
  log "STAGE 3 FAILED: V3 benchmark returned non-zero"
  exit 4
fi
log "STAGE 3: V3 benchmark exit 0"

# ------------------------------------------------------------------
# Stage 4 — Wait for V3 final.mp4
# (Should already be ready since stage 3 exits after assembly, but
# size-guard polling is cheap insurance against assembly-race.)
# ------------------------------------------------------------------
log "STAGE 4: confirming V3 final.mp4"
if ! wait_for_fresh_mp4 "${V3_MP4}" "V3 final.mp4" "${V3_START_EPOCH}"; then
  log "stage 4 failed"
  exit 4
fi

# ------------------------------------------------------------------
# Stage 5 — Audio mux V3
# ------------------------------------------------------------------
log "STAGE 5: muxing audio onto V3 -> ${V3_AUDIO_OUT}"
if [[ ! -f scripts/add_audio_to_movie.py ]]; then
  git checkout feat/audio-narration-mvp -- scripts/add_audio_to_movie.py 2>/dev/null \
    || { log "STAGE 5 FAILED: could not pull audio script"; exit 4; }
fi
if ! "${PY_TTS}" scripts/add_audio_to_movie.py \
    --mp4 "${V3_MP4}" \
    --prompts-json "${QWEN_JSON}" \
    --shots "${SHOTS}" \
    --time-mode stretch \
    --out "${V3_AUDIO_OUT}"; then
  log "STAGE 5 FAILED: V3 audio mux returned non-zero"
  exit 4
fi
log "STAGE 5: ${V3_AUDIO_OUT} written"

# ------------------------------------------------------------------
# Stage 6 — Bonus: audio mux V8 (now that Qwen JSON is complete + V8 is on disk)
# ------------------------------------------------------------------
log "STAGE 6: bonus audio mux for V8 -> ${V8_AUDIO_OUT}"
if ! "${PY_TTS}" scripts/add_audio_to_movie.py \
    --mp4 "${V8_MP4}" \
    --prompts-json "${QWEN_JSON}" \
    --shots "${SHOTS}" \
    --time-mode stretch \
    --out "${V8_AUDIO_OUT}"; then
  log "STAGE 6 WARN: V8 audio mux failed (non-fatal — V8 alone is on disk)"
fi
log "STAGE 6: V8_with_audio.mp4 done (or warned)"

log "ALL STAGES COMPLETE"
log "  V8 with audio:  ${V8_AUDIO_OUT}"
log "  V3 with audio:  ${V3_AUDIO_OUT}"
log "  Qwen prompts:   ${QWEN_JSON}"
exit 0
