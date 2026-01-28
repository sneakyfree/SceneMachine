# SceneMachine User Guide
## Complete Walkthrough: Screenplay to Movie

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Screenplay Import](#screenplay-import)
3. [Character Laboratory](#character-laboratory)
4. [Scene Planning](#scene-planning)
5. [Video Generation](#video-generation)
6. [Timeline & Assembly](#timeline-assembly)
7. [Export & Publishing](#export-publishing)
8. [Explainability Dashboard](#explainability-dashboard)
9. [Troubleshooting FAQ](#troubleshooting-faq)

---

## Getting Started

### System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 16 GB | 32 GB |
| GPU | RTX 3080 (10GB) | RTX 4090/5090 (24GB) |
| Storage | 50 GB | 200 GB SSD |

### Quick Start

1. **Launch SceneMachine** - Open the desktop application
2. **Create New Project** - Click "New Project" on the home screen
3. **Import Screenplay** - Upload your .fountain, .fdx, or .pdf script
4. **Setup Characters** - Define appearance and voice for each character
5. **Generate** - Click "Generate Movie" to start the AI pipeline
6. **Export** - Download your finished movie

---

## Screenplay Import

### Supported Formats

| Format | Extension | Best For |
|--------|-----------|----------|
| Fountain | `.fountain` | Indie writers, open-source tools |
| Final Draft | `.fdx` | Professional screenwriters |
| PDF | `.pdf` | Any screenplay exported as PDF |
| Plain Text | `.txt` | Simple scripts, quick tests |

### Import Wizard Steps

#### Step 1: Upload Your Script

1. Click **"Import Screenplay"** on the project page
2. Drag and drop your file, or click to browse
3. Wait for automatic format detection

#### Step 2: Parsing Preview

The AI parses your screenplay and shows:
- **Title** - Extracted title from the script
- **Scene Count** - Number of scenes detected
- **Characters** - List of speaking characters
- **Estimated Runtime** - Based on page count

**Review and confirm** the extracted information is correct.

#### Step 3: Fix Any Issues

If parsing encounters problems:
- **Missing character names** - Add manually
- **Scene boundaries unclear** - Adjust scene breaks
- **Format errors** - Use the inline editor to fix

> **Tip:** Fountain format (.fountain) produces the most reliable parsing results.

---

## Character Laboratory

The Character Lab is where you define and lock character appearances for consistent generation.

### Creating a Character

1. Navigate to **Character Lab** from the sidebar
2. Click **"Add Character"**
3. Fill in details:
   - **Name** - Character's name as it appears in the script
   - **Description** - Physical appearance, age, traits
   - **Personality** - Key characteristics for voice/expression

### Setting Up Reference Images

**Option A: Upload Reference**
1. Click **"Upload Reference"**
2. Select a clear headshot or portrait
3. The AI extracts face embeddings automatically

**Option B: AI Generation**
1. Click **"Generate with AI"**
2. Review the prompt based on your description
3. Select the best generated portrait
4. Lock the character appearance

### Voice Profile Setup

1. Click **"Select Voice"** on the character card
2. Choose from library voices (Kokoro TTS) or
3. **Clone a voice:**
   - Upload a 10-30 second audio sample
   - Clear speech, minimal background noise
   - The AI creates a custom voice clone

### Locking Characters

When satisfied with appearance and voice:
1. Click **"Lock Character"** ✅
2. This ensures consistency across all generated shots
3. Locked characters cannot be modified during generation

---

## Scene Planning

### Shot Breakdown

Each scene is broken down into individual shots:

| Shot Type | Description |
|-----------|-------------|
| Wide | Establishing shot showing location |
| Medium | Waist-up view of characters |
| Close-up | Face or detail focus |
| Over-shoulder | Conversation perspective |
| POV | Character's point of view |

### Editing Shots

1. Click on any shot card to edit
2. Modify:
   - **Description** - What happens in the shot
   - **Camera Angle** - Wide, medium, close, etc.
   - **Characters** - Who appears in this shot
   - **Duration** - Estimated length in seconds
3. Click **"Save"** to confirm changes

### Blockers Panel

The **Blockers Panel** shows issues that need resolution:

| Severity | Meaning | Action |
|----------|---------|--------|
| 🔴 Critical | Blocks generation | Must fix |
| 🟡 High | Quality risk | Should fix |
| 🔵 Medium | Minor issue | Optional |

Click any blocker to see the **Unlocker** - a suggested fix with estimated time.

---

## Video Generation

### Quality Settings

| Quality | Resolution | Speed | Cost |
|---------|------------|-------|------|
| Draft | 480p | Fast | $ |
| Standard | 720p | Medium | $$ |
| Premium | 1080p | Slow | $$$ |

### Starting Generation

1. Review **Cost Estimate** in the dashboard
2. Check that all **Critical Blockers** are resolved
3. Click **"Start Generation"**
4. Approve the human-in-the-loop confirmation

### Monitoring Progress

The **Generation Queue** shows:
- Current phase (Parse → Characters → Generate → Review → Assemble)
- Progress percentage per shot
- Estimated time remaining
- Cost tracking in real-time

### Quality Review

After generation, the **Reviewer Agent** checks each shot for:
- Physics violations
- Lip-sync accuracy
- Character consistency
- Visual artifacts

Failed shots can be **regenerated** individually.

---

## Timeline & Assembly

### Timeline Editor

The timeline shows all generated clips arranged by scene:

- **Drag and drop** to reorder clips
- **Trim** clips by dragging edges
- **Add transitions** between clips (fade, dissolve, wipe)

### Audio Mixing

The **Audio Mixer** panel lets you:
- Adjust dialogue volume per character
- Add ambient/background audio
- Set music tracks and levels
- **Normalize** audio for consistent levels

### Transitions

Available transitions:
- Fade (in/out)
- Dissolve (cross-fade)
- Wipe (directional)
- Cut (instant)

---

## Export & Publishing

### Export Formats

| Format | Use Case |
|--------|----------|
| MP4 (H.264) | Universal compatibility |
| MOV (ProRes) | Professional editing |
| WebM (VP9) | Web distribution |

### Export Presets

| Preset | Resolution | Bitrate | Best For |
|--------|------------|---------|----------|
| YouTube | 1080p | 12 Mbps | YouTube upload |
| Social | 720p | 8 Mbps | Instagram, TikTok |
| Archive | 4K | 50 Mbps | Master copy |

### Exporting

1. Click **"Export"** in the top menu
2. Select preset or customize settings
3. Choose output location
4. Click **"Start Export"**
5. Download when complete

---

## Explainability Dashboard

SceneMachine provides 4 views of the generation process:

### Client View 👤
- Plain language status updates
- "Your movie is 75% complete"
- Visual preview of results

### Operator View 🎬
- Shot-by-shot progress
- Phase timeline (Parse → Generate → Assemble)
- Cost tracking

### Technical View 🔧
- Action logs from all agents
- Confidence scores
- Model parameters
- Error traces

### Audit View 📋
- Immutable snapshots
- Version history
- Delta reports (what changed)
- Export for compliance

---

## Troubleshooting FAQ

### Q: Screenplay won't parse correctly

**A:** Try these steps:
1. Ensure proper Fountain/FDX formatting
2. Check for special characters in character names
3. Use the "Paste Text" fallback option
4. Contact support with your file for analysis

### Q: Characters look different between shots

**A:** Ensure character is **locked** ✅:
1. Go to Character Lab
2. Check the lock icon is green
3. If unlocked, lock before regenerating
4. Consider updating the reference image

### Q: Lip-sync is off

**A:** Common causes:
1. Audio quality issues - re-record dialogue
2. Face angle too extreme - use frontal shots
3. Try regenerating the specific shot
4. Check audio timing in timeline

### Q: Generation is slow

**A:** Improve speed:
1. Use Draft quality for previews
2. Enable cloud burst (Settings → Compute)
3. Close other GPU-intensive applications
4. Consider upgrading GPU

### Q: Cost is too high

**A:** Reduce costs:
1. Use Draft quality for iterations
2. Generate only critical scenes first
3. Fix blockers before generating
4. Use preview mode before full generation

### Q: Export fails

**A:** Troubleshooting:
1. Check available disk space
2. Try a different export format
3. Reduce bitrate/resolution
4. Check FFmpeg logs in Technical View

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New Project |
| `Ctrl+S` | Save Project |
| `Ctrl+G` | Start Generation |
| `Space` | Play/Pause Preview |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `Shift+F` | Send Feedback |
| `?` | Show All Shortcuts |

---

## Support

- **Documentation:** https://docs.scenemachine.ai
- **Community:** https://community.scenemachine.ai
- **Email:** support@scenemachine.ai

---

*Last Updated: January 2026*
