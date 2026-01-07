# SceneMachine Database Schema

Complete database documentation including entity relationships, model reference, migrations, and query patterns.

## Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [Entity Relationship Diagrams](#entity-relationship-diagrams)
- [Model Reference](#model-reference)
  - [Core Module](#core-module)
  - [ActForge Module](#actforge-module)
  - [Settings Module](#settings-module)
- [Enumerations Reference](#enumerations-reference)
- [Migrations](#migrations)
- [Indexes and Constraints](#indexes-and-constraints)
- [Query Patterns](#query-patterns)
- [Database Configuration](#database-configuration)

---

## Overview

SceneMachine uses a relational database to persist all project data, from screenplays through final exports. The schema is designed for:

- **Hierarchical Data**: Projects contain Screenplays, Characters, and Scenes; Scenes contain Shots
- **State Machines**: Projects, Scenes, Shots, and Bookings track workflow states
- **Audit Trails**: All entities have `created_at` and `updated_at` timestamps
- **Soft Relationships**: Optional references allow flexible associations
- **JSON Fields**: Complex nested data (settings, metadata) stored as JSONB/JSON

**Total Models:** 19
**Total Tables:** 19
**Total Enumerations:** 35+

---

## Technology Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **ORM** | SQLAlchemy 2.0 | Async support via AsyncSession |
| **Migrations** | Alembic | 6 migrations to date |
| **Production DB** | PostgreSQL 14+ | JSONB, UUID native types |
| **Development DB** | SQLite | JSON emulation, String UUIDs |
| **Connection Pool** | AsyncPG | Async PostgreSQL driver |

### Database Agnostic Types

The codebase uses custom TypeDecorators for cross-database compatibility:

```python
# packages/core/scenemachine/models/base.py

class JSONType(TypeDecorator):
    """Uses JSONB on PostgreSQL, JSON on SQLite."""
    impl = JSON
    cache_ok = True

class ArrayType(TypeDecorator):
    """Uses native ARRAY on PostgreSQL, JSON on SQLite."""
    impl = JSON
    cache_ok = True

class UUIDType(TypeDecorator):
    """Uses native UUID on PostgreSQL, String(36) on SQLite."""
    impl = String(36)
    cache_ok = True
```

---

## Entity Relationship Diagrams

### Core Module ER Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE MODULE                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐         ┌──────────────┐         ┌────────────────┐
│   Project   │ 1 ─── 1 │  Screenplay  │         │  UserSettings  │
│─────────────│         │──────────────│         │────────────────│
│ id (PK)     │         │ id (PK)      │         │ id (PK)        │
│ name        │         │ project_id   │◄────────│ settings_key   │
│ description │         │ title        │         │ llm_provider   │
│ state       │         │ format       │         │ video_provider │
│ settings    │         │ movie_plan   │         │ *_api_key      │
│             │         │ is_parsed    │         └────────────────┘
└──────┬──────┘         └──────────────┘
       │
       │ 1
       │
       ├────────────────────────────────────┐
       │                                    │
       ▼ N                                  ▼ N
┌──────────────┐                    ┌──────────────┐
│  Character   │                    │    Scene     │
│──────────────│                    │──────────────│
│ id (PK)      │                    │ id (PK)      │
│ project_id   │                    │ project_id   │
│ name         │                    │ scene_number │
│ lock_state   │                    │ location     │
│ physical_desc│                    │ time_of_day  │
│ locked_like. │                    │ state        │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       │ 1                                 │ 1
       ▼ N                                 ▼ N
┌──────────────┐                    ┌──────────────┐
│    Asset     │                    │     Shot     │
│──────────────│                    │──────────────│
│ id (PK)      │                    │ id (PK)      │
│ character_id │                    │ scene_id     │
│ asset_type   │                    │ shot_type    │
│ file_path    │                    │ camera_move  │
│ status       │                    │ state        │
└──────────────┘                    └──────┬───────┘
                                           │
                                           │ 1
                                           ▼ N
                                    ┌────────────────┐
                                    │ GenerationJob  │
                                    │────────────────│
                                    │ id (PK)        │
                                    │ shot_id        │
                                    │ job_type       │
                                    │ status         │
                                    │ provider       │
                                    │ progress       │
                                    └────────────────┘

Additional Core Relationships:
┌─────────────┐    1 ─── N    ┌───────────────┐
│   Project   │──────────────►│ ProjectShare  │
└─────────────┘               └───────────────┘
       │
       │ 1 ─── N    ┌─────────────────┐
       └───────────►│ ProjectComment  │
                    └─────────────────┘
       │
       │ 1 ─── N    ┌───────────────┐
       └───────────►│ ExportHistory │
                    └───────────────┘

Audio & Text Overlays (standalone tables):
┌──────────────┐         ┌──────────────┐
│  AudioAsset  │         │ TextOverlay  │
│──────────────│         │──────────────│
│ id (PK)      │         │ id (PK)      │
│ asset_type   │         │ shot_id      │
│ name         │         │ scene_id     │
│ file_path    │         │ overlay_type │
│ category     │         │ text         │
└──────────────┘         └──────────────┘
```

### ActForge Module ER Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ACTFORGE MODULE                                    │
│                      (Talent Marketplace)                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐         ┌───────────────────┐
│    Performer    │ 1 ─── N │  PerformanceTake  │
│─────────────────│         │───────────────────│
│ id (PK)         │         │ id (PK)           │
│ stage_name      │         │ performer_id      │
│ performer_type  │         │ mode (blink/deep) │
│ availability    │         │ duration_seconds  │
│ verification    │         │ motion_profile    │
│ aci_score       │         │ quality_metrics   │
│ total_bookings  │         │ status            │
│ revenue_split   │         └─────────┬─────────┘
│ pricing         │                   │
└────────┬────────┘                   │
         │                            │
         │ 1                          │ 1
         │                            │
         ├───────────────────────────►│
         │                            │
         ▼ N                          ▼ N
┌─────────────────┐         ┌─────────────────┐
│    Booking      │ 1 ─── 1 │ PerformerRating │
│─────────────────│         │─────────────────│
│ id (PK)         │         │ id (PK)         │
│ performer_id    │         │ booking_id (UQ) │
│ project_id      │         │ performer_id    │
│ take_id         │◄────────│ overall_score   │
│ booking_mode    │         │ would_rehire    │
│ status          │         │ review_text     │
│ price_usd       │         └─────────────────┘
│ payment_status  │
└─────────────────┘
         │
         │ relates to
         ▼
┌─────────────────┐         ┌─────────────────┐
│    Auction      │ 1 ─── N │   AuctionBid    │
│─────────────────│         │─────────────────│
│ id (PK)         │         │ id (PK)         │
│ project_id      │         │ auction_id      │
│ title           │         │ performer_id    │
│ status          │         │ bid_amount_usd  │
│ min_bid_usd     │         │ status          │
│ winning_bid_id  │◄────────│ pitch_message   │
└─────────────────┘         └─────────────────┘
```

### Cross-Module Relationships

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CROSS-MODULE RELATIONSHIPS                              │
└─────────────────────────────────────────────────────────────────────────────┘

Core Module                              ActForge Module
┌───────────┐                           ┌─────────────────┐
│  Project  │◄──────────────────────────│    Booking      │
│           │     project_id            │                 │
└───────────┘                           └─────────────────┘
                                                │
┌───────────┐                                   │
│   Shot    │◄──────────────────────────────────┤ shot_id
└───────────┘                                   │
                                                │
┌───────────────┐                               │
│GenerationJob  │  Uses performer motion data   │
│  (ACTCORE     │  from completed bookings      │
│   provider)   │◄──────────────────────────────┘
└───────────────┘
```

---

## Model Reference

### Core Module

#### Project

Central entity representing a movie production project.

**Table:** `projects`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `name` | String(255) | No | - | Project name |
| `description` | Text | Yes | - | Optional description |
| `state` | Enum | No | EMPTY | Workflow state |
| `settings` | JSONB | No | {} | Project settings |
| `created_at` | DateTime | No | now() | Creation timestamp |
| `updated_at` | DateTime | No | now() | Last update timestamp |

**Relationships:**
- `screenplay` - One-to-one with Screenplay (cascade delete)
- `characters` - One-to-many with Character (cascade delete)
- `scenes` - One-to-many with Scene (cascade delete, ordered by sequence_number)
- `shares` - One-to-many with ProjectShare (cascade delete)
- `export_history` - One-to-many with ExportHistory (cascade delete)

**State Machine:** See [ProjectState Enum](#projectstate)

**Settings JSON Structure:**
```json
{
  "visual_style": {
    "aspect_ratio": "16:9",
    "color_palette": "warm",
    "lighting_preference": "natural"
  },
  "generation": {
    "quality_preset": "high",
    "preferred_provider": "local",
    "max_concurrent_jobs": 2
  },
  "export": {
    "format": "mp4",
    "resolution": "1920x1080",
    "frame_rate": 24
  }
}
```

---

#### Screenplay

Screenplay document associated with a project.

**Table:** `screenplays`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `project_id` | UUID | No | - | FK to projects (unique) |
| `original_filename` | String(255) | No | - | Uploaded filename |
| `original_format` | Enum | No | - | File format |
| `file_hash` | String(64) | No | - | SHA-256 hash |
| `original_file_path` | String(512) | No | - | Storage path |
| `parsed_content` | JSONB | Yes | - | Structured screenplay data |
| `movie_plan` | JSONB | Yes | - | AI-generated plan |
| `movie_plan_approved` | Boolean | No | false | User approval flag |
| `is_parsed` | Boolean | No | false | Parsing complete flag |
| `parse_errors` | JSONB | Yes | - | Parsing errors list |

**Unique Constraint:** One screenplay per project (`project_id` is unique)

**Parsed Content Structure:**
```json
{
  "title_page": {
    "title": "My Movie",
    "author": "Writer Name",
    "draft_date": "2024-01-15"
  },
  "elements": [
    {
      "type": "scene_heading",
      "scene_number": "1",
      "location": "COFFEE SHOP",
      "time_of_day": "DAY"
    },
    {
      "type": "dialogue",
      "character": "SARAH",
      "text": "Hello world."
    }
  ],
  "metadata": {
    "page_count": 120,
    "scene_count": 45,
    "character_count": 12
  }
}
```

---

#### Character

Character with likeness definition for consistent generation.

**Table:** `characters`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `project_id` | UUID | No | - | FK to projects |
| `name` | String(255) | No | - | Display name |
| `screenplay_name` | String(255) | No | - | Original screenplay name |
| `description` | Text | Yes | - | Character description |
| `age_range_min` | Integer | Yes | - | Minimum age |
| `age_range_max` | Integer | Yes | - | Maximum age |
| `gender` | Enum | No | UNSPECIFIED | Gender |
| `physical_description` | JSONB | Yes | - | Structured appearance |
| `personality_traits` | Array(String) | Yes | - | Trait keywords |
| `voice_description` | Text | Yes | - | Voice characteristics |
| `lock_state` | Enum | No | UNDEFINED | Workflow state |
| `locked_likeness` | JSONB | Yes | - | Final approved likeness |
| `scene_count` | Integer | No | 0 | Scenes appearing in |
| `dialogue_count` | Integer | No | 0 | Dialogue line count |
| `is_protagonist` | Boolean | No | false | Main character flag |
| `consent_status` | JSONB | Yes | - | Ethics tracking |

**Index:** `project_id`

**Physical Description Structure:**
```json
{
  "hair_color": "brown",
  "hair_style": "short, wavy",
  "eye_color": "blue",
  "skin_tone": "fair",
  "height": "tall",
  "build": "athletic",
  "facial_features": {
    "face_shape": "oval",
    "jawline": "strong"
  },
  "distinguishing_features": ["scar on left cheek"]
}
```

---

#### Scene

Scene with shot breakdown and generation plan.

**Table:** `scenes`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `project_id` | UUID | No | - | FK to projects |
| `scene_number` | String(20) | No | - | Scene identifier |
| `sequence_number` | Integer | No | - | Sort order |
| `scene_type` | Enum | No | - | INT/EXT/INT-EXT |
| `location` | String(255) | No | - | Location name |
| `sub_location` | String(255) | Yes | - | Sub-location |
| `time_of_day` | Enum | No | - | Lighting time |
| `raw_content` | Text | No | - | Original screenplay text |
| `action_lines` | Array(Text) | No | [] | Action descriptions |
| `dialogue_blocks` | JSONB | Yes | - | Dialogue data |
| `character_ids` | Array(String) | No | [] | Character UUIDs |
| `analysis` | JSONB | Yes | - | AI scene analysis |
| `shot_breakdown` | JSONB | Yes | - | Shot plan |
| `shot_breakdown_approved` | Boolean | No | false | Approval flag |
| `generation_settings` | JSONB | Yes | - | Scene overrides |
| `estimated_duration_seconds` | Float | Yes | - | Planned duration |
| `actual_duration_seconds` | Float | Yes | - | Final duration |
| `state` | Enum | No | PARSED | Workflow state |

**Index:** `project_id`

---

#### Shot

Atomic generation unit within a scene.

**Table:** `shots`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `scene_id` | UUID | No | - | FK to scenes |
| `shot_number` | String(20) | No | - | Shot identifier (1A, 1B) |
| `sequence_number` | Integer | No | - | Sort order |
| `shot_type` | Enum | No | - | Camera shot type |
| `camera_movement` | Enum | No | STATIC | Movement type |
| `description` | Text | No | - | Visual description |
| `dialogue` | Text | Yes | - | Dialogue in shot |
| `action` | Text | Yes | - | Action description |
| `character_ids` | Array(String) | No | [] | Visible characters |
| `composition_notes` | Text | Yes | - | Framing guidance |
| `lighting_notes` | Text | Yes | - | Lighting guidance |
| `color_notes` | Text | Yes | - | Color guidance |
| `generation_prompt` | Text | Yes | - | Final prompt |
| `negative_prompt` | Text | Yes | - | Negative prompt |
| `generation_params` | JSONB | Yes | - | Generation parameters |
| `duration_seconds` | Float | No | 3.0 | Target duration |
| `actual_duration_seconds` | Float | Yes | - | Generated duration |
| `state` | Enum | No | PLANNED | Workflow state |
| `output_video_path` | String(512) | Yes | - | Generated video path |
| `output_thumbnail_path` | String(512) | Yes | - | Thumbnail path |
| `generation_metadata` | JSONB | Yes | - | Generation details |
| `user_notes` | Text | Yes | - | User feedback |
| `rating` | Integer | Yes | - | 1-5 rating |
| `rejection_reason` | Text | Yes | - | Rejection feedback |
| `version` | Integer | No | 1 | Version number |
| `previous_version_id` | UUID | Yes | - | Previous version FK |

**Index:** `scene_id`

---

#### Asset

Digital asset (image, video, model weights).

**Table:** `assets`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `project_id` | UUID | No | - | FK to projects |
| `character_id` | UUID | Yes | - | FK to characters |
| `shot_id` | UUID | Yes | - | FK to shots |
| `scene_id` | UUID | Yes | - | FK to scenes |
| `asset_type` | Enum | No | - | Asset classification |
| `status` | Enum | No | UPLOADED | Processing status |
| `filename` | String(255) | No | - | File name |
| `file_path` | String(512) | No | - | Storage path |
| `file_hash` | String(64) | Yes | - | SHA-256 hash |
| `file_size_bytes` | Integer | Yes | - | File size |
| `mime_type` | String(100) | Yes | - | MIME type |
| `display_name` | String(255) | Yes | - | User-friendly name |
| `description` | Text | Yes | - | Description |
| `asset_metadata` | JSONB | Yes | - | Type-specific metadata |
| `source_info` | JSONB | Yes | - | Generation source info |

**Indexes:** `project_id`, `character_id`, `shot_id`, `scene_id`, `asset_type`

---

#### GenerationJob

Video/image generation job tracking.

**Table:** `generation_jobs`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `project_id` | UUID | No | - | FK to projects |
| `shot_id` | UUID | Yes | - | FK to shots |
| `scene_id` | UUID | Yes | - | FK to scenes |
| `character_id` | UUID | Yes | - | FK to characters |
| `job_type` | Enum | No | - | Generation type |
| `status` | Enum | No | PENDING | Job status |
| `provider` | Enum | No | LOCAL | Execution provider |
| `priority` | Integer | No | 50 | Queue priority (0-100) |
| `queue_position` | Integer | Yes | - | Queue position |
| `retry_count` | Integer | No | 0 | Retry attempts |
| `max_retries` | Integer | No | 3 | Max retry attempts |
| `progress` | Float | No | 0.0 | Progress 0-100 |
| `progress_message` | String(255) | Yes | - | Status message |
| `input_params` | JSONB | Yes | - | Generation inputs |
| `output_info` | JSONB | Yes | - | Output details |
| `error_info` | JSONB | Yes | - | Error details |
| `cost_info` | JSONB | Yes | - | Cost tracking |
| `queued_at` | DateTime | Yes | - | Queue timestamp |
| `started_at` | DateTime | Yes | - | Start timestamp |
| `completed_at` | DateTime | Yes | - | Completion timestamp |
| `external_job_id` | String(255) | Yes | - | Provider job ID |
| `worker_id` | String(255) | Yes | - | Worker identifier |

**Indexes:** `project_id`, `shot_id`, `scene_id`, `character_id`, `job_type`, `status`

---

#### ProjectShare

Project sharing and collaboration.

**Table:** `project_shares`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `project_id` | UUID | No | - | FK to projects |
| `share_code` | String(64) | No | - | Unique share link |
| `recipient_email` | String(255) | Yes | - | Recipient email |
| `recipient_name` | String(255) | Yes | - | Recipient name |
| `permission` | Enum | No | VIEW | Permission level |
| `status` | Enum | No | PENDING | Share status |
| `message` | Text | Yes | - | Share message |
| `expires_at` | DateTime | Yes | - | Expiration time |
| `last_accessed_at` | DateTime | Yes | - | Last access time |
| `access_count` | Integer | No | 0 | Access counter |
| `is_public` | Boolean | No | false | Public access flag |

**Indexes:** `project_id`, `share_code` (unique)

---

#### ProjectComment

Comments and feedback on projects/shots.

**Table:** `project_comments`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `project_id` | UUID | No | - | FK to projects |
| `shot_id` | UUID | Yes | - | FK to shots |
| `parent_id` | UUID | Yes | - | Parent comment (replies) |
| `author_name` | String(255) | No | - | Author name |
| `author_email` | String(255) | Yes | - | Author email |
| `content` | Text | No | - | Comment text |
| `timecode_seconds` | Float | Yes | - | Video timecode |
| `is_resolved` | Boolean | No | false | Resolution status |
| `resolved_at` | DateTime | Yes | - | Resolution time |

**Indexes:** `project_id`, `shot_id`

**Self-Referential:** `parent_id` references `project_comments.id` for threaded replies.

---

#### ExportHistory

Export tracking with full metadata.

**Table:** `export_history`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `project_id` | UUID | No | - | FK to projects |
| `format` | String(50) | No | mp4_h264 | Export format |
| `quality` | String(50) | No | high | Quality preset |
| `resolution` | String(20) | No | 1920x1080 | Target resolution |
| `frame_rate` | Integer | No | 24 | Frame rate |
| `video_bitrate` | String(20) | Yes | - | Video bitrate |
| `audio_bitrate` | String(20) | Yes | - | Audio bitrate |
| `status` | String(50) | No | pending | Export status |
| `progress_percent` | Float | No | 0.0 | Progress 0-100 |
| `output_filename` | String(255) | Yes | - | Output filename |
| `output_path` | Text | Yes | - | Output path |
| `file_size_bytes` | Integer | Yes | - | File size |
| `actual_duration_seconds` | Float | Yes | - | Actual duration |
| `video_codec` | String(50) | Yes | - | Video codec used |
| `audio_codec` | String(50) | Yes | - | Audio codec used |
| `started_at` | DateTime | Yes | - | Start time |
| `completed_at` | DateTime | Yes | - | Completion time |
| `error_message` | Text | Yes | - | Error details |
| `include_subtitles` | Boolean | No | false | Subtitles flag |
| `include_audio` | Boolean | No | true | Audio flag |
| `has_watermark` | Boolean | No | false | Watermark flag |

**Index:** `project_id`, `status`

---

#### AudioAsset

Sound effects and music tracks.

**Table:** `audio_assets`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `asset_type` | Enum | No | - | sfx or music |
| `name` | String(255) | No | - | Asset name |
| `description` | Text | Yes | - | Description |
| `file_path` | String(512) | No | - | File path |
| `file_size_bytes` | Integer | Yes | - | File size |
| `duration_seconds` | Float | No | 0.0 | Duration |
| `mime_type` | String(100) | Yes | - | MIME type |
| `waveform_path` | String(512) | Yes | - | Waveform image |
| `category` | String(50) | No | other | Category |
| `subcategory` | String(50) | Yes | - | Subcategory |
| `tags` | Array(String) | Yes | - | Search tags |
| `artist` | String(255) | Yes | - | Artist name |
| `genre` | String(50) | Yes | - | Music genre |
| `bpm` | Integer | Yes | - | Beats per minute |
| `mood` | Array(String) | Yes | - | Mood tags |
| `key` | String(20) | Yes | - | Musical key |
| `is_favorite` | Boolean | No | false | Favorite flag |
| `use_count` | Integer | No | 0 | Usage counter |
| `is_system` | Boolean | No | false | System asset flag |
| `license_type` | String(50) | Yes | - | License type |
| `license_info` | JSONB | Yes | - | License details |

---

#### TextOverlay

Text overlays for titles, captions, lower thirds.

**Table:** `text_overlays`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `shot_id` | UUID | Yes | - | FK to shots |
| `scene_id` | UUID | Yes | - | FK to scenes |
| `project_id` | UUID | Yes | - | FK to projects |
| `overlay_type` | Enum | No | CUSTOM | Overlay type |
| `text` | Text | No | - | Display text |
| `position` | Enum | No | CENTER | Position preset |
| `custom_x` | Float | Yes | - | X position (0-100%) |
| `custom_y` | Float | Yes | - | Y position (0-100%) |
| `style` | JSONB | Yes | {} | Style settings |
| `animation_in` | Enum | No | FADE_IN | Entry animation |
| `animation_out` | Enum | No | FADE_OUT | Exit animation |
| `animation_in_duration_ms` | Integer | No | 500 | Entry duration |
| `animation_out_duration_ms` | Integer | No | 500 | Exit duration |
| `start_time_ms` | Integer | No | 0 | Start time |
| `duration_ms` | Integer | No | 5000 | Display duration |
| `is_visible` | Boolean | No | true | Visibility flag |
| `z_index` | Integer | No | 1 | Layer order |

**Indexes:** `shot_id`, `scene_id`, `project_id`

---

### ActForge Module

#### Performer

ActCore performer (human or synthetic).

**Table:** `performers`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `stage_name` | String(255) | No | - | Public name |
| `legal_name` | String(255) | Yes | - | Legal name (encrypted) |
| `user_id` | UUID | Yes | - | Associated user |
| `performer_type` | Enum | No | HUMAN | Human or synthetic |
| `availability_status` | Enum | No | OFFLINE | Current availability |
| `verification_status` | Enum | No | UNVERIFIED | Verification level |
| `profile_image_path` | String(500) | Yes | - | Profile image |
| `bio` | Text | Yes | - | Biography |
| `specialties` | Array(String) | Yes | - | Motion specialties |
| `aci_score` | Float | No | 50.0 | ActCast Index score |
| `total_bookings` | Integer | No | 0 | Total bookings |
| `completed_bookings` | Integer | No | 0 | Completed bookings |
| `total_earnings_usd` | Float | No | 0.0 | Total earnings |
| `lifetime_earnings_usd` | Float | No | 0.0 | Lifetime earnings |
| `revenue_split_percent` | Float | No | 50.0 | Revenue split |
| `motion_capabilities` | JSONB | Yes | - | Supported features |
| `pricing` | JSONB | Yes | - | Pricing tiers |
| `banking_info` | JSONB | Yes | - | Banking (encrypted) |
| `is_active` | Boolean | No | true | Active status |
| `last_active_at` | DateTime | Yes | - | Last activity |
| `joined_at` | DateTime | No | - | Join date |

**Indexes:** `stage_name`, `user_id`, `availability_status`, `aci_score`

**ACI Score Calculation:**
```
ACI = (Placement Rate × 0.4) + (Rehire Rate × 0.3) +
      (Audience Buzz × 0.2) + (MotionScore × 0.1)
```

**Revenue Split Tiers:**
| Lifetime Earnings | Revenue Split |
|------------------|---------------|
| $0 - $999 | 50% |
| $1k - $9,999 | 60% |
| $10k - $99,999 | 70% |
| $100k - $999,999 | 80% |
| $1M - $9.99M | 90% |
| $10M+ | 99% |

---

#### PerformanceTake

Recorded performance with motion data.

**Table:** `performance_takes`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `performer_id` | UUID | No | - | FK to performers |
| `take_name` | String(255) | No | - | Take name |
| `mode` | Enum | No | BLINK | Booking mode |
| `duration_seconds` | Float | No | - | Duration |
| `recording_date` | DateTime | No | - | Recording date |
| `emotion_tags` | Array(String) | Yes | - | Emotion descriptors |
| `scene_context` | Text | Yes | - | Scene description |
| `motion_profile` | JSONB | Yes | - | Motion data paths |
| `quality_metrics` | JSONB | Yes | - | Quality scores |
| `status` | Enum | No | PROCESSING | Take status |
| `is_demo_reel` | Boolean | No | false | Demo reel flag |
| `usage_count` | Integer | No | 0 | Usage counter |
| `last_used_at` | DateTime | Yes | - | Last usage time |
| `storage_path` | String(500) | Yes | - | Storage location |
| `file_size_bytes` | Integer | Yes | - | File size |
| `thumbnail_path` | String(500) | Yes | - | Thumbnail |
| `preview_video_path` | String(500) | Yes | - | Preview video |
| `processed_at` | DateTime | Yes | - | Processing time |
| `processing_error` | Text | Yes | - | Error message |

**Index:** `performer_id`, `mode`, `status`

**Motion Profile Structure:**
```json
{
  "liveportrait_vectors_path": "takes/uuid/vectors.npy",
  "roop_gs_anim_path": "takes/uuid/roop_motion.json",
  "face_embedding_path": "takes/uuid/face_embed.pkl",
  "landmark_data_path": "takes/uuid/landmarks.json"
}
```

---

#### Booking

Talent booking in ActForge marketplace.

**Table:** `bookings`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `project_id` | UUID | No | - | FK to projects |
| `shot_id` | UUID | Yes | - | FK to shots |
| `performer_id` | UUID | Yes | - | FK to performers |
| `requester_user_id` | UUID | No | - | Requesting user |
| `take_id` | UUID | Yes | - | Delivered take |
| `booking_mode` | Enum | No | - | Booking type |
| `status` | Enum | No | REQUESTED | Booking status |
| `duration_requested_seconds` | Float | No | - | Requested duration |
| `duration_delivered_seconds` | Float | Yes | - | Delivered duration |
| `emotion_requirements` | Array(String) | Yes | - | Required emotions |
| `motion_requirements` | JSONB | Yes | - | Motion specs |
| `special_instructions` | Text | Yes | - | Instructions |
| `price_usd` | Float | No | - | Agreed price |
| `platform_fee_usd` | Float | No | 0.0 | Platform fee |
| `performer_payout_usd` | Float | No | 0.0 | Performer payout |
| `payment_status` | Enum | No | PENDING | Payment status |
| `stripe_payment_intent_id` | String(255) | Yes | - | Stripe payment ID |
| `requested_at` | DateTime | No | - | Request time |
| `matched_at` | DateTime | Yes | - | Match time |
| `delivered_at` | DateTime | Yes | - | Delivery time |
| `completed_at` | DateTime | Yes | - | Completion time |
| `is_disputed` | Boolean | No | false | Dispute flag |
| `retry_count` | Integer | No | 0 | Retry attempts |

**Indexes:** `project_id`, `shot_id`, `performer_id`, `booking_mode`, `status`

**State Machine:**
```
REQUESTED → MATCHING → MATCHED → ACCEPTED → IN_PROGRESS
                                                ↓
                                          DELIVERED
                                           ↓     ↓
                                    APPROVED  DISPUTED
                                        ↓         ↓
                                   COMPLETED  (resolution)
```

---

#### Auction

Auction for booking premium talent.

**Table:** `auctions`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `project_id` | UUID | No | - | FK to projects |
| `shot_id` | UUID | Yes | - | FK to shots |
| `creator_user_id` | UUID | No | - | Creator |
| `title` | String(255) | No | - | Auction title |
| `description` | Text | Yes | - | Description |
| `status` | Enum | No | DRAFT | Auction status |
| `requirements` | JSONB | Yes | - | Requirements |
| `min_aci_score` | Float | No | 0.0 | Minimum ACI |
| `required_specialties` | Array(String) | Yes | - | Required skills |
| `min_bid_usd` | Float | No | - | Minimum bid |
| `max_bid_usd` | Float | Yes | - | Maximum budget |
| `reserve_price_usd` | Float | Yes | - | Reserve price |
| `duration_hours` | Integer | No | 24 | Auction duration |
| `opens_at` | DateTime | Yes | - | Open time |
| `closes_at` | DateTime | Yes | - | Close time |
| `winning_bid_id` | UUID | Yes | - | Winning bid |
| `total_bids` | Integer | No | 0 | Bid count |
| `unique_bidders` | Integer | No | 0 | Bidder count |
| `highest_bid_usd` | Float | Yes | - | Highest bid |

**Indexes:** `project_id`, `creator_user_id`, `status`

---

#### AuctionBid

Bid placed on an auction.

**Table:** `auction_bids`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `auction_id` | UUID | No | - | FK to auctions |
| `performer_id` | UUID | No | - | FK to performers |
| `sample_take_id` | UUID | Yes | - | Sample take |
| `bid_amount_usd` | Float | No | - | Bid amount |
| `proposed_delivery_hours` | Integer | No | 24 | Delivery time |
| `pitch_message` | Text | Yes | - | Pitch message |
| `status` | Enum | No | ACTIVE | Bid status |
| `bid_at` | DateTime | No | - | Bid timestamp |
| `withdrawn_at` | DateTime | Yes | - | Withdrawal time |
| `auto_bid_enabled` | Boolean | No | false | Auto-bid flag |
| `auto_bid_max_usd` | Float | Yes | - | Auto-bid max |
| `auto_bid_increment_usd` | Float | Yes | - | Auto increment |

**Indexes:** `auction_id`, `performer_id`, `status`

---

#### PerformerRating

Rating given after completing a booking.

**Table:** `performer_ratings`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `booking_id` | UUID | No | - | FK to bookings (unique) |
| `performer_id` | UUID | No | - | FK to performers |
| `rater_user_id` | UUID | No | - | Rating user |
| `overall_score` | Float | No | - | Overall 1.0-5.0 |
| `motion_quality_score` | Float | Yes | - | Motion quality |
| `emotion_accuracy_score` | Float | Yes | - | Emotion accuracy |
| `professionalism_score` | Float | Yes | - | Professionalism |
| `timeliness_score` | Float | Yes | - | Timeliness |
| `would_rehire` | Boolean | No | - | Rehire indicator |
| `review_text` | Text | Yes | - | Review text |
| `review_title` | String(255) | Yes | - | Review title |
| `is_public` | Boolean | No | true | Public visibility |
| `audience_buzz_votes` | Integer | No | 0 | Buzz votes |
| `helpful_votes` | Integer | No | 0 | Helpful votes |
| `is_flagged` | Boolean | No | false | Moderation flag |
| `performer_response` | Text | Yes | - | Response text |
| `rated_at` | DateTime | No | - | Rating timestamp |

**Unique Constraint:** One rating per booking (`booking_id`)

**Index:** `performer_id`, `rater_user_id`

---

### Settings Module

#### UserSettings

User-configurable application settings.

**Table:** `user_settings`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | uuid4() | Primary key |
| `settings_key` | String(50) | No | default | Settings identifier |
| `llm_provider` | String(50) | Yes | anthropic | LLM provider |
| `video_provider` | String(50) | Yes | local | Video provider |
| `anthropic_api_key` | Text | Yes | - | Encrypted API key |
| `openai_api_key` | Text | Yes | - | Encrypted API key |
| `replicate_api_key` | Text | Yes | - | Encrypted API key |
| `fal_api_key` | Text | Yes | - | Encrypted API key |
| `runwayml_api_key` | Text | Yes | - | Encrypted API key |
| `max_concurrent_generations` | Integer | No | 2 | Concurrent jobs |
| `generation_timeout_seconds` | Integer | No | 600 | Job timeout |
| `default_video_resolution` | String(20) | No | 1920x1080 | Resolution |
| `default_video_fps` | Integer | No | 24 | Frame rate |
| `theme_mode` | String(20) | No | dark | UI theme |
| `auto_save_enabled` | Boolean | No | true | Auto-save |
| `show_advanced_options` | Boolean | No | false | Advanced UI |
| `auto_cleanup_temp_files` | Boolean | No | true | Cleanup flag |
| `max_cache_size_gb` | Integer | No | 10 | Cache limit |
| `default_export_format` | String(20) | No | mp4_h264 | Export format |
| `default_export_quality` | String(20) | No | high | Export quality |
| `font_size_scale` | String(20) | No | medium | Accessibility |
| `high_contrast_enabled` | Boolean | No | false | Accessibility |
| `reduce_motion_enabled` | Boolean | No | false | Accessibility |
| `large_click_targets_enabled` | Boolean | No | false | Accessibility |
| `additional_settings` | JSONB | Yes | {} | Extra settings |

**Unique Constraint:** `settings_key`

**API Key Encryption:** Fernet (AES-128-CBC) with PBKDF2HMAC key derivation. See [SECURITY.md](SECURITY.md) for details.

---

## Enumerations Reference

### ProjectState

```python
class ProjectState(str, Enum):
    EMPTY = "empty"                           # Just created
    SCREENPLAY_UPLOADED = "screenplay_uploaded"
    SCREENPLAY_PARSED = "screenplay_parsed"
    PLAN_GENERATED = "plan_generated"
    PLAN_APPROVED = "plan_approved"
    CHARACTERS_IN_PROGRESS = "characters_in_progress"
    CHARACTERS_LOCKED = "characters_locked"
    SCENES_PLANNING = "scenes_planning"
    SCENES_APPROVED = "scenes_approved"
    GENERATING = "generating"
    GENERATION_COMPLETE = "generation_complete"
    ASSEMBLY_IN_PROGRESS = "assembly_in_progress"
    COMPLETE = "complete"
    EXPORTED = "exported"
```

### CharacterLockState

```python
class CharacterLockState(str, Enum):
    UNDEFINED = "undefined"
    DRAFT = "draft"
    REFERENCE_UPLOADED = "reference_uploaded"
    GENERATING = "generating"
    REVIEW = "review"
    LOCKED = "locked"
```

### SceneState

```python
class SceneState(str, Enum):
    PARSED = "parsed"
    PLANNED = "planned"
    PLAN_APPROVED = "plan_approved"
    GENERATING = "generating"
    GENERATED = "generated"
    REVIEW = "review"
    APPROVED = "approved"
    LOCKED = "locked"
```

### ShotState

```python
class ShotState(str, Enum):
    PLANNED = "planned"
    QUEUED = "queued"
    GENERATING = "generating"
    GENERATED = "generated"
    FAILED = "failed"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REGENERATING = "regenerating"
```

### JobStatus

```python
class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
```

### JobProvider

```python
class JobProvider(str, Enum):
    LOCAL = "local"
    SCENEMACHINE_CLOUD = "scenemachine_cloud"
    REPLICATE = "replicate"
    RUNPOD = "runpod"
    MODAL = "modal"
    COMFYUI = "comfyui"
    CUSTOM = "custom"
    ACTCORE = "actcore"
    LAMBDA_LABS = "lambda_labs"
    VAST_AI = "vast_ai"
    FLUIDSTACK = "fluidstack"
    COREWEAVE = "coreweave"
```

### BookingStatus

```python
class BookingStatus(str, Enum):
    REQUESTED = "requested"
    MATCHING = "matching"
    MATCHED = "matched"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    APPROVED = "approved"
    DISPUTED = "disputed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
```

### ShotType

```python
class ShotType(str, Enum):
    ESTABLISHING = "establishing"
    WIDE = "wide"
    FULL = "full"
    MEDIUM = "medium"
    MEDIUM_CLOSE_UP = "medium_close_up"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_THE_SHOULDER = "over_the_shoulder"
    POV = "pov"
    TWO_SHOT = "two_shot"
    GROUP = "group"
    INSERT = "insert"
    CUTAWAY = "cutaway"
    AERIAL = "aerial"
    LOW_ANGLE = "low_angle"
    HIGH_ANGLE = "high_angle"
    DUTCH_ANGLE = "dutch_angle"
```

### CameraMovement

```python
class CameraMovement(str, Enum):
    STATIC = "static"
    PAN = "pan"
    TILT = "tilt"
    DOLLY = "dolly"
    TRUCK = "truck"
    CRANE = "crane"
    HANDHELD = "handheld"
    STEADICAM = "steadicam"
    ZOOM = "zoom"
    RACK_FOCUS = "rack_focus"
    TRACKING = "tracking"
    PUSH_IN = "push_in"
    PULL_OUT = "pull_out"
    WHIP_PAN = "whip_pan"
    ORBIT = "orbit"
```

---

## Migrations

SceneMachine uses Alembic for database migrations.

### Migration History

| Version | Name | Description |
|---------|------|-------------|
| 001 | initial_schema | Core tables (projects, screenplays, characters, scenes, shots, assets, generation_jobs, user_settings) |
| 002 | add_sharing_tables | ProjectShare, ProjectComment tables |
| 003 | add_export_history | ExportHistory table with full metadata |
| 004 | add_integrity_constraints | CHECK constraints, partial indexes, cascade behaviors |
| 005 | add_actcore_tables | ActForge module (performers, takes, bookings, auctions, ratings) |
| 006 | add_accessibility_settings | Accessibility columns to user_settings |

### Running Migrations

```bash
# Check current version
alembic current

# Upgrade to latest
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Downgrade one version
alembic downgrade -1

# View migration history
alembic history
```

### Creating New Migrations

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "description"

# Create empty migration
alembic revision -m "description"
```

### Migration Best Practices

1. **Always test migrations** on a copy of production data
2. **Keep migrations small** - one logical change per migration
3. **Use batch operations** for large data modifications
4. **Add indexes in separate migrations** to avoid locking
5. **Document breaking changes** in migration docstring

---

## Indexes and Constraints

### Primary Key Convention

All tables use UUID primary keys generated client-side with `uuid4()`.

### Foreign Key Convention

```
fk_{table_name}_{column_name}_{referred_table_name}
```

### Index Convention

```
ix_{column_label}
```

### Naming Convention (Alembic)

```python
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

### Notable Indexes

| Table | Column(s) | Type | Purpose |
|-------|-----------|------|---------|
| `characters` | `project_id` | B-tree | Project filtering |
| `scenes` | `project_id` | B-tree | Project filtering |
| `shots` | `scene_id` | B-tree | Scene filtering |
| `generation_jobs` | `status` | B-tree | Queue queries |
| `generation_jobs` | `job_type` | B-tree | Type filtering |
| `performers` | `availability_status` | B-tree | Availability queries |
| `performers` | `aci_score` | B-tree | Ranking queries |
| `bookings` | `status` | B-tree | Status filtering |
| `project_shares` | `share_code` | Unique | Share lookup |

### CHECK Constraints

```sql
-- Rating bounds (added in migration 004)
ALTER TABLE performer_ratings
ADD CONSTRAINT ck_performer_ratings_overall_score
CHECK (overall_score >= 1.0 AND overall_score <= 5.0);

-- Progress bounds
ALTER TABLE generation_jobs
ADD CONSTRAINT ck_generation_jobs_progress
CHECK (progress >= 0.0 AND progress <= 100.0);

-- ACI score bounds
ALTER TABLE performers
ADD CONSTRAINT ck_performers_aci_score
CHECK (aci_score >= 0.0 AND aci_score <= 100.0);
```

### Cascade Behaviors

| Parent | Child | On Delete |
|--------|-------|-----------|
| `projects` | `screenplays` | CASCADE |
| `projects` | `characters` | CASCADE |
| `projects` | `scenes` | CASCADE |
| `scenes` | `shots` | CASCADE |
| `shots` | `generation_jobs` | SET NULL |
| `performers` | `performance_takes` | CASCADE |
| `performers` | `performer_ratings` | CASCADE |
| `bookings` | `performer_ratings` | CASCADE |

---

## Query Patterns

### Eager Loading

Always use eager loading for relationships to avoid N+1 queries:

```python
from sqlalchemy.orm import selectinload

# Load project with all relationships
stmt = (
    select(Project)
    .options(
        selectinload(Project.screenplay),
        selectinload(Project.characters),
        selectinload(Project.scenes).selectinload(Scene.shots),
    )
    .where(Project.id == project_id)
)
result = await session.execute(stmt)
project = result.scalar_one_or_none()
```

### Pagination

```python
# Paginated project list
stmt = (
    select(Project)
    .order_by(Project.updated_at.desc())
    .offset(skip)
    .limit(limit)
)
```

### Filtering by State

```python
# Active generation jobs
stmt = (
    select(GenerationJob)
    .where(GenerationJob.status.in_([
        JobStatus.PENDING,
        JobStatus.QUEUED,
        JobStatus.RUNNING,
    ]))
    .order_by(GenerationJob.priority.desc())
)
```

### Aggregations

```python
from sqlalchemy import func

# Count shots by state
stmt = (
    select(Shot.state, func.count(Shot.id))
    .where(Shot.scene_id == scene_id)
    .group_by(Shot.state)
)
```

### Transaction Patterns

```python
async with session.begin():
    # All operations in this block are atomic
    project = Project(name="New Project")
    session.add(project)

    screenplay = Screenplay(project_id=project.id, ...)
    session.add(screenplay)
    # Commit happens automatically on exit
```

### Bulk Operations

```python
from sqlalchemy import update

# Bulk update
stmt = (
    update(Shot)
    .where(Shot.scene_id == scene_id)
    .values(state=ShotState.QUEUED)
)
await session.execute(stmt)
await session.commit()
```

---

## Database Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///scenemachine.db` | Full database URL |
| `DB_POOL_SIZE` | `5` | Connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max overflow connections |
| `DB_POOL_TIMEOUT` | `30` | Pool timeout seconds |
| `DB_ECHO` | `false` | SQL echo for debugging |

### PostgreSQL URL Format

```
postgresql+asyncpg://user:password@host:5432/scenemachine
```

### SQLite URL Format (Development)

```
sqlite+aiosqlite:///./data/scenemachine.db
```

### Connection Factory

```python
# packages/core/scenemachine/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

---

## Related Documentation

- [SECURITY.md](SECURITY.md) - API key encryption details
- [CONFIGURATION.md](CONFIGURATION.md) - Database configuration options
- [REST-API.md](api/REST-API.md) - API endpoints using these models
