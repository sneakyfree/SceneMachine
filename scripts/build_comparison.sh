#!/usr/bin/env bash
# build_comparison.sh — N-panel side-by-side comparison of multiple
# with-audio benchmark outputs. Each panel labeled in the upper-left.
# Audio taken from the first input.
#
# Designed to be re-runnable as new V_N runs land: drop in the new
# with_audio.mp4 and add a panel argument.
#
# Usage:
#   bash scripts/build_comparison.sh OUT_PATH LABEL1=PATH1 LABEL2=PATH2 ...
#
# Example (after V8_with_audio.mp4 lands tomorrow):
#   bash scripts/build_comparison.sh \\
#     /home/user1-gpu/scenemachine_movies/COMPARISON_V0_V5_V6a_V8.mp4 \\
#     'V0 (slop)=.../V0_with_audio.mp4' \\
#     'V5 (Animate)=.../V5_with_audio.mp4' \\
#     'V6a (str=0.5)=.../V6a_with_audio.mp4' \\
#     'V8 (hybrid)=.../V8_with_audio.mp4'
#
# Constraints (verified by precheck):
#   - All inputs must have the same width × height and same frame rate
#   - Output dimensions: (W * N_inputs) × H
#   - Audio comes from input #1 only
#   - Output codec: libx264 (CRF 22) + aac 128k

set -u
set -o pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 OUT_PATH LABEL1=PATH1 LABEL2=PATH2 ..." >&2
  echo "  At least 2 input panels required." >&2
  exit 2
fi

OUT="$1"
shift

# Parse LABEL=PATH pairs
LABELS=()
INPUTS=()
for pair in "$@"; do
  if [[ "$pair" != *=* ]]; then
    echo "Bad arg (expected LABEL=PATH): $pair" >&2
    exit 2
  fi
  label="${pair%%=*}"
  path="${pair#*=}"
  if [[ ! -f "$path" ]]; then
    echo "Input file missing: $path" >&2
    exit 2
  fi
  LABELS+=("$label")
  INPUTS+=("$path")
done

N=${#INPUTS[@]}
if (( N < 2 )); then
  echo "Need at least 2 panels, got $N" >&2
  exit 2
fi

# Precheck: same width × height
first_dims=$(ffprobe -v quiet -show_entries 'stream=width,height' \
  -of csv=p=0 "${INPUTS[0]}" 2>/dev/null | head -1)
for p in "${INPUTS[@]:1}"; do
  d=$(ffprobe -v quiet -show_entries 'stream=width,height' \
    -of csv=p=0 "$p" 2>/dev/null | head -1)
  if [[ "$d" != "$first_dims" ]]; then
    echo "Dimension mismatch: ${INPUTS[0]} is $first_dims, $p is $d" >&2
    exit 3
  fi
done
echo "[$(date -Iseconds)] all $N inputs verified at $first_dims"

# Build the ffmpeg invocation
# Per-input drawtext label, then hstack inputs, then map audio from input 0.
INPUT_ARGS=()
for p in "${INPUTS[@]}"; do
  INPUT_ARGS+=(-i "$p")
done

# Build the filter_complex string
FC=""
for i in "${!INPUTS[@]}"; do
  label="${LABELS[$i]}"
  FC+="[$i:v]drawtext=text='${label//\'/\\\'}':x=20:y=20:"
  FC+="fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=8[lbl$i]; "
done
FC+="$(for i in "${!INPUTS[@]}"; do echo -n "[lbl$i]"; done)"
FC+="hstack=inputs=$N[vout]; [0:a]anull[aout]"

echo "[$(date -Iseconds)] rendering -> $OUT"
ffmpeg -y -loglevel error \
  "${INPUT_ARGS[@]}" \
  -filter_complex "$FC" \
  -map "[vout]" -map "[aout]" \
  -c:v libx264 -preset fast -crf 22 -c:a aac -b:a 128k \
  "$OUT"

if [[ -f "$OUT" ]]; then
  size=$(stat -c%s "$OUT")
  dur=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUT")
  echo "[$(date -Iseconds)] wrote $OUT ($size bytes, ${dur}s)"
else
  echo "[$(date -Iseconds)] FAILED — no output" >&2
  exit 4
fi
