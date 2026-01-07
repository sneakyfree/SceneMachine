# SceneMachine REST API Reference

Complete reference documentation for the SceneMachine REST API. This API provides programmatic access to all SceneMachine functionality including project management, screenplay parsing, video generation, and export.

**Base URL:** `http://localhost:8000/api/v1`

**API Version:** v1

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Common Patterns](#common-patterns)
4. [Error Handling](#error-handling)
5. [Health API](#health-api)
6. [Projects API](#projects-api)
7. [Screenplays API](#screenplays-api)
8. [Movie Plans API](#movie-plans-api)
9. [Characters API](#characters-api)
10. [Scenes API](#scenes-api)
11. [Generation API](#generation-api)
12. [Assembly API](#assembly-api)
13. [Audio API](#audio-api)
14. [Settings API](#settings-api)
15. [Analytics API](#analytics-api)
16. [Sharing API](#sharing-api)
17. [Archive API](#archive-api)
18. [ActForge Performers API](#actforge-performers-api)
19. [ActForge Bookings API](#actforge-bookings-api)
20. [GPU Exchange API](#gpu-exchange-api)
21. [AI Co-pilot API](#ai-co-pilot-api)
22. [Watermarks API](#watermarks-api)
23. [Text Overlays API](#text-overlays-api)
24. [WebSocket API](#websocket-api)

---

## Overview

The SceneMachine REST API follows RESTful conventions:

- **Resources** are nouns (projects, characters, scenes)
- **HTTP Methods** indicate actions (GET, POST, PATCH, DELETE)
- **JSON** is used for request and response bodies
- **UUID** identifiers for all resources
- **ISO 8601** timestamps

### Quick Start

```bash
# Create a project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Movie"}'

# Upload screenplay
curl -X POST http://localhost:8000/api/v1/screenplays/upload/{project_id} \
  -F "file=@screenplay.fountain"

# Parse screenplay
curl -X POST http://localhost:8000/api/v1/screenplays/{screenplay_id}/parse

# List characters
curl http://localhost:8000/api/v1/characters/project/{project_id}
```

---

## Authentication

The REST API supports optional API key authentication.

### API Key Header

```bash
curl http://localhost:8000/api/v1/projects \
  -H "X-API-Key: your-api-key"
```

For local development, authentication is typically not required. In production, configure API keys via the Settings API.

See [Security Guide](../SECURITY.md) for complete authentication documentation.

---

## Common Patterns

### Pagination

List endpoints support pagination via query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Number of items to skip |
| `limit` | integer | 50-100 | Maximum items to return |

```bash
# Get projects 21-40
curl "http://localhost:8000/api/v1/projects?skip=20&limit=20"
```

### Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type` | Yes (POST/PATCH) | `application/json` or `multipart/form-data` |
| `X-API-Key` | Production | API key for authentication |
| `X-Request-ID` | No | Client-provided request ID for tracing |

### Response Headers

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Unique request identifier |
| `X-RateLimit-Limit` | Rate limit ceiling |
| `X-RateLimit-Remaining` | Remaining requests |
| `X-RateLimit-Reset` | Seconds until reset |

---

## Error Handling

### Error Response Format

All errors return JSON with consistent structure:

```json
{
  "error": "Human-readable error message",
  "detail": "Additional details (debug mode only)",
  "code": "ERROR_CODE",
  "request_id": "uuid"
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Successful GET/PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input, validation error |
| 401 | Unauthorized | Missing/invalid API key |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 413 | Payload Too Large | Request body > 100MB |
| 414 | URI Too Long | URL > 2048 characters |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Error | Server error |

### Error Codes

| Code | Description |
|------|-------------|
| `NOT_FOUND` | Resource not found |
| `VALIDATION_ERROR` | Invalid request data |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `BODY_TOO_LARGE` | Request body too large |
| `URL_TOO_LONG` | URL too long |
| `INTERNAL_ERROR` | Server error |

---

## Health API

Health check endpoints for monitoring and orchestration.

**Base Path:** `/` (root)

### GET /health

Basic health check. Always returns quickly.

```bash
curl http://localhost:8000/health
```

**Response:**

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-01-06T12:00:00.000000"
}
```

---

### GET /ready

Comprehensive readiness check including database connectivity.

```bash
curl http://localhost:8000/ready
```

**Response:**

```json
{
  "ready": true,
  "checks": {
    "database": "ok (5.2ms)",
    "storage": "ok"
  },
  "timestamp": "2026-01-06T12:00:00.000000"
}
```

---

### GET /health/detailed

Detailed health with system information.

```bash
curl http://localhost:8000/health/detailed
```

**Response:**

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-01-06T12:00:00.000000",
  "uptime_seconds": 3600.5,
  "system": {
    "platform": "Linux",
    "platform_release": "5.15.0",
    "python_version": "3.11.0",
    "processor": "x86_64",
    "pid": 12345
  },
  "checks": {
    "database": {
      "status": "ok",
      "latency_ms": 5.2,
      "version": "PostgreSQL 15.0"
    },
    "storage": {
      "status": "ok",
      "path": "/data/scenemachine",
      "free_gb": 150.5,
      "total_gb": 500.0,
      "usage_percent": 69.9
    }
  }
}
```

---

### GET /health/providers

Health status of all video generation providers.

```bash
curl http://localhost:8000/health/providers
```

**Response:**

```json
{
  "providers": [
    {
      "provider": "replicate",
      "name": "Replicate",
      "available": true,
      "message": "OK",
      "latency_ms": 150.5,
      "models_available": 8,
      "queue_length": 0
    },
    {
      "provider": "fal",
      "name": "Fal.ai",
      "available": true,
      "message": "OK",
      "latency_ms": 120.3,
      "models_available": 6,
      "queue_length": 2
    }
  ],
  "total_registered": 5,
  "total_available": 3,
  "timestamp": "2026-01-06T12:00:00.000000"
}
```

---

### GET /health/providers/{provider_type}

Health of a specific provider.

```bash
curl http://localhost:8000/health/providers/replicate
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `provider_type` | string | Provider name (replicate, fal, comfyui, local) |

---

### GET /health/circuits

Status of all circuit breakers.

```bash
curl http://localhost:8000/health/circuits
```

**Response:**

```json
{
  "circuits": [
    {
      "name": "replicate",
      "state": "closed",
      "total_calls": 1500,
      "successful_calls": 1480,
      "failed_calls": 20,
      "rejected_calls": 0,
      "consecutive_failures": 0,
      "consecutive_successes": 50,
      "failure_threshold": 5,
      "recovery_timeout": 30.0,
      "remaining_timeout": 0.0,
      "success_rate": 98.7
    }
  ],
  "total_count": 5,
  "open_count": 0,
  "half_open_count": 0,
  "timestamp": "2026-01-06T12:00:00.000000"
}
```

---

### POST /health/circuits/{circuit_name}/reset

Reset a circuit breaker to closed state.

```bash
curl -X POST http://localhost:8000/health/circuits/replicate/reset
```

**Response:**

```json
{
  "success": true,
  "message": "Circuit 'replicate' reset to closed state"
}
```

---

## Projects API

Manage movie projects.

**Base Path:** `/api/v1/projects`

### GET /api/v1/projects

List all projects with pagination.

```bash
curl "http://localhost:8000/api/v1/projects?skip=0&limit=20"
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Pagination offset |
| `limit` | integer | 100 | Max items to return |

**Response:**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My Screenplay Project",
    "description": "A thrilling adventure",
    "state": "screenplay_parsed",
    "screenplay_title": "The Great Adventure",
    "character_count": 5,
    "scene_count": 12,
    "locked_character_count": 3,
    "approved_scene_count": 8,
    "created_at": "2026-01-01T10:00:00Z",
    "updated_at": "2026-01-05T15:30:00Z"
  }
]
```

---

### POST /api/v1/projects

Create a new project.

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My New Movie",
    "description": "An epic sci-fi adventure",
    "settings": {
      "generation": {
        "quality_preset": "high",
        "preferred_provider": "replicate"
      }
    }
  }'
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Project name |
| `description` | string | No | Project description |
| `settings` | object | No | Project-specific settings |

**Response:** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "My New Movie",
  "description": "An epic sci-fi adventure",
  "state": "empty",
  "settings": {
    "generation": {
      "quality_preset": "high",
      "preferred_provider": "replicate"
    }
  },
  "can_advance": false,
  "screenplay": null,
  "characters": [],
  "scenes": [],
  "character_count": 0,
  "scene_count": 0,
  "locked_character_count": 0,
  "approved_scene_count": 0,
  "created_at": "2026-01-06T12:00:00Z",
  "updated_at": "2026-01-06T12:00:00Z"
}
```

---

### GET /api/v1/projects/{project_id}

Get project details with relationships.

```bash
curl http://localhost:8000/api/v1/projects/550e8400-e29b-41d4-a716-446655440000
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | UUID | Project identifier |

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Screenplay Project",
  "description": "A thrilling adventure",
  "state": "screenplay_parsed",
  "settings": {},
  "can_advance": true,
  "screenplay": {
    "id": "550e8400-e29b-41d4-a716-446655440010",
    "title": "The Great Adventure",
    "original_filename": "screenplay.fountain",
    "is_parsed": true,
    "movie_plan_approved": false,
    "page_count": 120
  },
  "characters": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440020",
      "name": "John",
      "screenplay_name": "JOHN",
      "is_locked": true,
      "is_protagonist": true
    }
  ],
  "scenes": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440030",
      "scene_number": "1",
      "heading": "INT. OFFICE - DAY",
      "shot_breakdown_approved": false
    }
  ],
  "character_count": 5,
  "scene_count": 12,
  "locked_character_count": 3,
  "approved_scene_count": 8,
  "created_at": "2026-01-01T10:00:00Z",
  "updated_at": "2026-01-05T15:30:00Z"
}
```

### Project States

Projects progress through these states:

```
empty → screenplay_uploaded → screenplay_parsed → plan_generated →
plan_approved → characters_in_progress → characters_locked →
scenes_planning → scenes_approved → generating → generation_complete →
assembly_in_progress → complete → exported
```

---

### PATCH /api/v1/projects/{project_id}

Update project details.

```bash
curl -X PATCH http://localhost:8000/api/v1/projects/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Project Name",
    "description": "New description"
  }'
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | New project name |
| `description` | string | No | New description |
| `settings` | object | No | Settings to merge |

---

### DELETE /api/v1/projects/{project_id}

Permanently delete a project and all associated data.

```bash
curl -X DELETE http://localhost:8000/api/v1/projects/550e8400-e29b-41d4-a716-446655440000
```

**Response:**

```json
{
  "success": true,
  "message": "Project 550e8400-e29b-41d4-a716-446655440000 deleted successfully"
}
```

---

### POST /api/v1/projects/{project_id}/duplicate

Create a copy of a project.

```bash
curl -X POST http://localhost:8000/api/v1/projects/550e8400-e29b-41d4-a716-446655440000/duplicate \
  -H "Content-Type: application/json" \
  -d '{
    "new_name": "My Project (Copy)",
    "include_generated_videos": false
  }'
```

**Request Body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `new_name` | string | null | Name for the copy (auto-generated if null) |
| `include_generated_videos` | boolean | false | Copy generated video files |

**Response:** `201 Created` - Returns the new project details

---

## Screenplays API

Upload and parse screenplay files.

**Base Path:** `/api/v1/screenplays`

### POST /api/v1/screenplays/upload/{project_id}

Upload a screenplay file.

```bash
curl -X POST http://localhost:8000/api/v1/screenplays/upload/550e8400-e29b-41d4-a716-446655440000 \
  -F "file=@screenplay.fountain"
```

**Supported Formats:**

| Extension | Format | Description |
|-----------|--------|-------------|
| `.fountain`, `.spmd` | Fountain | Industry-standard plain text format |
| `.pdf` | PDF | Scanned or digital PDFs |
| `.fdx` | Final Draft | Final Draft XML format |
| `.txt` | Plain Text | Parsed as Fountain |

**Response:** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_filename": "screenplay.fountain",
  "original_format": "fountain",
  "is_parsed": false,
  "parse_errors": null,
  "created_at": "2026-01-06T12:00:00Z",
  "updated_at": "2026-01-06T12:00:00Z"
}
```

---

### POST /api/v1/screenplays/{screenplay_id}/parse

Parse an uploaded screenplay to extract characters, scenes, and dialogue.

```bash
curl -X POST http://localhost:8000/api/v1/screenplays/550e8400-e29b-41d4-a716-446655440010/parse
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_filename": "screenplay.fountain",
  "original_format": "fountain",
  "is_parsed": true,
  "parse_errors": null,
  "created_at": "2026-01-06T12:00:00Z",
  "updated_at": "2026-01-06T12:01:00Z"
}
```

---

### GET /api/v1/screenplays/{screenplay_id}

Get screenplay details including parsed content.

```bash
curl http://localhost:8000/api/v1/screenplays/550e8400-e29b-41d4-a716-446655440010
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_filename": "screenplay.fountain",
  "original_format": "fountain",
  "is_parsed": true,
  "parse_errors": null,
  "parsed_content": {
    "title": "The Great Adventure",
    "author": "Jane Writer",
    "contact": "jane@example.com"
  },
  "character_count": 5,
  "scene_count": 12,
  "characters": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440020",
      "name": "JOHN",
      "dialogue_count": 45,
      "scene_count": 8
    }
  ],
  "scenes": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440030",
      "scene_number": "1",
      "sequence_number": 1,
      "scene_type": "interior",
      "location": "OFFICE",
      "time_of_day": "day"
    }
  ],
  "created_at": "2026-01-06T12:00:00Z",
  "updated_at": "2026-01-06T12:01:00Z"
}
```

---

### GET /api/v1/screenplays/project/{project_id}

Get screenplay for a project.

```bash
curl http://localhost:8000/api/v1/screenplays/project/550e8400-e29b-41d4-a716-446655440000
```

---

### DELETE /api/v1/screenplays/{screenplay_id}

Delete a screenplay and associated data.

```bash
curl -X DELETE http://localhost:8000/api/v1/screenplays/550e8400-e29b-41d4-a716-446655440010
```

**Response:** `204 No Content`

---

## Movie Plans API

AI-powered movie planning.

**Base Path:** `/api/v1/movie-plans`

### POST /api/v1/movie-plans/generate/{screenplay_id}

Generate an AI movie plan from parsed screenplay.

```bash
curl -X POST http://localhost:8000/api/v1/movie-plans/generate/550e8400-e29b-41d4-a716-446655440010
```

---

### GET /api/v1/movie-plans/{screenplay_id}

Get existing movie plan.

```bash
curl http://localhost:8000/api/v1/movie-plans/550e8400-e29b-41d4-a716-446655440010
```

---

### POST /api/v1/movie-plans/{screenplay_id}/approve

Approve movie plan to proceed with production.

```bash
curl -X POST http://localhost:8000/api/v1/movie-plans/550e8400-e29b-41d4-a716-446655440010/approve
```

---

## Characters API

Manage characters and their visual consistency.

**Base Path:** `/api/v1/characters`

### GET /api/v1/characters/project/{project_id}

Get all characters for a project.

```bash
curl http://localhost:8000/api/v1/characters/project/550e8400-e29b-41d4-a716-446655440000
```

**Response:**

```json
{
  "characters": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440020",
      "project_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "John Smith",
      "screenplay_name": "JOHN",
      "description": "A determined detective in his 40s",
      "age_range_min": 38,
      "age_range_max": 45,
      "age_range_display": "38-45",
      "gender": "male",
      "physical_description": {
        "hair_color": "dark brown",
        "hair_style": "short, neat",
        "eye_color": "blue",
        "skin_tone": "fair",
        "height": "6'0\"",
        "build": "athletic",
        "distinguishing_features": ["scar on left cheek"],
        "clothing_style": "professional suits"
      },
      "personality_traits": ["determined", "intelligent", "stubborn"],
      "voice_description": "Deep, gravelly voice",
      "lock_state": "locked",
      "is_locked": true,
      "locked_likeness": {
        "primary_reference_id": "asset-uuid",
        "locked_at": "2026-01-05T10:00:00Z"
      },
      "scene_count": 8,
      "dialogue_count": 45,
      "is_protagonist": true,
      "reference_assets": [
        {
          "id": "550e8400-e29b-41d4-a716-446655440050",
          "asset_type": "character_reference",
          "original_filename": "john_reference.jpg",
          "file_path": "/data/assets/john_reference.jpg",
          "is_primary": true,
          "created_at": "2026-01-05T09:00:00Z"
        }
      ],
      "created_at": "2026-01-01T10:00:00Z",
      "updated_at": "2026-01-05T10:00:00Z"
    }
  ],
  "total": 5,
  "locked_count": 3
}
```

---

### GET /api/v1/characters/{character_id}

Get character details.

```bash
curl http://localhost:8000/api/v1/characters/550e8400-e29b-41d4-a716-446655440020
```

---

### PATCH /api/v1/characters/{character_id}

Update character details.

```bash
curl -X PATCH http://localhost:8000/api/v1/characters/550e8400-e29b-41d4-a716-446655440020 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Smith",
    "description": "Updated character description",
    "age_range_min": 40,
    "age_range_max": 48,
    "gender": "male",
    "physical_description": {
      "hair_color": "salt and pepper",
      "hair_style": "short, neat",
      "eye_color": "blue",
      "skin_tone": "fair",
      "height": "6'\''0\"",
      "build": "athletic"
    },
    "personality_traits": ["determined", "intelligent", "compassionate"],
    "voice_description": "Deep, authoritative voice",
    "is_protagonist": true
  }'
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Display name |
| `description` | string | No | Character description |
| `age_range_min` | integer | No | Minimum age |
| `age_range_max` | integer | No | Maximum age |
| `gender` | string | No | male, female, non_binary, unspecified |
| `physical_description` | object | No | Physical attributes |
| `personality_traits` | array | No | List of traits |
| `voice_description` | string | No | Voice description for TTS |
| `is_protagonist` | boolean | No | Main character flag |

---

### POST /api/v1/characters/{character_id}/generate-description

AI-generate character description from screenplay context.

```bash
curl -X POST http://localhost:8000/api/v1/characters/550e8400-e29b-41d4-a716-446655440020/generate-description
```

**Response:**

```json
{
  "description": "A seasoned detective haunted by past cases...",
  "estimated_age": 42,
  "gender": "male",
  "personality_traits": ["determined", "haunted", "analytical"],
  "physical_description": {
    "hair_color": "dark brown with gray",
    "eye_color": "piercing blue",
    "build": "weathered but fit"
  }
}
```

---

### POST /api/v1/characters/{character_id}/reference

Upload a reference image.

```bash
curl -X POST http://localhost:8000/api/v1/characters/550e8400-e29b-41d4-a716-446655440020/reference \
  -F "file=@reference_image.jpg" \
  -F "is_primary=true"
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `is_primary` | boolean | false | Set as primary reference |

**Response:** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440050",
  "asset_type": "character_reference",
  "original_filename": "reference_image.jpg",
  "file_path": "/data/assets/reference_image.jpg",
  "is_primary": true,
  "created_at": "2026-01-06T12:00:00Z"
}
```

---

### DELETE /api/v1/characters/{character_id}/reference/{asset_id}

Delete a reference image.

```bash
curl -X DELETE http://localhost:8000/api/v1/characters/550e8400-e29b-41d4-a716-446655440020/reference/550e8400-e29b-41d4-a716-446655440050
```

**Response:** `204 No Content`

---

### POST /api/v1/characters/{character_id}/lock

Lock character likeness for consistent generation.

```bash
curl -X POST http://localhost:8000/api/v1/characters/550e8400-e29b-41d4-a716-446655440020/lock \
  -H "Content-Type: application/json" \
  -d '{
    "primary_reference_id": "550e8400-e29b-41d4-a716-446655440050"
  }'
```

### Character Lock States

```
undefined → draft → reference_uploaded → generating → review → locked
```

---

### POST /api/v1/characters/{character_id}/unlock

Unlock character for further editing.

```bash
curl -X POST http://localhost:8000/api/v1/characters/550e8400-e29b-41d4-a716-446655440020/unlock
```

---

### GET /api/v1/characters/{character_id}/prompt

Get AI generation prompts for character consistency.

```bash
curl "http://localhost:8000/api/v1/characters/550e8400-e29b-41d4-a716-446655440020/prompt?scene_context=office%20scene"
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scene_context` | string | No | Scene context for prompt customization |

**Response:**

```json
{
  "positive_prompt": "40-year-old male detective, dark brown hair, blue eyes, wearing a suit...",
  "negative_prompt": "cartoon, anime, deformed, blurry...",
  "style_prompt": "cinematic lighting, professional photography, 4K...",
  "consistency_tokens": ["JOHN_V1", "DETECTIVE_SUIT"]
}
```

---

## Scenes API

Manage scenes and shot breakdowns.

**Base Path:** `/api/v1/scenes`

### GET /api/v1/scenes/project/{project_id}

Get all scenes for a project.

```bash
curl http://localhost:8000/api/v1/scenes/project/550e8400-e29b-41d4-a716-446655440000
```

---

### GET /api/v1/scenes/{scene_id}

Get scene details.

```bash
curl http://localhost:8000/api/v1/scenes/550e8400-e29b-41d4-a716-446655440030
```

---

### POST /api/v1/scenes/{scene_id}/analyze

AI-analyze scene content.

```bash
curl -X POST http://localhost:8000/api/v1/scenes/550e8400-e29b-41d4-a716-446655440030/analyze
```

---

### POST /api/v1/scenes/{scene_id}/breakdown

Generate shot breakdown using AI.

```bash
curl -X POST http://localhost:8000/api/v1/scenes/550e8400-e29b-41d4-a716-446655440030/breakdown
```

---

### POST /api/v1/scenes/{scene_id}/approve

Approve shot breakdown.

```bash
curl -X POST http://localhost:8000/api/v1/scenes/550e8400-e29b-41d4-a716-446655440030/approve
```

---

### GET /api/v1/scenes/{scene_id}/shots

Get all shots for a scene.

```bash
curl http://localhost:8000/api/v1/scenes/550e8400-e29b-41d4-a716-446655440030/shots
```

---

### POST /api/v1/scenes/{scene_id}/shots

Add a shot to a scene.

```bash
curl -X POST http://localhost:8000/api/v1/scenes/550e8400-e29b-41d4-a716-446655440030/shots \
  -H "Content-Type: application/json" \
  -d '{
    "shot_type": "medium",
    "camera_movement": "static",
    "description": "John enters the room cautiously",
    "duration_seconds": 3.0
  }'
```

---

### GET /api/v1/scenes/shots/{shot_id}

Get shot details.

```bash
curl http://localhost:8000/api/v1/scenes/shots/550e8400-e29b-41d4-a716-446655440040
```

---

### PATCH /api/v1/scenes/shots/{shot_id}

Update shot details.

```bash
curl -X PATCH http://localhost:8000/api/v1/scenes/shots/550e8400-e29b-41d4-a716-446655440040 \
  -H "Content-Type: application/json" \
  -d '{
    "shot_type": "close_up",
    "description": "Updated shot description"
  }'
```

---

### DELETE /api/v1/scenes/shots/{shot_id}

Delete a shot.

```bash
curl -X DELETE http://localhost:8000/api/v1/scenes/shots/550e8400-e29b-41d4-a716-446655440040
```

---

### GET /api/v1/scenes/reference/shot-types

Get available shot types.

```bash
curl http://localhost:8000/api/v1/scenes/reference/shot-types
```

**Response:**

```json
[
  {"type": "establishing", "description": "Wide shot establishing location"},
  {"type": "wide", "description": "Full environment visible"},
  {"type": "full", "description": "Full body visible"},
  {"type": "medium", "description": "Waist up"},
  {"type": "medium_close_up", "description": "Chest up"},
  {"type": "close_up", "description": "Face/object detail"},
  {"type": "extreme_close_up", "description": "Eyes, small details"},
  {"type": "over_the_shoulder", "description": "OTS conversation shot"},
  {"type": "pov", "description": "Character point of view"},
  {"type": "two_shot", "description": "Two characters in frame"},
  {"type": "group", "description": "Multiple characters"},
  {"type": "insert", "description": "Detail insert"},
  {"type": "cutaway", "description": "Reaction or related shot"},
  {"type": "aerial", "description": "Bird's eye view"},
  {"type": "low_angle", "description": "Looking up"},
  {"type": "high_angle", "description": "Looking down"},
  {"type": "dutch_angle", "description": "Tilted frame"}
]
```

---

### GET /api/v1/scenes/reference/camera-movements

Get available camera movements.

```bash
curl http://localhost:8000/api/v1/scenes/reference/camera-movements
```

---

## Generation API

Video generation queue and job management.

**Base Path:** `/api/v1/generation`

### GET /api/v1/generation/providers

List available generation providers.

```bash
curl http://localhost:8000/api/v1/generation/providers
```

**Response:**

```json
[
  {"provider": "local", "name": "Local (Development)", "available": true},
  {"provider": "replicate", "name": "Replicate", "available": true},
  {"provider": "fal", "name": "Fal.ai", "available": true},
  {"provider": "comfyui", "name": "ComfyUI", "available": false},
  {"provider": "runpod", "name": "RunPod", "available": false}
]
```

---

### GET /api/v1/generation/queue

Get queue status.

```bash
curl "http://localhost:8000/api/v1/generation/queue?project_id=550e8400-e29b-41d4-a716-446655440000"
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | UUID | No | Filter by project |

**Response:**

```json
{
  "total_jobs": 50,
  "pending": 20,
  "running": 2,
  "completed": 25,
  "failed": 3,
  "status_counts": {
    "pending": 20,
    "queued": 5,
    "running": 2,
    "completed": 25,
    "failed": 3
  }
}
```

---

### GET /api/v1/generation/queue/pending

Get pending jobs.

```bash
curl "http://localhost:8000/api/v1/generation/queue/pending?limit=10"
```

---

### POST /api/v1/generation/shots/{shot_id}/queue

Queue a shot for generation.

```bash
curl -X POST http://localhost:8000/api/v1/generation/shots/550e8400-e29b-41d4-a716-446655440040/queue \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "replicate",
    "priority": 0
  }'
```

**Request Body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | string | local | Generation provider |
| `priority` | integer | 0 | Queue priority (-100 to 100) |

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440060",
  "shot_id": "550e8400-e29b-41d4-a716-446655440040",
  "job_number": 1,
  "status": "pending",
  "provider": "replicate",
  "model_id": "minimax",
  "progress_percent": null,
  "progress_message": null,
  "error_message": null,
  "output_path": null,
  "thumbnail_path": null,
  "cost_usd": null,
  "queued_at": "2026-01-06T12:00:00Z",
  "started_at": null,
  "completed_at": null
}
```

---

### POST /api/v1/generation/scenes/{scene_id}/queue

Queue all shots in a scene.

```bash
curl -X POST http://localhost:8000/api/v1/generation/scenes/550e8400-e29b-41d4-a716-446655440030/queue \
  -H "Content-Type: application/json" \
  -d '{"provider": "replicate"}'
```

---

### POST /api/v1/generation/projects/{project_id}/queue

Queue all shots in a project.

```bash
curl -X POST http://localhost:8000/api/v1/generation/projects/550e8400-e29b-41d4-a716-446655440000/queue \
  -H "Content-Type: application/json" \
  -d '{"provider": "replicate"}'
```

**Response:**

```json
{
  "queued_count": 45,
  "jobs": [...]
}
```

---

### GET /api/v1/generation/jobs/{job_id}

Get job details.

```bash
curl http://localhost:8000/api/v1/generation/jobs/550e8400-e29b-41d4-a716-446655440060
```

---

### POST /api/v1/generation/jobs/{job_id}/process

Manually trigger job processing.

```bash
curl -X POST http://localhost:8000/api/v1/generation/jobs/550e8400-e29b-41d4-a716-446655440060/process
```

---

### POST /api/v1/generation/jobs/{job_id}/cancel

Cancel a pending or running job.

```bash
curl -X POST http://localhost:8000/api/v1/generation/jobs/550e8400-e29b-41d4-a716-446655440060/cancel
```

---

### POST /api/v1/generation/jobs/{job_id}/retry

Retry a failed job.

```bash
curl -X POST http://localhost:8000/api/v1/generation/jobs/550e8400-e29b-41d4-a716-446655440060/retry
```

---

### GET /api/v1/generation/shots/{shot_id}/jobs

Get all jobs for a shot.

```bash
curl http://localhost:8000/api/v1/generation/shots/550e8400-e29b-41d4-a716-446655440040/jobs
```

---

### POST /api/v1/generation/shots/{shot_id}/approve

Approve a generated shot.

```bash
curl -X POST http://localhost:8000/api/v1/generation/shots/550e8400-e29b-41d4-a716-446655440040/approve
```

---

### POST /api/v1/generation/shots/{shot_id}/reject

Reject a shot for regeneration.

```bash
curl -X POST http://localhost:8000/api/v1/generation/shots/550e8400-e29b-41d4-a716-446655440040/reject \
  -H "Content-Type: application/json" \
  -d '{"notes": "Character likeness not matching"}'
```

---

### GET /api/v1/generation/providers/health

Get detailed provider health status.

```bash
curl http://localhost:8000/api/v1/generation/providers/health
```

---

### GET /api/v1/generation/providers/{provider_id}/models

Get available models for a provider.

```bash
curl http://localhost:8000/api/v1/generation/providers/replicate/models
```

**Response:**

```json
[
  {
    "id": "minimax",
    "name": "Minimax Video-01",
    "cost_per_second": 0.03,
    "supports_text_to_video": true,
    "supports_image_to_video": true,
    "max_duration": 6.0
  },
  {
    "id": "luma",
    "name": "Luma Dream Machine",
    "cost_per_second": 0.05,
    "supports_text_to_video": true,
    "supports_image_to_video": true,
    "max_duration": 5.0
  }
]
```

---

### POST /api/v1/generation/estimate-cost

Estimate generation cost.

```bash
curl -X POST http://localhost:8000/api/v1/generation/estimate-cost \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "replicate",
    "model_id": "minimax",
    "duration_seconds": 3.0,
    "shot_count": 50
  }'
```

**Response:**

```json
{
  "provider": "replicate",
  "model_id": "minimax",
  "model_name": "Minimax Video-01",
  "duration_seconds": 3.0,
  "shot_count": 50,
  "cost_per_shot": 0.09,
  "total_cost": 4.50,
  "currency": "USD"
}
```

---

### GET /api/v1/generation/worker/status

Get queue worker status.

```bash
curl http://localhost:8000/api/v1/generation/worker/status
```

**Response:**

```json
{
  "started_at": "2026-01-06T10:00:00Z",
  "uptime_seconds": 7200.5,
  "jobs_processed": 150,
  "jobs_succeeded": 145,
  "jobs_failed": 5,
  "success_rate": 96.7,
  "current_job_id": "550e8400-e29b-41d4-a716-446655440060",
  "last_job_completed_at": "2026-01-06T11:55:00Z",
  "is_running": true,
  "is_paused": false
}
```

---

### POST /api/v1/generation/worker/pause

Pause the queue worker.

```bash
curl -X POST http://localhost:8000/api/v1/generation/worker/pause
```

---

### POST /api/v1/generation/worker/resume

Resume the queue worker.

```bash
curl -X POST http://localhost:8000/api/v1/generation/worker/resume
```

---

## Assembly API

Video assembly and export.

**Base Path:** `/api/v1/assembly`

### GET /api/v1/assembly/status/{project_id}

Get assembly status for a project.

```bash
curl http://localhost:8000/api/v1/assembly/status/550e8400-e29b-41d4-a716-446655440000
```

---

### GET /api/v1/assembly/timeline/{project_id}

Get project timeline.

```bash
curl http://localhost:8000/api/v1/assembly/timeline/550e8400-e29b-41d4-a716-446655440000
```

---

### POST /api/v1/assembly/assemble/scene/{scene_id}

Assemble a single scene.

```bash
curl -X POST http://localhost:8000/api/v1/assembly/assemble/scene/550e8400-e29b-41d4-a716-446655440030
```

---

### POST /api/v1/assembly/assemble/movie/{project_id}

Assemble full movie.

```bash
curl -X POST http://localhost:8000/api/v1/assembly/assemble/movie/550e8400-e29b-41d4-a716-446655440000
```

---

### POST /api/v1/assembly/export/{project_id}

Export movie with settings.

```bash
curl -X POST http://localhost:8000/api/v1/assembly/export/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "format": "mp4_h264",
    "quality": "high",
    "resolution": "1920x1080",
    "include_audio": true,
    "include_subtitles": false
  }'
```

---

### GET /api/v1/assembly/export/progress/{export_id}

Get export progress.

```bash
curl http://localhost:8000/api/v1/assembly/export/progress/550e8400-e29b-41d4-a716-446655440070
```

---

### GET /api/v1/assembly/export/history/{project_id}

Get export history.

```bash
curl http://localhost:8000/api/v1/assembly/export/history/550e8400-e29b-41d4-a716-446655440000
```

---

### DELETE /api/v1/assembly/export/{export_id}

Cancel an export.

```bash
curl -X DELETE http://localhost:8000/api/v1/assembly/export/550e8400-e29b-41d4-a716-446655440070
```

---

### GET /api/v1/assembly/formats

Get available export formats.

```bash
curl http://localhost:8000/api/v1/assembly/formats
```

---

### GET /api/v1/assembly/quality-presets

Get quality presets.

```bash
curl http://localhost:8000/api/v1/assembly/quality-presets
```

---

## Audio API

Sound effects and music management.

**Base Path:** `/api/v1/audio`

### GET /api/v1/audio/sfx

List sound effects.

```bash
curl "http://localhost:8000/api/v1/audio/sfx?category=ambient&limit=20"
```

---

### GET /api/v1/audio/sfx/categories

Get sound effect categories.

```bash
curl http://localhost:8000/api/v1/audio/sfx/categories
```

---

### GET /api/v1/audio/sfx/{effect_id}

Get specific sound effect.

```bash
curl http://localhost:8000/api/v1/audio/sfx/550e8400-e29b-41d4-a716-446655440080
```

---

### POST /api/v1/audio/sfx/{effect_id}/favorite

Toggle favorite status.

```bash
curl -X POST http://localhost:8000/api/v1/audio/sfx/550e8400-e29b-41d4-a716-446655440080/favorite
```

---

### POST /api/v1/audio/sfx/upload

Upload custom sound effect.

```bash
curl -X POST http://localhost:8000/api/v1/audio/sfx/upload \
  -F "file=@sound_effect.wav"
```

---

### DELETE /api/v1/audio/sfx/{effect_id}

Delete custom sound effect.

```bash
curl -X DELETE http://localhost:8000/api/v1/audio/sfx/550e8400-e29b-41d4-a716-446655440080
```

---

### GET /api/v1/audio/music

List music tracks.

```bash
curl "http://localhost:8000/api/v1/audio/music?genre=orchestral&mood=tense"
```

---

### GET /api/v1/audio/music/genres

Get available genres.

```bash
curl http://localhost:8000/api/v1/audio/music/genres
```

---

### GET /api/v1/audio/music/moods

Get available moods.

```bash
curl http://localhost:8000/api/v1/audio/music/moods
```

---

## Settings API

Application configuration.

**Base Path:** `/api/v1/settings`

### GET /api/v1/settings

Get current settings.

```bash
curl http://localhost:8000/api/v1/settings
```

---

### PATCH /api/v1/settings

Update settings.

```bash
curl -X PATCH http://localhost:8000/api/v1/settings \
  -H "Content-Type: application/json" \
  -d '{
    "themeMode": "dark",
    "maxConcurrentGenerations": 4,
    "autoSaveEnabled": true
  }'
```

---

### POST /api/v1/settings/api-keys

Set an API key.

```bash
curl -X POST http://localhost:8000/api/v1/settings/api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "api_key": "sk-ant-..."
  }'
```

---

### DELETE /api/v1/settings/api-keys/{provider}

Remove an API key.

```bash
curl -X DELETE http://localhost:8000/api/v1/settings/api-keys/anthropic
```

---

### POST /api/v1/settings/api-keys/{provider}/validate

Validate an API key.

```bash
curl -X POST http://localhost:8000/api/v1/settings/api-keys/anthropic/validate
```

---

### GET /api/v1/settings/providers/status

Check all provider configurations.

```bash
curl http://localhost:8000/api/v1/settings/providers/status
```

---

### GET /api/v1/settings/storage

Get storage statistics.

```bash
curl http://localhost:8000/api/v1/settings/storage
```

---

### POST /api/v1/settings/storage/clear-cache

Clear cache.

```bash
curl -X POST http://localhost:8000/api/v1/settings/storage/clear-cache
```

---

### GET /api/v1/settings/export

Export settings.

```bash
curl http://localhost:8000/api/v1/settings/export
```

---

### POST /api/v1/settings/import

Import settings.

```bash
curl -X POST http://localhost:8000/api/v1/settings/import \
  -H "Content-Type: application/json" \
  -d '{"settings": {...}}'
```

---

## Analytics API

Usage statistics and cost tracking.

**Base Path:** `/api/v1/analytics`

### GET /api/v1/analytics/generation-stats

Get generation job statistics.

```bash
curl "http://localhost:8000/api/v1/analytics/generation-stats?time_range=7d"
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `time_range` | string | 7d | 24h, 7d, 30d, all |

---

### GET /api/v1/analytics/cost-stats

Get cost statistics.

```bash
curl "http://localhost:8000/api/v1/analytics/cost-stats?time_range=30d"
```

---

### GET /api/v1/analytics/project-stats

Get project statistics.

```bash
curl http://localhost:8000/api/v1/analytics/project-stats
```

---

### GET /api/v1/analytics/performance-stats

Get performance metrics.

```bash
curl http://localhost:8000/api/v1/analytics/performance-stats
```

---

### GET /api/v1/analytics/provider-usage

Get provider usage statistics.

```bash
curl http://localhost:8000/api/v1/analytics/provider-usage
```

---

### GET /api/v1/analytics/daily-stats

Get daily generation statistics.

```bash
curl "http://localhost:8000/api/v1/analytics/daily-stats?days=7"
```

---

### GET /api/v1/analytics/dashboard

Get combined dashboard statistics.

```bash
curl http://localhost:8000/api/v1/analytics/dashboard
```

---

### GET /api/v1/analytics/projects/{project_id}/costs

Get project cost breakdown.

```bash
curl http://localhost:8000/api/v1/analytics/projects/550e8400-e29b-41d4-a716-446655440000/costs
```

---

## Sharing API

Project collaboration and sharing.

**Base Path:** `/api/v1/sharing`

### POST /api/v1/sharing

Create a project share.

```bash
curl -X POST http://localhost:8000/api/v1/sharing \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "recipient_email": "collaborator@example.com",
    "permission": "edit",
    "message": "Please review my screenplay project"
  }'
```

---

### GET /api/v1/sharing/project/{project_id}

Get shares for a project.

```bash
curl http://localhost:8000/api/v1/sharing/project/550e8400-e29b-41d4-a716-446655440000
```

---

### GET /api/v1/sharing/code/{share_code}

Get share by code.

```bash
curl http://localhost:8000/api/v1/sharing/code/abc123xyz
```

---

### POST /api/v1/sharing/code/{share_code}/accept

Accept share invitation.

```bash
curl -X POST http://localhost:8000/api/v1/sharing/code/abc123xyz/accept
```

---

### PATCH /api/v1/sharing/{share_id}

Update share permission.

```bash
curl -X PATCH http://localhost:8000/api/v1/sharing/550e8400-e29b-41d4-a716-446655440090 \
  -H "Content-Type: application/json" \
  -d '{"permission": "view"}'
```

---

### DELETE /api/v1/sharing/{share_id}

Revoke share.

```bash
curl -X DELETE http://localhost:8000/api/v1/sharing/550e8400-e29b-41d4-a716-446655440090
```

---

### POST /api/v1/sharing/projects/{project_id}/comments

Add comment to project.

```bash
curl -X POST http://localhost:8000/api/v1/sharing/projects/550e8400-e29b-41d4-a716-446655440000/comments \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Great shot composition here!",
    "shot_id": "550e8400-e29b-41d4-a716-446655440040",
    "timecode_seconds": 15.5
  }'
```

---

### GET /api/v1/sharing/projects/{project_id}/comments

Get project comments.

```bash
curl http://localhost:8000/api/v1/sharing/projects/550e8400-e29b-41d4-a716-446655440000/comments
```

---

## Archive API

Project import/export.

**Base Path:** `/api/v1/archive`

### POST /api/v1/archive/export

Export project to .smproject file.

```bash
curl -X POST http://localhost:8000/api/v1/archive/export \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "include_generated_videos": true
  }'
```

---

### POST /api/v1/archive/export/{project_id}/download

Export and download immediately.

```bash
curl -X POST http://localhost:8000/api/v1/archive/export/550e8400-e29b-41d4-a716-446655440000/download \
  -o project.smproject
```

---

### GET /api/v1/archive/download/{filename}

Download existing export.

```bash
curl http://localhost:8000/api/v1/archive/download/project_2026-01-06.smproject \
  -o project.smproject
```

---

### GET /api/v1/archive/list

List all exports.

```bash
curl http://localhost:8000/api/v1/archive/list
```

---

### DELETE /api/v1/archive/export

Delete export file.

```bash
curl -X DELETE http://localhost:8000/api/v1/archive/export \
  -H "Content-Type: application/json" \
  -d '{"filename": "project_2026-01-06.smproject"}'
```

---

### POST /api/v1/archive/import

Import .smproject file.

```bash
curl -X POST http://localhost:8000/api/v1/archive/import \
  -F "file=@project.smproject"
```

---

### GET /api/v1/archive/info

Get archive info without importing.

```bash
curl -X POST http://localhost:8000/api/v1/archive/info \
  -F "file=@project.smproject"
```

---

## ActForge Performers API

Talent marketplace - performer management.

**Base Path:** `/api/v1/performers`

### GET /api/v1/performers

List performers with filtering.

```bash
curl "http://localhost:8000/api/v1/performers?availability=available&min_aci=70"
```

---

### GET /api/v1/performers/featured

Get featured/top performers.

```bash
curl http://localhost:8000/api/v1/performers/featured
```

---

### GET /api/v1/performers/leaderboard

Get ACI leaderboard.

```bash
curl http://localhost:8000/api/v1/performers/leaderboard
```

---

### GET /api/v1/performers/{performer_id}

Get performer profile.

```bash
curl http://localhost:8000/api/v1/performers/550e8400-e29b-41d4-a716-446655440100
```

---

### POST /api/v1/performers

Create performer profile.

```bash
curl -X POST http://localhost:8000/api/v1/performers \
  -H "Content-Type: application/json" \
  -d '{
    "stage_name": "Alex Motion",
    "bio": "Professional motion capture artist...",
    "specialties": ["action", "drama", "comedy"]
  }'
```

---

### PATCH /api/v1/performers/{performer_id}

Update performer profile.

```bash
curl -X PATCH http://localhost:8000/api/v1/performers/550e8400-e29b-41d4-a716-446655440100 \
  -H "Content-Type: application/json" \
  -d '{"bio": "Updated bio..."}'
```

---

### POST /api/v1/performers/{performer_id}/availability

Set availability status.

```bash
curl -X POST http://localhost:8000/api/v1/performers/550e8400-e29b-41d4-a716-446655440100/availability \
  -H "Content-Type: application/json" \
  -d '{"status": "available"}'
```

---

### GET /api/v1/performers/{performer_id}/takes

Get available performance takes.

```bash
curl http://localhost:8000/api/v1/performers/550e8400-e29b-41d4-a716-446655440100/takes
```

---

### GET /api/v1/performers/{performer_id}/stats

Get ACI breakdown and statistics.

```bash
curl http://localhost:8000/api/v1/performers/550e8400-e29b-41d4-a716-446655440100/stats
```

---

## ActForge Bookings API

Talent booking management.

**Base Path:** `/api/v1/bookings`

### POST /api/v1/bookings/blink

Create Blink booking (10-sec auto-match).

```bash
curl -X POST http://localhost:8000/api/v1/bookings/blink \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "shot_id": "550e8400-e29b-41d4-a716-446655440040",
    "emotion_requirements": ["happy", "surprised"],
    "max_price_usd": 10.00
  }'
```

---

### POST /api/v1/bookings/deep

Create Deep booking (method acting, 120s).

```bash
curl -X POST http://localhost:8000/api/v1/bookings/deep \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "performer_id": "550e8400-e29b-41d4-a716-446655440100",
    "scene_description": "Intense confrontation scene...",
    "special_instructions": "Focus on subtle facial expressions"
  }'
```

---

### POST /api/v1/bookings/epic

Create Epic booking (5-20 min long-form).

```bash
curl -X POST http://localhost:8000/api/v1/bookings/epic \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "performer_id": "550e8400-e29b-41d4-a716-446655440100",
    "duration_requested_seconds": 600,
    "character_context": "Lead detective in noir film..."
  }'
```

---

### GET /api/v1/bookings

List bookings.

```bash
curl "http://localhost:8000/api/v1/bookings?status=in_progress"
```

---

### GET /api/v1/bookings/{booking_id}

Get booking details.

```bash
curl http://localhost:8000/api/v1/bookings/550e8400-e29b-41d4-a716-446655440110
```

---

### POST /api/v1/bookings/{booking_id}/accept

Performer accepts booking.

```bash
curl -X POST http://localhost:8000/api/v1/bookings/550e8400-e29b-41d4-a716-446655440110/accept
```

---

### POST /api/v1/bookings/{booking_id}/deliver

Deliver performance take.

```bash
curl -X POST http://localhost:8000/api/v1/bookings/550e8400-e29b-41d4-a716-446655440110/deliver \
  -H "Content-Type: application/json" \
  -d '{"take_id": "550e8400-e29b-41d4-a716-446655440120"}'
```

---

### POST /api/v1/bookings/{booking_id}/approve

Director approves delivery.

```bash
curl -X POST http://localhost:8000/api/v1/bookings/550e8400-e29b-41d4-a716-446655440110/approve
```

---

### POST /api/v1/bookings/{booking_id}/dispute

Dispute delivery.

```bash
curl -X POST http://localhost:8000/api/v1/bookings/550e8400-e29b-41d4-a716-446655440110/dispute \
  -H "Content-Type: application/json" \
  -d '{"reason": "Performance does not match requirements"}'
```

---

### POST /api/v1/bookings/{booking_id}/cancel

Cancel booking.

```bash
curl -X POST http://localhost:8000/api/v1/bookings/550e8400-e29b-41d4-a716-446655440110/cancel
```

---

### POST /api/v1/bookings/{booking_id}/rate

Rate performer.

```bash
curl -X POST http://localhost:8000/api/v1/bookings/550e8400-e29b-41d4-a716-446655440110/rate \
  -H "Content-Type: application/json" \
  -d '{
    "overall_score": 4.5,
    "motion_quality_score": 5.0,
    "emotion_accuracy_score": 4.0,
    "professionalism_score": 5.0,
    "timeliness_score": 4.5,
    "would_rehire": true,
    "review_text": "Excellent performance, highly recommended!"
  }'
```

---

## GPU Exchange API

Multi-provider GPU routing and pricing.

**Base Path:** `/api/v1/gpu-exchange`

### GET /api/v1/gpu-exchange/providers

List GPU providers.

```bash
curl http://localhost:8000/api/v1/gpu-exchange/providers
```

---

### GET /api/v1/gpu-exchange/providers/{provider_id}

Get provider information.

```bash
curl http://localhost:8000/api/v1/gpu-exchange/providers/replicate
```

---

### GET /api/v1/gpu-exchange/providers/{provider_id}/health

Get provider health.

```bash
curl http://localhost:8000/api/v1/gpu-exchange/providers/replicate/health
```

---

### GET /api/v1/gpu-exchange/pricing/{provider_id}/{gpu_type}

Get pricing for provider/GPU combination.

```bash
curl http://localhost:8000/api/v1/gpu-exchange/pricing/replicate/a100
```

---

### GET /api/v1/gpu-exchange/pricing/compare/{gpu_type}

Compare pricing across providers.

```bash
curl http://localhost:8000/api/v1/gpu-exchange/pricing/compare/a100
```

---

### POST /api/v1/gpu-exchange/routing/select

Select optimal provider based on criteria.

```bash
curl -X POST http://localhost:8000/api/v1/gpu-exchange/routing/select \
  -H "Content-Type: application/json" \
  -d '{
    "gpu_type": "a100",
    "priority": "cost",
    "max_price_per_hour": 2.00
  }'
```

---

### POST /api/v1/gpu-exchange/budget/limit

Set budget limit.

```bash
curl -X POST http://localhost:8000/api/v1/gpu-exchange/budget/limit \
  -H "Content-Type: application/json" \
  -d '{
    "daily_limit_usd": 50.00,
    "monthly_limit_usd": 500.00
  }'
```

---

### POST /api/v1/gpu-exchange/budget/check

Check budget availability.

```bash
curl -X POST http://localhost:8000/api/v1/gpu-exchange/budget/check \
  -H "Content-Type: application/json" \
  -d '{"estimated_cost_usd": 25.00}'
```

---

## AI Co-pilot API

AI assistant "Steven" for creative guidance.

**Base Path:** `/api/v1/copilot`

### POST /api/v1/copilot/analyze-scene

Analyze scene with AI suggestions.

```bash
curl -X POST http://localhost:8000/api/v1/copilot/analyze-scene \
  -H "Content-Type: application/json" \
  -d '{
    "scene_id": "550e8400-e29b-41d4-a716-446655440030",
    "focus_areas": ["cinematography", "pacing"]
  }'
```

---

### POST /api/v1/copilot/recommend-performers

Get AI performer recommendations.

```bash
curl -X POST http://localhost:8000/api/v1/copilot/recommend-performers \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "550e8400-e29b-41d4-a716-446655440020",
    "scene_context": "Emotional confrontation scene"
  }'
```

---

### POST /api/v1/copilot/creative-guidance

Get creative guidance.

```bash
curl -X POST http://localhost:8000/api/v1/copilot/creative-guidance \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "question": "How can I improve the pacing of Act 2?"
  }'
```

---

### POST /api/v1/copilot/chat

Chat with Steven AI.

```bash
curl -X POST http://localhost:8000/api/v1/copilot/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What shot types would work best for this action sequence?",
    "context": {
      "project_id": "550e8400-e29b-41d4-a716-446655440000",
      "scene_id": "550e8400-e29b-41d4-a716-446655440030"
    }
  }'
```

---

### POST /api/v1/copilot/voice-command

Process voice command.

```bash
curl -X POST http://localhost:8000/api/v1/copilot/voice-command \
  -F "audio=@voice_command.wav"
```

---

### GET /api/v1/copilot/status

Get Steven status.

```bash
curl http://localhost:8000/api/v1/copilot/status
```

---

## Watermarks API

Watermark management.

**Base Path:** `/api/v1/watermarks`

### GET /api/v1/watermarks

List watermarks.

```bash
curl http://localhost:8000/api/v1/watermarks
```

---

### POST /api/v1/watermarks/upload

Upload watermark image.

```bash
curl -X POST http://localhost:8000/api/v1/watermarks/upload \
  -F "file=@watermark.png"
```

**Supported formats:** PNG, JPG, JPEG, WebP, GIF (max 5MB)

---

### GET /api/v1/watermarks/{watermark_id}

Get watermark info.

```bash
curl http://localhost:8000/api/v1/watermarks/550e8400-e29b-41d4-a716-446655440130
```

---

### DELETE /api/v1/watermarks/{watermark_id}

Delete user watermark.

```bash
curl -X DELETE http://localhost:8000/api/v1/watermarks/550e8400-e29b-41d4-a716-446655440130
```

---

## Text Overlays API

Text overlays for titles, captions, lower thirds.

**Base Path:** `/api/v1/text-overlays`

### GET /api/v1/text-overlays/presets

Get available presets.

```bash
curl http://localhost:8000/api/v1/text-overlays/presets
```

---

### GET /api/v1/text-overlays/shot/{shot_id}

Get shot overlays.

```bash
curl http://localhost:8000/api/v1/text-overlays/shot/550e8400-e29b-41d4-a716-446655440040
```

---

### GET /api/v1/text-overlays/scene/{scene_id}

Get scene overlays.

```bash
curl http://localhost:8000/api/v1/text-overlays/scene/550e8400-e29b-41d4-a716-446655440030
```

---

### POST /api/v1/text-overlays

Create overlay.

```bash
curl -X POST http://localhost:8000/api/v1/text-overlays \
  -H "Content-Type: application/json" \
  -d '{
    "shot_id": "550e8400-e29b-41d4-a716-446655440040",
    "overlay_type": "lower_third",
    "text": "JOHN SMITH\nDetective",
    "position": "bottom_left",
    "style": {
      "font_family": "Helvetica",
      "font_size": 24,
      "color": "#FFFFFF",
      "background_color": "#000000AA"
    },
    "animation_in": "slide_up",
    "animation_out": "fade_out",
    "start_time_ms": 1000,
    "duration_ms": 3000
  }'
```

---

### PATCH /api/v1/text-overlays/{overlay_id}

Update overlay.

```bash
curl -X PATCH http://localhost:8000/api/v1/text-overlays/550e8400-e29b-41d4-a716-446655440140 \
  -H "Content-Type: application/json" \
  -d '{"text": "Updated text"}'
```

---

### DELETE /api/v1/text-overlays/{overlay_id}

Delete overlay.

```bash
curl -X DELETE http://localhost:8000/api/v1/text-overlays/550e8400-e29b-41d4-a716-446655440140
```

---

## WebSocket API

Real-time updates.

**Base Path:** `/ws`

### WS /ws

WebSocket connection for real-time updates.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// Subscribe to project updates
ws.send(JSON.stringify({
  action: 'subscribe',
  project_id: '550e8400-e29b-41d4-a716-446655440000'
}));

// Subscribe to job updates
ws.send(JSON.stringify({
  action: 'subscribe_job',
  job_id: '550e8400-e29b-41d4-a716-446655440060'
}));

// Handle messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

**Message Types:**

| Type | Description |
|------|-------------|
| `subscribed` | Subscription confirmed |
| `subscribed_job` | Job subscription confirmed |
| `project_update` | Project state changed |
| `job_update` | Job progress/status changed |
| `generation_complete` | Generation finished |
| `error` | Error message |
| `pong` | Heartbeat response |

---

### GET /ws/stats

Get WebSocket connection statistics.

```bash
curl http://localhost:8000/ws/stats
```

---

## Related Documentation

- [Security Guide](../SECURITY.md) - Authentication and security details
- [Database Schema](../DATABASE.md) - Data models and relationships
- [Configuration Reference](../CONFIGURATION.md) - Environment variables
- [IPC API Reference](README.md) - Desktop app IPC documentation
