# SceneMachine API Reference
## Version 1.0 | January 2026

---

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All API requests require a Bearer token in the Authorization header:

```http
Authorization: Bearer <access_token>
```

### Obtain Token

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## Endpoints

### Health

#### Check Health
```http
GET /health
```
**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-25T12:00:00Z"
}
```

---

### Projects

#### List Projects
```http
GET /projects
```
**Response:**
```json
[
  {
    "id": "uuid",
    "name": "My Movie",
    "state": "screenplay_parsed",
    "created_at": "2026-01-25T12:00:00Z"
  }
]
```

#### Create Project
```http
POST /projects
Content-Type: application/json

{
  "name": "New Project",
  "description": "Project description"
}
```

#### Get Project
```http
GET /projects/{project_id}
```

#### Update Project
```http
PATCH /projects/{project_id}
Content-Type: application/json

{
  "name": "Updated Name"
}
```

#### Delete Project
```http
DELETE /projects/{project_id}
```

---

### Screenplay

#### Upload Screenplay
```http
POST /screenplay/projects/{project_id}/upload
Content-Type: multipart/form-data

file: [screenplay.fountain]
```

#### Get Parsed Screenplay
```http
GET /screenplay/projects/{project_id}
```

---

### Scenes

#### List Scenes
```http
GET /scenes/projects/{project_id}
```
**Response:**
```json
[
  {
    "id": "uuid",
    "scene_number": 1,
    "heading": "INT. OFFICE - DAY",
    "description": "John enters the office",
    "shot_count": 5
  }
]
```

#### Get Scene
```http
GET /scenes/{scene_id}
```

#### Update Scene
```http
PATCH /scenes/{scene_id}
Content-Type: application/json

{
  "heading": "INT. OFFICE - NIGHT"
}
```

---

### Characters

#### List Characters
```http
GET /character-lab/projects/{project_id}/characters
```
**Response:**
```json
[
  {
    "id": "uuid",
    "name": "John",
    "description": "Tall, 30s, brown hair",
    "is_locked": true,
    "voice_id": "kokoro_en_1"
  }
]
```

#### Create Character
```http
POST /character-lab/projects/{project_id}/characters
Content-Type: application/json

{
  "name": "John",
  "description": "Tall, 30s, brown hair",
  "physical_description": {
    "height": "tall",
    "age": "30s",
    "hair_color": "brown"
  }
}
```

#### Update Character
```http
PATCH /character-lab/characters/{character_id}
```

#### Lock Character
```http
POST /character-lab/characters/{character_id}/lock
```

#### Unlock Character
```http
POST /character-lab/characters/{character_id}/unlock
```

#### Upload Reference Image
```http
POST /character-lab/characters/{character_id}/reference
Content-Type: multipart/form-data

file: [reference.jpg]
```

#### Generate AI Reference
```http
POST /character-lab/characters/{character_id}/generate-reference
Content-Type: application/json

{
  "style": "photorealistic"
}
```

#### Set Voice Profile
```http
POST /character-lab/characters/{character_id}/voice
Content-Type: application/json

{
  "voice_id": "kokoro_en_1",
  "provider": "kokoro",
  "voice_name": "English Female 1"
}
```

---

### Generation

#### Get Queue Status
```http
GET /generation/queue
```
**Response:**
```json
{
  "pending": 5,
  "running": 2,
  "completed": 10,
  "failed": 0
}
```

#### List Jobs
```http
GET /generation/projects/{project_id}/jobs
```

#### Start Generation
```http
POST /generation/projects/{project_id}/start
Content-Type: application/json

{
  "quality": "standard",
  "shots": ["shot_id_1", "shot_id_2"]
}
```

#### Get Cost Estimate
```http
POST /generation/projects/{project_id}/estimate
Content-Type: application/json

{
  "quality": "standard",
  "shot_count": 10
}
```
**Response:**
```json
{
  "estimated_cost_usd": 4.50,
  "estimated_time_minutes": 15
}
```

#### Retry Shot
```http
POST /generation/shots/{shot_id}/retry
```

---

### Timeline

#### Get Timeline
```http
GET /timeline/projects/{project_id}
```
**Response:**
```json
{
  "tracks": [
    {
      "id": "video_track",
      "type": "video",
      "clips": [...]
    },
    {
      "id": "audio_track",
      "type": "audio",
      "clips": [...]
    }
  ],
  "duration_seconds": 120
}
```

#### Update Timeline
```http
PATCH /timeline/projects/{project_id}
Content-Type: application/json

{
  "clips": [
    {
      "id": "clip_id",
      "start_time": 0,
      "duration": 5
    }
  ]
}
```

---

### Assembly

#### Assemble Movie
```http
POST /assembly/projects/{project_id}/assemble
Content-Type: application/json

{
  "include_audio": true,
  "transitions": "dissolve"
}
```

---

### Export

#### Start Export
```http
POST /assembly/projects/{project_id}/export
Content-Type: application/json

{
  "format": "mp4",
  "quality": "1080p",
  "preset": "youtube"
}
```

#### Get Export Status
```http
GET /assembly/exports/{export_id}/status
```

#### Download Export
```http
GET /assembly/exports/{export_id}/download
```

---

### Snapshots

#### List Snapshots
```http
GET /snapshots/projects/{project_id}
```

#### Create Snapshot
```http
POST /snapshots/projects/{project_id}
Content-Type: application/json

{
  "label": "Before changes",
  "description": "Snapshot before editing"
}
```

#### Compare Snapshots
```http
GET /snapshots/projects/{project_id}/compare?from={from_id}&to={to_id}
```

---

### Pipeline

#### Get Pipeline Status
```http
GET /pipeline/projects/{project_id}/status
```
**Response:**
```json
{
  "status": "running",
  "current_phase": "generate",
  "progress_percent": 45,
  "phases": {
    "parse": "completed",
    "characters": "completed",
    "generate": "running",
    "review": "pending",
    "assemble": "pending"
  }
}
```

---

### Analytics

#### Get Project Analytics
```http
GET /analytics/projects/{project_id}
```
**Response:**
```json
{
  "total_shots": 50,
  "completed_shots": 45,
  "total_cost_usd": 22.50,
  "generation_time_minutes": 120,
  "average_shot_quality": 0.85
}
```

---

## Error Responses

All errors follow this format:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request",
    "details": [
      {"field": "name", "message": "Required"}
    ]
  }
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 429 | Rate Limited |
| 500 | Internal Error |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/auth/*` | 10/min |
| `/generation/*` | 100/min |
| All others | 1000/min |

---

## WebSocket

### Real-time Updates
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle: pipeline_status, generation_progress, export_complete
};
```

---

*Generated from OpenAPI spec v1.0*
