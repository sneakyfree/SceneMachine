#!/usr/bin/env bash
# wait_and_analyze.sh — block until a benchmark V-tag completes, then run
# the full 3-command analysis pipeline and emit a markdown scorecard.
#
# Composes the tools shipped in PRs #65, #66, #69 into one overnight
# automation. Drop it in the background after kicking off a long
# benchmark run and the morning artifact is ready when the run lands.
#
# Usage (recommended — run in background after starting a benchmark run):
#
#   bash scripts/wait_and_analyze.sh V6a_animate_strength_05 \\
#     /home/user1-gpu/scenemachine_movies/benchmarks/V6a_animate_strength_05 \\
#     > /tmp/wait_and_analyze_V6a.log 2>&1 &
#
# Positional args:
#   $1 = target version tag (e.g. V6a_animate_strength_05). Also the
#        SCF/scorecard's --target-tag (after stripping any suffix past the
#        first underscore so V6a_animate_strength_05 -> V6a).
#   $2 = run directory created by run_benchmark.py (contains
#        <screenplay>/final.mp4 once the run finishes).
#
# Optional env vars:
#   SCREENPLAY        default: RADAR_LOVE_2
#   SHOTS             default: 47
#   REFS_DIR          default: /home/user1-gpu/scenemachine_movies/character_refs/<SCREENPLAY>
#   V0_MP4 / V1_MP4 / V5_MP4 — baselines included in the scorecard
#   POLL_INTERVAL_S   default: 60
#   MAX_WAIT_HOURS    default: 24 (safety stop so this doesn't loop forever)
#   MIN_MP4_BYTES     default: 100000 (don't analyze a stub fallback mp4)
#
# Exit codes:
#   0  scorecard written
#   2  args invalid
#   3  timed out waiting for V-tag mp4
#   4  a downstream tool (SCF / montage / scorecard) failed loud — see log

set -u
set -o pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <V_TAG> <RUN_DIR>" >&2
  exit 2
fi

V_TAG="$1"
RUN_DIR="$2"

SCREENPLAY="${SCREENPLAY:-RADAR_LOVE_2}"
SHOTS="${SHOTS:-47}"
REFS_DIR="${REFS_DIR:-/home/user1-gpu/scenemachine_movies/character_refs/${SCREENPLAY}}"
POLL_INTERVAL_S="${POLL_INTERVAL_S:-60}"
MAX_WAIT_HOURS="${MAX_WAIT_HOURS:-24}"
MIN_MP4_BYTES="${MIN_MP4_BYTES:-100000}"

# Short tag for axis labels (V6a vs V6a_animate_strength_05).
SHORT_TAG="${V_TAG%%_*}"

V0_MP4="${V0_MP4:-/home/user1-gpu/scenemachine_movies/${SCREENPLAY}/final.mp4}"
V1_MP4="${V1_MP4:-/home/user1-gpu/scenemachine_movies/benchmarks/V1_30steps/${SCREENPLAY}/final.mp4}"
V5_MP4="${V5_MP4:-/home/user1-gpu/scenemachine_movies/benchmarks/V5_animate/${SCREENPLAY}/final.mp4}"
TARGET_MP4="${RUN_DIR}/${SCREENPLAY}/final.mp4"

OUT_BASE="${RUN_DIR}/morning_analysis"
SCF_JSON="${OUT_BASE}/scene_context_fidelity_with_${SHORT_TAG}.json"
MONTAGE_DIR="${OUT_BASE}/rigidity_montage_with_${SHORT_TAG}"
SCORECARD_MD="${OUT_BASE}/scorecard_${SHORT_TAG}.md"

mkdir -p "${OUT_BASE}"

echo "[$(date -Iseconds)] wait_and_analyze: V_TAG=${V_TAG} short=${SHORT_TAG}"
echo "[$(date -Iseconds)] wait_and_analyze: polling ${TARGET_MP4} every ${POLL_INTERVAL_S}s"

# Capture start time so we can require the target mp4 was written AFTER we
# started watching. Otherwise stale outputs from previous smoke tests at
# the same path can falsely trigger the analysis pipeline — exactly the
# bug caught during this script's first overnight wiring on V6a.
START_EPOCH=$(date +%s)
deadline=$(( START_EPOCH + MAX_WAIT_HOURS * 3600 ))
echo "[$(date -Iseconds)] requiring target mp4 mtime > ${START_EPOCH} (only accept fresh writes)"

while true; do
  if [[ -f "${TARGET_MP4}" ]]; then
    size=$(stat -c%s "${TARGET_MP4}" 2>/dev/null || echo 0)
    mtime=$(stat -c%Y "${TARGET_MP4}" 2>/dev/null || echo 0)
    if (( size >= MIN_MP4_BYTES )) && (( mtime > START_EPOCH )); then
      echo "[$(date -Iseconds)] target mp4 ready (${size} bytes, mtime=${mtime})"
      break
    fi
  fi
  if (( $(date +%s) >= deadline )); then
    echo "[$(date -Iseconds)] TIMEOUT after ${MAX_WAIT_HOURS}h waiting for ${TARGET_MP4}" >&2
    exit 3
  fi
  sleep "${POLL_INTERVAL_S}"
done

# Stable Python interpreter — system python3 has the SceneMachine deps;
# the ComfyUI venv has cv2 + transformers. The SCF script needs cv2 +
# transformers; the montage + scorecard scripts need pillow + stdlib.
SCF_PY="/opt/ai/comfyui/venv/bin/python"
TOOL_PY="python3"
if [[ ! -x "${SCF_PY}" ]]; then
  echo "[$(date -Iseconds)] SCF python ${SCF_PY} not executable, falling back to ${TOOL_PY}" >&2
  SCF_PY="${TOOL_PY}"
fi

# ------------------------------------------------------------------
# Stage 1 — SCF metric over V0 / V1 / V5 / <target>
# ------------------------------------------------------------------
echo "[$(date -Iseconds)] stage 1: SCF metric -> ${SCF_JSON}"
SCF_ARGS=(
  --tag V0  --mp4 "${V0_MP4}"
  --tag V1  --mp4 "${V1_MP4}"
  --tag V5  --mp4 "${V5_MP4}"
  --tag "${SHORT_TAG}" --mp4 "${TARGET_MP4}"
  --refs "${REFS_DIR}" --shots "${SHOTS}"
  --out "${SCF_JSON}"
)
if ! "${SCF_PY}" scripts/analyze_scene_context_fidelity.py "${SCF_ARGS[@]}"; then
  echo "[$(date -Iseconds)] SCF FAILED — see above" >&2
  exit 4
fi

# ------------------------------------------------------------------
# Stage 2 — rigidity montage with the target row added
# ------------------------------------------------------------------
echo "[$(date -Iseconds)] stage 2: rigidity montage -> ${MONTAGE_DIR}"
MONTAGE_ARGS=(
  --scf-json "${SCF_JSON}"
  --mp4 "V0=${V0_MP4}"
  --mp4 "V1=${V1_MP4}"
  --mp4 "V5=${V5_MP4}"
  --mp4 "${SHORT_TAG}=${TARGET_MP4}"
  --out-dir "${MONTAGE_DIR}"
)
if ! "${TOOL_PY}" scripts/make_rigidity_montage.py "${MONTAGE_ARGS[@]}"; then
  echo "[$(date -Iseconds)] montage FAILED — see above" >&2
  exit 4
fi

# ------------------------------------------------------------------
# Stage 3 — scorecard with auto-recommendation
# ------------------------------------------------------------------
echo "[$(date -Iseconds)] stage 3: scorecard -> ${SCORECARD_MD}"
SCORECARD_ARGS=(
  --scf-json "${SCF_JSON}"
  --montage-dir "${MONTAGE_DIR}"
  --baseline-tag V0
  --target-tag "${SHORT_TAG}"
  --out "${SCORECARD_MD}"
)
if ! "${TOOL_PY}" scripts/v_scorecard.py "${SCORECARD_ARGS[@]}"; then
  echo "[$(date -Iseconds)] scorecard FAILED — see above" >&2
  exit 4
fi

echo "[$(date -Iseconds)] morning analysis complete"
echo "[$(date -Iseconds)] scorecard: ${SCORECARD_MD}"
echo "[$(date -Iseconds)] SCF JSON:  ${SCF_JSON}"
echo "[$(date -Iseconds)] montages:  ${MONTAGE_DIR}"
exit 0
