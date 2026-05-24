# ComfyUI server lifecycle

## What's here

- `comfyui.service` — systemd user unit. Auto-starts ComfyUI on boot.
- `restart-comfyui.sh` — convenience wrapper that kills + restarts ComfyUI when you want fresh VRAM (matches the Stage 3a pattern from `scripts/post_v8_sequencer.sh`).

## Why this exists

Before this, every reboot or session timeout left ComfyUI dead until someone noticed and manually launched it. The 2026-05-19 incident (post-reboot ComfyUI down → 47/47 silent-fails in 1.1s) cost ~30 min of recovery + a failed V8 run. Tracked as P1-12 in `docs/INVENTORY_DEFECTS.md`.

## Install (one-time)

```bash
mkdir -p ~/.config/systemd/user/
cp tools/comfyui/comfyui.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable comfyui.service
systemctl --user start comfyui.service

# Enable lingering so the user unit survives logout / boots
# without a login session.
sudo loginctl enable-linger "$USER"
```

## Operations

### Status

```bash
systemctl --user status comfyui
curl -sf http://127.0.0.1:8188/system_stats | head -c 300
```

### Logs

```bash
journalctl --user -u comfyui -f         # tail
journalctl --user -u comfyui --since '10 min ago'
```

### Restart (clean VRAM)

```bash
bash tools/comfyui/restart-comfyui.sh
```

Or directly:

```bash
systemctl --user restart comfyui
```

### Stop

```bash
systemctl --user stop comfyui
```

## When to restart

- Between heavy benchmark types (Animate → T2V), per the VRAM-leak pattern documented in `reference_comfyui_server_startup.md`. The `post_v8_sequencer.sh` Stage 3a already does this for the V8→V3 chain; do it manually when starting any V_N where the previous run used a different workflow.
- When `nvidia-smi memory.used` is stuck above 5 GB while ComfyUI is idle (a sign the offload manager hasn't released).
- After any CUDA driver upgrade.

## Why a user unit, not system

- Doesn't need root for normal operation.
- Easier to audit/restart from the same login session as the benchmark harness.
- The model files at `/opt/ai/comfyui/` are owned by user1-gpu anyway.

If you do want a system-scoped unit, copy to `/etc/systemd/system/comfyui.service`, change the `WorkingDirectory` ownership, add a `User=user1-gpu` line, and `systemctl enable comfyui` (without `--user`).
