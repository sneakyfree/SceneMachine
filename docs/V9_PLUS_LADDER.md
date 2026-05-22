# V9+ Experiment Ladder

_Authored 2026-05-21 21:35 PDT by Dr. D Opus 4.7 as part of the autonomous /goal execution. Source-of-truth design doc for Stage 3 video quality elevation._

## Reading the evidence

After V5, V8, V3, and V4-as-broken on RADAR_LOVE_2:

| preset | mechanism | inter_shot_diversity | ref_sim_best_mean | verdict |
|---|---|---:|---:|---|
| V0 | template prompts, T2V everywhere | 0.6191 | 0.5332 | the "slop" baseline |
| V1 | V0 + 30 steps | 0.6130 | 0.5223 | step count doesn't help |
| V5 | V0 + Wan Animate when characters present | 0.7003 | **0.8013** | identity ✓, diversity ✗ (rigid) |
| V8 | Animate only on first appearance per character | 0.6021 | 0.5452 | diversity ✓, identity ✗ (collapsed to V0) |
| V3 | V1 + Qwen-rich LLM prompts | 0.6163 | 0.5207 | indistinguishable from V0/V1 |
| V4 (as-broken) | V1 + I2V continuity routing | (running, predicted V1-equivalent) | predicted ~0.522 | harness limitation: 1 shot/scene means I2V never fires |

**The shape of the problem**: V5 proves the model HAS the capacity to lock identity. V8 proves identity is local-only (one Animate shot doesn't carry). V3 proves prompt richness alone isn't the lever. **The unsolved question: can identity be propagated across T2V shots once Animate has established it on the first shot?**

V4 (when fixed) tests one answer: I2V continuity (visual seeding). The ladder below explores three more.

## The kill criteria

A V9+ experiment is killed if:
- First 10 shots show clear identity drift visible in the rigidity_montage
- SCF metric after 10 shots has `ref_sim_best_mean < 0.55` (worse than V8 = no progress)
- ComfyUI runtime exceeds 12 min/shot (3× baseline = run won't finish overnight)
- Any failure mode that the harness silently masks (PR #96 closes the assembly variant; remaining variants tracked in [[silent-fail-audit]])

## Quality bar (when does the ladder END?)

All metrics from [STRESS_TEST_PLAN.md §0.B] hold on RADAR_LOVE_2:

| metric | target |
|---|---:|
| ref_sim_best_mean | ≥ 0.70 |
| inter_shot_diversity (lower better) | ≤ 0.60 |
| worst-cluster rigidity | < 0.85 |
| per-character self-sim min | ≥ 0.70 |
| assembly success rate | 100% |
| Grant's watch-it grade | ≥ 4/5 |

Once all bars are green on RADAR_LOVE_2: replicate on IMPOSSIBLE_FULL (106 scenes) as the final qualification.

## Prerequisite (blocks the ladder)

**[fix] Harness 1-shot-per-scene limitation** at `scripts/run_benchmark.py:351`:

```python
shot_statuses.append(ShotGenerationStatus(
    shot_id=shot_id, scene_id=sd["scene_number"], status="queued",
))
```

For continuity-using presets, this needs to group shots into chains. Two options:

- **(a) Single-chain mode**: when `preset.use_continuity` is True, all 47 shots share `scene_id="_chain"` so the I2V grouping treats them as one big chain. Cheapest test of the mechanism. Recommended.
- **(b) Multi-shot scene decomposition**: split each scene into N shots based on duration/pacing (real screenplay shot breakdown). More invasive (~30 min code work + tests) but realistic.

Recommended: ship (a) immediately, ship (b) as Stage 4 hardening once V9+ ladder has run.

## V9 — I2V continuity chain (the V4 hypothesis, fixed harness)

- **Hypothesis**: feeding the previous shot's last frame as an I2V seed propagates visual structure including face/composition; identity decays slower than under pure T2V.
- **Mechanism**: harness chain-mode (above), `preset.use_continuity = True`, `preset.use_animate_when_chars = False`. Pipeline already wires `extract_last_frame()` → next shot's `prev_shot_last_frame` → router decides I2V vs T2V based on availability. With chain-mode + use_continuity, after shot 1 every shot routes I2V.
- **Expected outcome**: identity stays higher than V0/V1 (because of the visual seed) but drifts faster than V5 (because the T-pose anchor weakens shot-by-shot). Best-case: ref_sim_best_mean 0.60-0.65, diversity ~0.62. Below the 0.70 identity floor but a meaningful step.
- **Cost**: ~5h on RADAR_LOVE_2 (I2V is slightly slower than T2V).
- **Kill**: if first 10 shots show < 0.55 ref_sim_best_mean.

## V9b — Animate-anchor + I2V chain (the synthesis hypothesis)

- **Hypothesis**: V8's first-appearance Animate gives a STRONG anchor; V9's I2V chain propagates the anchor visually. Combining both should preserve identity longer than either alone.
- **Mechanism**: per character, the FIRST shot routes Animate (V8's logic). All subsequent shots route I2V using the previous shot's last frame (V9's logic). Within a character's chain, identity propagates via image conditioning seeded from the Animate-anchor.
- **Expected outcome**: ref_sim_best_mean 0.70-0.78, diversity 0.62-0.66. Possibly the sweet spot.
- **Cost**: ~5.5h (mix of Animate shots ~14 min + T2V chain shots).
- **Kill**: if V9 lands above 0.65 ref_sim_best_mean, skip V9b and go directly to V10 (LoRA). If V9 underperforms, V9b is the natural next.

## V10 — per-character LoRA injection

- **Hypothesis**: a learned per-character LoRA, trained from each character_ref PNG (4-12 images per char), gives the T2V model a hard identity prior that doesn't decay.
- **Mechanism**: train one LoRA per character via `kohya_ss` or `ai-toolkit` from each `character_refs/{character}.png` (need 4+ refs per char for good convergence). At shot time, attach the LoRA for any character the shot mentions. T2V picks up the identity from the LoRA weight.
- **Expected outcome**: ref_sim_best_mean 0.72-0.85 (LoRAs are strong identity priors). Diversity 0.60-0.66 (LoRA conditions the appearance but doesn't constrain composition). Closest match to "industry-shaking".
- **Cost**: ~30 min LoRA training per character × 7 RADAR_LOVE_2 characters = 3.5h training + ~5h inference. Total ~8.5h.
- **Pre-req**: need ≥4 reference images per character; only 1 currently exists per character (`character_refs/RADAR_LOVE_2/{name}.png`). Need to either (a) generate more refs from the single image via Animate-multi-angle, or (b) accept low-shot LoRA training risk.
- **Kill**: if LoRA loss doesn't converge in 30 min per character, escalate to (a) above.

## V11 — Animate-everywhere + scene-diversification

- **Hypothesis**: V5's 0.700 inter_shot_diversity (rigid) was the failure mode of Animate-everywhere. Maybe with active diversification (prompt jitter, seed variation per shot, scene-type tags), V5's identity can be kept while diversity goes up.
- **Mechanism**: V5 base preset + per-shot prompt augmentation (e.g., "wide angle establishing shot", "close-up on hands", "low angle dramatic") + per-shot seed variation. Animate stays as-is.
- **Expected outcome**: ref_sim_best_mean 0.75-0.82 (slight drop from V5), diversity 0.60-0.66. Trades a little identity for a lot of diversity.
- **Cost**: ~5h, same as V5.
- **Risk**: Animate may not respect prompt augmentations strongly enough; could behave identically to V5.

## V12 — embedding injection (most invasive, highest ceiling)

- **Hypothesis**: extract Animate's CLIP-vision embedding per character on first appearance (free, comes out of the existing Animate workflow). Cache per character. Inject into T2V's text encoder for subsequent shots featuring that character. Identity rides on the embedding, scene composition rides on the prompt.
- **Mechanism**: StackRouter changes (extract embed during Animate shot's post-process, store in `character_refs/{name}.embed.pt`, append to T2V text_encode inputs). Requires ComfyUI workflow modification.
- **Expected outcome**: ref_sim_best_mean 0.75-0.88, diversity 0.55-0.62. Best theoretical ceiling.
- **Cost**: ~2 days infra (workflow + cache + injection plumbing) + ~5h benchmark.
- **Status**: scope-deferred to post-V11 unless V9-V11 all underperform.

## Order of execution (overnight 2026-05-21 → 2026-05-24)

1. **Tonight (already running)**: V4-as-broken finishes ~03:30 → confirms V1-equivalence (control data).
2. **2026-05-22 morning**: harness chain-mode fix → V9 launch → ~5h → analyze.
3. **2026-05-22 afternoon**: V9b launch (if V9 below 0.65) → ~5.5h → analyze.
4. **2026-05-22 night**: V10 LoRA training start (if V9+V9b below 0.72). 3.5h training + 5h inference = wakeup-Saturday.
5. **2026-05-23 morning**: review V10 results. If all bars green → IMPOSSIBLE_FULL run as final qualification. If not → V11.
6. **2026-05-23 afternoon/night**: V11 (Animate + diversification) as fallback.
7. **2026-05-24**: IMPOSSIBLE_FULL qualification + perceptual grading (Grant on return).

V12 deferred unless V9-V11 all fail to clear bars.

## Grant grading checkpoints

Each result lands a `READY_TO_WATCH/V{N}_with_audio.mp4` artifact. Grant grades 1-5 on his "watch-it scale". Metrics inform the design; eyes decide success. When V{N} hits all metric bars AND Grant grades ≥4/5, the ladder exits and we move to IMPOSSIBLE_FULL qualification + Stage 5 polish.

## Risk register specific to V9+

- **GPU thermal**: 5 consecutive overnight runs at 100% utilization may stress the cooling system. Monitor `nvidia-smi --query-gpu=temperature.gpu` periodically; cap at 85°C with auto-throttle.
- **HF disk fill**: each preset's RESULTS.json + final.mp4 pushes to HF. 5 presets × ~40 MB = ~200 MB; well within limits.
- **ComfyUI VRAM leak across runs**: see [[reference-comfyui-server-startup]]. Restart between runs (Stage 3a in `post_v8_sequencer.sh`, PR #92).
- **Harness silent-fail regression**: PR #96 closed three sites; the V9+ ladder relies on no new ones appearing. Stage 2 audit (#27) closes the remaining sites.

## What happens when the ladder concludes

When all §0.B bars green on RADAR_LOVE_2 + IMPOSSIBLE_FULL AND Grant grades ≥4/5:

1. Write final scorecard report comparing V0 → winner.
2. Lock the winning preset's config as the default for new projects.
3. Mark the V9+ track complete; move to Stage 4 hardening + Stage 5 polish.
4. Add the winning preset's perceptual grade to the README.
5. The platform is no longer "embarrassing".
