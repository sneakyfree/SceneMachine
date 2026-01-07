# SceneMachine API Documentation

SceneMachine provides two API interfaces for different use cases:

| API | Protocol | Use Case | Documentation |
|-----|----------|----------|---------------|
| **REST API** | HTTP/JSON | External integrations, web clients, testing | [REST-API.md](REST-API.md) |
| **IPC API** | Unix Socket/JSON | Desktop app frontend-backend communication | This document |

## When to Use Which API

| Scenario | Recommended API |
|----------|-----------------|
| Building external integrations | REST API |
| Web application development | REST API |
| API testing with curl | REST API |
| Desktop app (Electron) | IPC API |
| Low-latency local operations | IPC API |

---

## REST API Reference

For the complete REST API with 200+ endpoints, curl examples, and detailed request/response schemas, see:

**[REST-API.md](REST-API.md)** - Complete REST API Reference

### REST API Quick Links

- [Health & System](REST-API.md#health-api) - Server health, readiness, version info
- [Projects](REST-API.md#projects-api) - Project CRUD operations
- [Screenplays](REST-API.md#screenplays-api) - Upload and parse screenplays
- [Characters](REST-API.md#characters-api) - Character management and locking
- [Scenes](REST-API.md#scenes-api) - Scene and shot planning
- [Generation](REST-API.md#generation-api) - Video generation queue
- [Settings](REST-API.md#settings-api) - Configuration and API keys

---

## IPC API Documentation

This section describes the IPC API used for communication between the Electron frontend and Python backend.

### Overview

SceneMachine uses an IPC (Inter-Process Communication) pattern over Unix domain sockets. The frontend sends requests to named handlers, and the backend returns JSON responses.

### Request Format

```typescript
interface IPCRequest {
  method: string;     // Handler name (e.g., "projects.list")
  params?: object;    // Optional parameters
}
```

### Response Format

```typescript
interface IPCResponse {
  success: boolean;
  data?: any;         // Response data on success
  error?: string;     // Error message on failure
}
```

---

## API Endpoints

### Projects

#### `projects.list`
List all projects.

**Parameters:** None

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Project Name",
    "description": "Description",
    "state": "draft|screenplay_uploaded|analyzed|...",
    "settings": {},
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
  }
]
```

---

#### `projects.get`
Get a single project by ID.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Project UUID |

**Response:** Project object

---

#### `projects.create`
Create a new project.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Project name |
| `description` | string | No | Project description |
| `settings` | object | No | Project settings |

**Response:** Created project object

---

#### `projects.update`
Update an existing project.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Project UUID |
| `name` | string | No | New name |
| `description` | string | No | New description |
| `settings` | object | No | Updated settings |

**Response:** Updated project object

---

#### `projects.delete`
Delete a project.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Project UUID |

**Response:**
```json
{ "success": true }
```

---

### Screenplay

#### `screenplay.upload`
Upload and parse a screenplay file.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project_id` | string | Yes | Project UUID |
| `file_path` | string | Yes | Path to screenplay file |
| `format` | string | No | File format (auto-detected) |

**Response:**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "title": "Screenplay Title",
  "author": "Author Name",
  "format": "fountain|fdx",
  "is_parsed": true,
  "page_count": 120,
  "parsed_content": { ... }
}
```

---

#### `screenplay.get`
Get screenplay for a project.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project_id` | string | Yes | Project UUID |

**Response:** Screenplay object

---

### Movie Plan

#### `moviePlan.generate`
Generate a movie plan from screenplay using AI.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project_id` | string | Yes | Project UUID |
| `force_regenerate` | boolean | No | Regenerate if exists |

**Response:**
```json
{
  "characters": [...],
  "scenes": [...],
  "visual_themes": [...],
  "mood_progression": [...]
}
```

---

#### `moviePlan.get`
Get existing movie plan.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project_id` | string | Yes | Project UUID |

**Response:** Movie plan object

---

### Characters

#### `characters.list`
List all characters in a project.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project_id` | string | Yes | Project UUID |

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Character Name",
    "description": "Description",
    "appearance": "Physical appearance",
    "personality": "Personality traits",
    "role": "protagonist|antagonist|supporting",
    "lock_state": "unlocked|partial|locked",
    "scene_count": 15
  }
]
```

---

#### `characters.get`
Get a single character.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Character UUID |

**Response:** Character object

---

#### `characters.update`
Update character details.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Character UUID |
| `name` | string | No | Character name |
| `description` | string | No | Description |
| `appearance` | string | No | Physical appearance |
| `personality` | string | No | Personality traits |
| `age` | string | No | Character age |
| `gender` | string | No | Character gender |

**Response:** Updated character object

---

#### `characters.lock`
Lock a character's appearance.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Character UUID |
| `lock_state` | string | Yes | "partial" or "locked" |

**Response:** Updated character object

---

### Scenes

#### `scenes.list`
List all scenes in a project.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project_id` | string | Yes | Project UUID |

**Response:**
```json
[
  {
    "id": "uuid",
    "scene_number": "1",
    "heading": "INT. HOUSE - DAY",
    "location": "HOUSE",
    "time_of_day": "DAY",
    "description": "Scene description",
    "state": "draft|planned|approved",
    "shots": [...]
  }
]
```

---

#### `scenes.get`
Get a single scene with shots.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Scene UUID |

**Response:** Scene object with shots

---

#### `scenes.generateBreakdown`
Generate AI shot breakdown for a scene.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `scene_id` | string | Yes | Scene UUID |
| `force_regenerate` | boolean | No | Regenerate existing |

**Response:** Scene with generated shots

---

### Shots

#### `shots.update`
Update a shot.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Shot UUID |
| `shot_type` | string | No | WIDE, MEDIUM, CLOSE, etc. |
| `camera_movement` | string | No | STATIC, PAN, DOLLY, etc. |
| `description` | string | No | Shot description |
| `duration_seconds` | number | No | Shot duration |
| `generation_prompt` | string | No | Custom prompt |

**Response:** Updated shot object

---

#### `shots.reorder`
Reorder shots within a scene.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `scene_id` | string | Yes | Scene UUID |
| `shot_ids` | string[] | Yes | Ordered shot IDs |

**Response:** Updated shots array

---

### Generation

#### `generation.queueShot`
Queue a shot for video generation.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `shot_id` | string | Yes | Shot UUID |
| `provider` | string | No | Generation provider |
| `priority` | number | No | Queue priority |

**Response:**
```json
{
  "job_id": "uuid",
  "shot_id": "uuid",
  "status": "pending",
  "priority": 0
}
```

---

#### `generation.queueScene`
Queue all shots in a scene.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `scene_id` | string | Yes | Scene UUID |
| `provider` | string | No | Generation provider |

**Response:** Array of generation jobs

---

#### `generation.getStatus`
Get generation job status.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_id` | string | Yes | Job UUID |

**Response:**
```json
{
  "id": "uuid",
  "status": "pending|processing|completed|failed",
  "progress": 0.75,
  "error_message": null
}
```

---

#### `generation.cancel`
Cancel a generation job.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_id` | string | Yes | Job UUID |

**Response:**
```json
{ "success": true }
```

---

### Assembly

#### `assembly.previewScene`
Generate preview for a scene.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `scene_id` | string | Yes | Scene UUID |
| `include_audio` | boolean | No | Include TTS audio |

**Response:**
```json
{
  "preview_path": "/path/to/preview.mp4",
  "duration_seconds": 45.5
}
```

---

#### `assembly.export`
Export final video.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project_id` | string | Yes | Project UUID |
| `output_path` | string | Yes | Output file path |
| `format` | string | No | mp4_h264, mov_prores, etc. |
| `quality` | string | No | draft, standard, high, master |
| `include_scenes` | string[] | No | Specific scene IDs |

**Response:**
```json
{
  "output_path": "/path/to/output.mp4",
  "duration_seconds": 300,
  "file_size_bytes": 150000000
}
```

---

### Audio/TTS

#### `audio.getProviders`
List available TTS providers.

**Parameters:** None

**Response:**
```json
[
  {
    "id": "elevenlabs",
    "name": "ElevenLabs",
    "available": true,
    "voices_count": 50,
    "requires_api_key": true
  }
]
```

---

#### `audio.getVoices`
List voices for a provider.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `provider` | string | No | Provider ID |

**Response:**
```json
[
  {
    "id": "voice_id",
    "name": "Voice Name",
    "provider": "elevenlabs",
    "gender": "female",
    "language": "en-US"
  }
]
```

---

#### `audio.generateSpeech`
Generate speech from text.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `text` | string | Yes | Text to speak |
| `voice_id` | string | Yes | Voice ID |
| `provider` | string | No | TTS provider |

**Response:**
```json
{
  "audio_path": "/path/to/audio.mp3",
  "duration_seconds": 5.2
}
```

---

#### `audio.assignVoice`
Assign a voice to a character.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `character_id` | string | Yes | Character UUID |
| `voice_id` | string | Yes | Voice ID |
| `provider` | string | Yes | TTS provider |

**Response:** Character voice assignment

---

### Settings

#### `settings.get`
Get user settings.

**Parameters:** None

**Response:**
```json
{
  "id": "uuid",
  "llm_provider": "anthropic",
  "video_provider": "local",
  "theme_mode": "dark",
  "api_keys": {
    "anthropic": { "configured": true, "masked": "sk-ant-...xxxx" },
    "openai": { "configured": false }
  }
}
```

---

#### `settings.update`
Update settings.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `llm_provider` | string | No | Default LLM |
| `video_provider` | string | No | Default video provider |
| `theme_mode` | string | No | dark, light, system |
| ... | ... | ... | Other settings |

**Response:** Updated settings object

---

#### `settings.setApiKey`
Set an API key.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `provider` | string | Yes | Provider name |
| `api_key` | string | Yes | API key value |

**Response:**
```json
{ "success": true }
```

---

#### `settings.validateApiKey`
Test an API key.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `provider` | string | Yes | Provider name |
| `api_key` | string | No | Key to test (or use stored) |

**Response:**
```json
{
  "provider": "anthropic",
  "available": true,
  "message": "API key is valid",
  "latency_ms": 250
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `NOT_FOUND` | Resource not found |
| `VALIDATION_ERROR` | Invalid parameters |
| `UNAUTHORIZED` | API key invalid or missing |
| `RATE_LIMITED` | Too many requests |
| `PROVIDER_ERROR` | External provider error |
| `INTERNAL_ERROR` | Server error |

## Rate Limits

External API calls are subject to provider rate limits:

| Provider | Limit |
|----------|-------|
| Anthropic | 60 req/min |
| OpenAI | 60 req/min |
| ElevenLabs | Varies by plan |

## Pagination

For endpoints that return lists, pagination is supported:

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `offset` | number | 0 | Skip N items |
| `limit` | number | 50 | Max items to return |

**Response includes:**
```json
{
  "items": [...],
  "total": 100,
  "offset": 0,
  "limit": 50
}
```
