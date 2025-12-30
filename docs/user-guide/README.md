# SceneMachine User Guide

Welcome to SceneMachine! This guide will walk you through using the application to transform your screenplays into AI-generated video content.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Your First Project](#creating-your-first-project)
3. [Uploading a Screenplay](#uploading-a-screenplay)
4. [Working with Characters](#working-with-characters)
5. [Scene Planning](#scene-planning)
6. [Video Generation](#video-generation)
7. [Exporting Your Movie](#exporting-your-movie)
8. [Settings & Configuration](#settings--configuration)
9. [Keyboard Shortcuts](#keyboard-shortcuts)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### System Requirements

- **Operating System**: Windows 10+, macOS 11+, or Linux (Ubuntu 20.04+)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB free space for application and generated content
- **Internet**: Required for AI services

### Installation

1. Download the installer for your platform
2. Run the installer and follow the prompts
3. Launch SceneMachine from your applications

### First Launch

On first launch, you'll see the onboarding wizard:

1. **Welcome**: Overview of SceneMachine features
2. **API Keys**: Configure your AI provider keys
3. **Workflow**: Learn how the process works
4. **Get Started**: Create your first project

---

## Creating Your First Project

### From the Projects Page

1. Click **"New Project"** or press `Ctrl+N`
2. Enter a **project name** (e.g., "My Short Film")
3. Optionally add a **description**
4. Click **"Create"**

### Project States

Projects progress through several states:

| State | Description |
|-------|-------------|
| Empty | New project, no content |
| Screenplay Uploaded | Screenplay file added |
| Analyzed | AI analysis complete |
| Characters Defined | Character appearances set |
| Shots Planned | Scene breakdowns ready |
| Generating | Video generation in progress |
| Exported | Final video created |

---

## Uploading a Screenplay

### Supported Formats

- **Fountain** (`.fountain`) - Plain text screenplay format
- **Final Draft** (`.fdx`) - Industry standard format

### How to Upload

1. Open your project
2. Click **"Upload Screenplay"** or drag & drop your file
3. Wait for parsing to complete
4. Review the extracted content

### After Upload

SceneMachine will automatically:
- Extract the title and author
- Identify all scenes
- List all characters with dialogue
- Count page numbers

---

## Working with Characters

### Character List

After uploading, navigate to the **Characters** tab to see all extracted characters.

Each character shows:
- Name
- Number of scenes they appear in
- Role (protagonist, antagonist, supporting)
- Lock status

### Defining Character Appearance

1. Click on a character to edit
2. Fill in the **Appearance** section:
   - Physical description
   - Age
   - Gender
   - Distinctive features
3. Optionally upload **Reference Images**
4. Click **"Save"**

### Assigning Voices

1. In the character editor, scroll to **Voice Settings**
2. Select a **TTS Provider** (ElevenLabs, OpenAI, etc.)
3. Choose a **Voice** from the dropdown
4. Click **"Preview"** to hear the voice
5. Click **"Assign"** to confirm

### Locking Characters

Lock characters to ensure visual consistency:

| Lock State | Meaning |
|------------|---------|
| Unlocked | Can be edited freely |
| Partial | Appearance defined, but flexible |
| Locked | Fixed appearance for generation |

Click the **lock icon** to toggle lock state.

---

## Scene Planning

### Scene List

Navigate to the **Scenes** tab to view all scenes from your screenplay.

Each scene shows:
- Scene number and heading
- Location and time of day
- Characters present
- Number of shots

### Generating Shot Breakdowns

1. Select a scene
2. Click **"Generate Breakdown"**
3. AI will analyze the scene and suggest shots
4. Review and edit as needed

### Shot Types

| Type | Description |
|------|-------------|
| WIDE | Establishes location, full setting |
| MEDIUM | Characters from waist up |
| CLOSE | Face/detail focused |
| EXTREME_CLOSE | Specific detail |
| OVER_SHOULDER | POV from behind character |
| POV | First-person perspective |
| INSERT | Object or detail shot |

### Editing Shots

Click any shot to edit:
- **Shot Type**: Camera framing
- **Camera Movement**: Static, pan, dolly, etc.
- **Duration**: Length in seconds
- **Description**: What happens in the shot
- **Generation Prompt**: Custom AI prompt

### Reordering Shots

Drag and drop shots to reorder them within a scene.

---

## Video Generation

### Starting Generation

1. Navigate to the **Generate** tab
2. Select shots or scenes to generate
3. Click **"Start Generation"**

### Generation Queue

The queue shows:
- Pending shots
- Currently generating
- Completed shots
- Failed shots (with retry option)

### Progress Tracking

Each shot shows:
- Thumbnail (when complete)
- Progress percentage
- Estimated time remaining
- Provider used

### Retrying Failed Shots

If a shot fails:
1. Click the **"Retry"** button
2. Or right-click and select **"Regenerate"**
3. Consider adjusting the prompt if issues persist

---

## Exporting Your Movie

### Preview

Before exporting:
1. Go to **Export** tab
2. Click **"Preview All"** to watch assembled footage
3. Check for issues or needed adjustments

### Export Settings

Configure your export:

| Setting | Options |
|---------|---------|
| Format | MP4 (H.264), MOV (ProRes), WebM |
| Resolution | 720p, 1080p, 1440p, 4K |
| Quality | Draft, Standard, High, Master |
| Frame Rate | 24, 25, 30, 60 fps |

### Exporting

1. Choose your settings
2. Select output location
3. Click **"Export"**
4. Wait for processing to complete

### Export Contents

The final export includes:
- All generated video shots
- Assembled scenes
- Dialogue audio (if TTS enabled)
- Background music (if configured)

---

## Settings & Configuration

### Accessing Settings

Press `Ctrl+,` or click **Settings** in the sidebar.

### API Keys

Configure keys for AI services:

| Provider | Purpose |
|----------|---------|
| Anthropic | Screenplay analysis, prompts |
| OpenAI | Alternative LLM, TTS |
| ElevenLabs | Voice synthesis |
| Replicate | Video generation |
| Fal.ai | Video generation |
| RunwayML | Video generation |

### Generation Settings

- **Default LLM Provider**: For screenplay analysis
- **Default Video Provider**: For shot generation
- **Resolution**: Default output resolution
- **Frame Rate**: Default fps
- **Concurrent Generations**: Parallel jobs

### Appearance

- **Theme**: Dark, Light, or System
- **Auto-save**: Enable/disable automatic saving
- **Advanced Options**: Show/hide advanced features

### Storage

- View storage usage
- Clear cache files
- Set max cache size

---

## Keyboard Shortcuts

### Navigation

| Shortcut | Action |
|----------|--------|
| `Ctrl+H` | Go to Home/Projects |
| `Ctrl+,` | Open Settings |
| `Ctrl+B` | Toggle Sidebar |
| `?` | Show Shortcuts |

### Project Navigation

| Shortcut | Action |
|----------|--------|
| `Ctrl+1` | Project Overview |
| `Ctrl+2` | Characters |
| `Ctrl+3` | Scene Planning |
| `Ctrl+4` | Generation |
| `Ctrl+5` | Export |

### General

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save |
| `Escape` | Close/Cancel |

---

## Troubleshooting

### Common Issues

#### "API Key Invalid"

1. Go to Settings → API Keys
2. Click "Test" next to the provider
3. Re-enter your key if needed
4. Check your provider account for issues

#### "Generation Failed"

1. Check your API key status
2. Review the error message
3. Try simplifying the generation prompt
4. Check provider service status

#### "Screenplay Parse Error"

1. Ensure correct file format (.fountain or .fdx)
2. Check for formatting issues in the file
3. Try opening in a screenplay editor first

#### "Export Stuck"

1. Check available disk space
2. Cancel and try with lower quality
3. Export individual scenes first

### Getting Help

- **Documentation**: Check docs at scenemachine.ai/docs
- **Support**: Email support@scenemachine.ai
- **Community**: Join our Discord server
- **Issues**: Report bugs on GitHub

### Logs

Find application logs at:
- **Windows**: `%APPDATA%\SceneMachine\logs`
- **macOS**: `~/Library/Logs/SceneMachine`
- **Linux**: `~/.config/scenemachine/logs`

---

## Tips & Best Practices

### Writing for AI Generation

1. **Be Specific**: Detailed descriptions help AI
2. **Keep It Simple**: Complex action may not render well
3. **Visual Focus**: Describe what can be seen

### Character Consistency

1. Define detailed appearances early
2. Use reference images when possible
3. Lock characters before generation

### Efficient Generation

1. Generate in batches by scene
2. Start with lower quality for preview
3. Only regenerate what needs fixing

### Storage Management

1. Regularly export completed projects
2. Clear cache for unused projects
3. Archive raw footage if needed

---

## Glossary

| Term | Definition |
|------|------------|
| **Fountain** | Plain text screenplay format |
| **FDX** | Final Draft XML format |
| **Shot** | Single camera setup/angle |
| **Scene** | Continuous action in one location |
| **TTS** | Text-to-Speech |
| **LLM** | Large Language Model (AI) |
| **Generation** | AI video creation process |
| **Lock** | Freeze character appearance |
| **Breakdown** | Shot-by-shot scene analysis |
