# Road Home Implementation Plan

## SceneMachine Platform: Complete Gap Closure & 10/10 UX Achievement

**Document Version**: 1.0
**Created**: 2026-01-10
**Status**: Ready for Execution

---

## Strategy Summary

This plan closes every identified gap in the SceneMachine platform through four sequential phases:

1. **Phase 1 (Fix First)**: Repair broken integrations blocking core value proposition (lip sync, audio paths, critical backend TODOs). Target: 2 weeks.
2. **Phase 2 (High Impact)**: Surface hidden functionality (audio workflow, multi-track timeline, booking UX). Target: 2 weeks.
3. **Phase 3 (Polish)**: Elevate all 7-9 UX features to 10/10 with micro-interactions, edge cases, and accessibility. Target: 1 week.
4. **Phase 4 (Network Integration)**: Bridge desktop app to network services (auth, distribution, monetization). Target: 3 weeks.

**Execution Principle**: Quality over speed. Every task must pass its acceptance criteria before moving forward. No feature ships without tests, error handling, and accessibility compliance.

---

## Table of Contents

1. [Definition of Done](#definition-of-done)
2. [Phase 1: Fix First (Critical)](#phase-1-fix-first-critical)
3. [Phase 2: High Impact](#phase-2-high-impact)
4. [Phase 3: Polish](#phase-3-polish)
5. [Phase 4: Network Integration](#phase-4-network-integration)
6. [Top 10 Highest-Leverage Improvements](#top-10-highest-leverage-improvements)
7. [Rollout Plan](#rollout-plan)
8. [Risk Register](#risk-register)

---

## Definition of Done

Every feature must meet ALL of the following criteria to be considered complete:

### Functional Requirements
- [ ] All acceptance criteria pass
- [ ] No console errors or warnings in browser/Electron
- [ ] No unhandled promise rejections
- [ ] No Python exceptions reaching the user
- [ ] All happy path flows complete without intervention
- [ ] All error paths show user-friendly messages
- [ ] All edge cases handled (empty states, boundary values, null data)

### User Experience Requirements
- [ ] Loading states shown for operations > 200ms
- [ ] Progress indicators for operations > 2 seconds
- [ ] Success confirmation for destructive or important actions
- [ ] Error messages include: what went wrong, why, and how to fix
- [ ] No dead-end screens (always provide next action)
- [ ] Consistent with existing design system (colors, spacing, typography)
- [ ] Responsive on all supported screen sizes (1280px - 4K)

### Accessibility Requirements
- [ ] All interactive elements keyboard-accessible
- [ ] Focus states visible on all interactive elements
- [ ] ARIA labels on icon-only buttons
- [ ] Screen reader announcements for dynamic content changes
- [ ] Color contrast meets WCAG 2.1 AA (4.5:1 for text)
- [ ] No information conveyed by color alone

### Code Quality Requirements
- [ ] TypeScript strict mode passes (no `any` types without justification)
- [ ] ESLint passes with zero warnings
- [ ] Python type hints on all function signatures
- [ ] No TODO comments left in shipped code
- [ ] Functions under 50 lines
- [ ] Files under 500 lines (split if larger)

### Testing Requirements
- [ ] Unit tests for all business logic functions
- [ ] Integration tests for API endpoints
- [ ] E2E tests for critical user paths
- [ ] Test coverage > 80% for new code
- [ ] All tests pass in CI

### Observability Requirements
- [ ] Errors logged with context (user action, relevant IDs)
- [ ] Performance-critical operations timed and logged
- [ ] Analytics events for key user actions

---

## Phase 1: Fix First (Critical)

**Duration**: 2 weeks
**Goal**: Repair all broken integrations and unblock core value proposition
**Priority**: UX scores currently 0-4, blocking user success

---

### Epic 1.1: Lip Sync Backend Completion

**Goal**: Make lip sync actually work by fixing backend TODOs
**Current UX Score**: 4/10 → Target: 9/10
**Owner**: Backend Engineer

---

#### Task 1.1.1: Fix Video/Audio Path Retrieval in Lipsync Route

**Goal**: Replace stub code with actual database queries to retrieve video and audio file paths.

**Scope**:
- INCLUDED: Fix lines 93 and 140 in `packages/core/scenemachine/api/routes/lipsync.py`
- INCLUDED: Add proper validation for video_id and audio_id existence
- EXCLUDED: Changing lip sync providers or algorithms
- EXCLUDED: Frontend changes

**Dependencies**:
- Database must have Asset model with file paths
- Shot model must reference video assets

**Prerequisites**:
- Read and understand the Asset and Shot models in `packages/core/scenemachine/models/`
- Understand the lipsync service in `packages/core/scenemachine/services/lipsync.py`

**Implementation Steps**:

1. Open `packages/core/scenemachine/api/routes/lipsync.py`

2. Locate the TODO at approximately line 93. Replace the stub with:
```python
# Validate video_id exists
video_asset = await db.execute(
    select(Asset).where(Asset.id == request.video_id)
)
video_asset = video_asset.scalar_one_or_none()
if not video_asset:
    raise HTTPException(
        status_code=404,
        detail=f"Video asset with id {request.video_id} not found"
    )
if video_asset.asset_type != AssetType.VIDEO:
    raise HTTPException(
        status_code=400,
        detail=f"Asset {request.video_id} is not a video"
    )

# Validate audio_id exists
audio_asset = await db.execute(
    select(Asset).where(Asset.id == request.audio_id)
)
audio_asset = audio_asset.scalar_one_or_none()
if not audio_asset:
    raise HTTPException(
        status_code=404,
        detail=f"Audio asset with id {request.audio_id} not found"
    )
if audio_asset.asset_type != AssetType.AUDIO:
    raise HTTPException(
        status_code=400,
        detail=f"Asset {request.audio_id} is not an audio file"
    )
```

3. Locate the TODO at approximately line 140. Replace with:
```python
# Get actual file paths from database
video_path = video_asset.file_path
audio_path = audio_asset.file_path

# Validate files exist on disk
if not os.path.exists(video_path):
    raise HTTPException(
        status_code=500,
        detail=f"Video file not found at expected path. Asset may need regeneration."
    )
if not os.path.exists(audio_path):
    raise HTTPException(
        status_code=500,
        detail=f"Audio file not found at expected path. Asset may need regeneration."
    )
```

4. Add required imports at top of file:
```python
import os
from scenemachine.models import Asset, AssetType
from sqlalchemy import select
```

5. Add proper error handling wrapper around the lip sync service call:
```python
try:
    result = await lipsync_service.process(
        video_path=video_path,
        audio_path=audio_path,
        provider=request.provider or "rhubarb"
    )
except LipsyncError as e:
    raise HTTPException(
        status_code=500,
        detail=f"Lip sync processing failed: {str(e)}"
    )
```

**Acceptance Criteria**:
- [ ] POST /api/v1/lipsync/process returns 404 if video_id does not exist
- [ ] POST /api/v1/lipsync/process returns 404 if audio_id does not exist
- [ ] POST /api/v1/lipsync/process returns 400 if video_id is not a video asset
- [ ] POST /api/v1/lipsync/process returns 400 if audio_id is not an audio asset
- [ ] POST /api/v1/lipsync/process returns 500 with helpful message if file missing from disk
- [ ] POST /api/v1/lipsync/process successfully processes valid video and audio assets
- [ ] Resulting video has synced mouth movements matching audio

**Backend Requirements**:
- Asset model must have `file_path` field (verify exists)
- Asset model must have `asset_type` enum including VIDEO and AUDIO
- LipsyncError exception class must exist (create if not)

**Testing Requirements**:

Unit Tests (file: `packages/core/tests/api/routes/test_lipsync.py`):
```python
async def test_lipsync_process_video_not_found():
    """POST /lipsync/process returns 404 for missing video_id"""
    response = await client.post("/api/v1/lipsync/process", json={
        "video_id": "nonexistent-uuid",
        "audio_id": "valid-audio-uuid"
    })
    assert response.status_code == 404
    assert "video asset" in response.json()["detail"].lower()

async def test_lipsync_process_audio_not_found():
    """POST /lipsync/process returns 404 for missing audio_id"""
    # Create a valid video asset first
    response = await client.post("/api/v1/lipsync/process", json={
        "video_id": "valid-video-uuid",
        "audio_id": "nonexistent-uuid"
    })
    assert response.status_code == 404
    assert "audio asset" in response.json()["detail"].lower()

async def test_lipsync_process_wrong_asset_type():
    """POST /lipsync/process returns 400 if video_id points to audio"""
    # Create an audio asset and try to use as video
    response = await client.post("/api/v1/lipsync/process", json={
        "video_id": "audio-asset-uuid",  # This is actually an audio asset
        "audio_id": "valid-audio-uuid"
    })
    assert response.status_code == 400
    assert "not a video" in response.json()["detail"].lower()

async def test_lipsync_process_success():
    """POST /lipsync/process successfully syncs valid assets"""
    # Create valid video and audio assets
    response = await client.post("/api/v1/lipsync/process", json={
        "video_id": "valid-video-uuid",
        "audio_id": "valid-audio-uuid",
        "provider": "mock"
    })
    assert response.status_code == 200
    assert "output_path" in response.json()
```

**Observability Requirements**:
- Log at INFO level when lip sync job starts: `"Starting lip sync for video={video_id} audio={audio_id}"`
- Log at INFO level when lip sync completes: `"Lip sync complete for video={video_id}, duration={duration}ms"`
- Log at ERROR level on failure: `"Lip sync failed for video={video_id}: {error}"`

**Risks and Mitigations**:
| Risk | Impact | Mitigation |
|------|--------|------------|
| Asset file_path field missing | High | Check model first, add migration if needed |
| Files on disk have been moved/deleted | Medium | Clear error message guiding user to regenerate |
| Lip sync provider timeout | Medium | Add timeout and retry logic |

---

#### Task 1.1.2: Add Lip Sync Job Status Endpoint

**Goal**: Allow frontend to poll for lip sync job progress and completion.

**Scope**:
- INCLUDED: GET endpoint for lip sync job status
- INCLUDED: Job progress percentage
- INCLUDED: Job completion with output path
- EXCLUDED: WebSocket real-time updates (future enhancement)

**Dependencies**:
- Task 1.1.1 must be complete
- LipsyncJob model must exist or be created

**Prerequisites**:
- Understand how GenerationJob tracks status (use as pattern)

**Implementation Steps**:

1. If LipsyncJob model doesn't exist, create it in `packages/core/scenemachine/models/lipsync.py`:
```python
from enum import Enum
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel
import uuid
from datetime import datetime

class LipsyncJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class LipsyncJob(BaseModel):
    __tablename__ = "lipsync_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shot_id = Column(UUID(as_uuid=True), ForeignKey("shots.id"), nullable=False)
    video_asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    audio_asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    output_asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    status = Column(SQLEnum(LipsyncJobStatus), default=LipsyncJobStatus.PENDING)
    progress = Column(Float, default=0.0)
    error_message = Column(String, nullable=True)
    provider = Column(String, default="rhubarb")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
```

2. Add GET endpoint to `packages/core/scenemachine/api/routes/lipsync.py`:
```python
@router.get("/jobs/{job_id}", response_model=LipsyncJobResponse)
async def get_lipsync_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get lip sync job status and progress."""
    job = await db.execute(
        select(LipsyncJob).where(LipsyncJob.id == job_id)
    )
    job = job.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Lip sync job {job_id} not found"
        )

    return LipsyncJobResponse(
        id=job.id,
        status=job.status,
        progress=job.progress,
        output_asset_id=job.output_asset_id,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at
    )
```

3. Create response schema:
```python
class LipsyncJobResponse(BaseModel):
    id: UUID
    status: LipsyncJobStatus
    progress: float  # 0.0 to 1.0
    output_asset_id: Optional[UUID]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
```

4. Modify the POST /process endpoint to create a job and return job_id for async processing:
```python
@router.post("/process", response_model=LipsyncJobCreatedResponse)
async def create_lipsync_job(
    request: LipsyncProcessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a lip sync job for async processing."""
    # ... validation from Task 1.1.1 ...

    # Create job record
    job = LipsyncJob(
        shot_id=request.shot_id,
        video_asset_id=request.video_id,
        audio_asset_id=request.audio_id,
        provider=request.provider or "rhubarb",
        status=LipsyncJobStatus.PENDING
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Start background processing
    background_tasks.add_task(
        process_lipsync_job,
        job_id=job.id,
        video_path=video_path,
        audio_path=audio_path,
        provider=request.provider or "rhubarb"
    )

    return LipsyncJobCreatedResponse(
        job_id=job.id,
        status=job.status,
        message="Lip sync job created. Poll GET /jobs/{job_id} for status."
    )
```

**Acceptance Criteria**:
- [ ] POST /lipsync/process returns job_id immediately (< 500ms)
- [ ] GET /lipsync/jobs/{job_id} returns current status
- [ ] Status transitions: pending → processing → completed/failed
- [ ] Progress updates from 0.0 to 1.0 during processing
- [ ] Completed jobs include output_asset_id
- [ ] Failed jobs include error_message

**Testing Requirements**:
```python
async def test_lipsync_job_lifecycle():
    """Test complete lip sync job lifecycle"""
    # Create job
    response = await client.post("/api/v1/lipsync/process", json={...})
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Poll until complete (with timeout)
    for _ in range(30):
        status_response = await client.get(f"/api/v1/lipsync/jobs/{job_id}")
        if status_response.json()["status"] == "completed":
            break
        await asyncio.sleep(1)

    assert status_response.json()["status"] == "completed"
    assert status_response.json()["output_asset_id"] is not None
```

---

#### Task 1.1.3: Create Frontend Lip Sync Integration

**Goal**: Add UI to trigger and monitor lip sync from the timeline or generation page.

**Scope**:
- INCLUDED: "Apply Lip Sync" button on shots with both video and audio
- INCLUDED: Progress indicator during processing
- INCLUDED: Success/error feedback
- EXCLUDED: Lip sync provider selection (use default)
- EXCLUDED: Preview before applying

**Dependencies**:
- Task 1.1.1 and 1.1.2 must be complete
- Shot must have video_asset_id and audio_asset_id

**Prerequisites**:
- Understand the lipsync-store in `apps/desktop/src/renderer/stores/lipsync-store.ts`

**Implementation Steps**:

1. Update `apps/desktop/src/renderer/stores/lipsync-store.ts`:
```typescript
interface LipsyncJob {
  id: string;
  shotId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  errorMessage?: string;
  outputAssetId?: string;
}

interface LipsyncStore {
  jobs: Record<string, LipsyncJob>;
  activeJobIds: string[];

  // Actions
  startLipsync: (shotId: string, videoAssetId: string, audioAssetId: string) => Promise<string>;
  pollJobStatus: (jobId: string) => Promise<void>;
  cancelJob: (jobId: string) => Promise<void>;
}

export const useLipsyncStore = create<LipsyncStore>((set, get) => ({
  jobs: {},
  activeJobIds: [],

  startLipsync: async (shotId, videoAssetId, audioAssetId) => {
    try {
      const result = await window.electronAPI.backendRequest<{
        job_id: string;
        status: string;
      }>('lipsync.process', {
        shot_id: shotId,
        video_id: videoAssetId,
        audio_id: audioAssetId,
      });

      set((state) => ({
        jobs: {
          ...state.jobs,
          [result.job_id]: {
            id: result.job_id,
            shotId,
            status: 'pending',
            progress: 0,
          },
        },
        activeJobIds: [...state.activeJobIds, result.job_id],
      }));

      // Start polling
      get().pollJobStatus(result.job_id);

      return result.job_id;
    } catch (error) {
      throw new Error(`Failed to start lip sync: ${error.message}`);
    }
  },

  pollJobStatus: async (jobId) => {
    const poll = async () => {
      try {
        const status = await window.electronAPI.backendRequest<LipsyncJob>(
          'lipsync.getJob',
          { job_id: jobId }
        );

        set((state) => ({
          jobs: {
            ...state.jobs,
            [jobId]: status,
          },
        }));

        if (status.status === 'pending' || status.status === 'processing') {
          setTimeout(poll, 1000); // Poll every second
        } else {
          // Remove from active jobs
          set((state) => ({
            activeJobIds: state.activeJobIds.filter((id) => id !== jobId),
          }));
        }
      } catch (error) {
        console.error('Failed to poll lip sync status:', error);
      }
    };

    poll();
  },
}));
```

2. Create `apps/desktop/src/renderer/components/lipsync/LipsyncButton.tsx`:
```typescript
import React from 'react';
import { Mic, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { useLipsyncStore } from '../../stores/lipsync-store';
import { useToast } from '../toast';
import { announce } from '../../lib/accessibility';
import { cn } from '../../lib/utils';

interface LipsyncButtonProps {
  shotId: string;
  videoAssetId: string | null;
  audioAssetId: string | null;
  className?: string;
}

export function LipsyncButton({
  shotId,
  videoAssetId,
  audioAssetId,
  className,
}: LipsyncButtonProps) {
  const { jobs, startLipsync } = useLipsyncStore();
  const { addToast } = useToast();

  // Find job for this shot
  const job = Object.values(jobs).find((j) => j.shotId === shotId);
  const isProcessing = job?.status === 'pending' || job?.status === 'processing';
  const isCompleted = job?.status === 'completed';
  const isFailed = job?.status === 'failed';

  // Determine if button should be enabled
  const canApplyLipsync = videoAssetId && audioAssetId && !isProcessing;

  const handleClick = async () => {
    if (!canApplyLipsync) return;

    try {
      announce('Starting lip sync');
      await startLipsync(shotId, videoAssetId!, audioAssetId!);
      addToast({
        type: 'info',
        title: 'Lip Sync Started',
        message: 'Processing lip sync for this shot...',
      });
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Lip Sync Failed',
        message: error.message,
      });
      announce('Lip sync failed');
    }
  };

  // Determine button state and content
  let icon = <Mic className="w-4 h-4" />;
  let label = 'Apply Lip Sync';
  let disabled = !canApplyLipsync;

  if (isProcessing) {
    icon = <Loader2 className="w-4 h-4 animate-spin" />;
    label = `Syncing ${Math.round((job?.progress || 0) * 100)}%`;
    disabled = true;
  } else if (isCompleted) {
    icon = <CheckCircle className="w-4 h-4 text-green-400" />;
    label = 'Lip Sync Applied';
  } else if (isFailed) {
    icon = <XCircle className="w-4 h-4 text-red-400" />;
    label = 'Retry Lip Sync';
    disabled = false;
  } else if (!videoAssetId) {
    label = 'No Video';
  } else if (!audioAssetId) {
    label = 'No Audio';
  }

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      className={cn(
        'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm',
        'transition-colors',
        disabled
          ? 'bg-surface-800 text-surface-500 cursor-not-allowed'
          : 'bg-brand-500/20 text-brand-400 hover:bg-brand-500/30',
        isCompleted && 'bg-green-500/20 text-green-400',
        isFailed && 'bg-red-500/20 text-red-400 hover:bg-red-500/30',
        className
      )}
      title={
        !videoAssetId
          ? 'Generate video first'
          : !audioAssetId
            ? 'Generate audio first'
            : 'Apply lip sync to match audio'
      }
      aria-label={label}
      aria-busy={isProcessing}
    >
      {icon}
      <span>{label}</span>
      {isProcessing && job && (
        <div className="w-16 h-1 bg-surface-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-400 transition-all"
            style={{ width: `${job.progress * 100}%` }}
          />
        </div>
      )}
    </button>
  );
}
```

3. Add the LipsyncButton to shot cards in the generation page. Edit `apps/desktop/src/renderer/pages/generation.tsx`, find the shot card component and add:
```typescript
// Inside the shot card, after the approve/reject buttons
<LipsyncButton
  shotId={shot.id}
  videoAssetId={shot.videoAssetId}
  audioAssetId={shot.audioAssetId}
/>
```

4. Add IPC handler in `packages/core/scenemachine/ipc/handlers.py`:
```python
@ipc_handler("lipsync.process")
async def handle_lipsync_process(params: dict, db: AsyncSession):
    """Create a lip sync job."""
    from scenemachine.api.routes.lipsync import create_lipsync_job
    # ... call the route handler logic

@ipc_handler("lipsync.getJob")
async def handle_lipsync_get_job(params: dict, db: AsyncSession):
    """Get lip sync job status."""
    from scenemachine.api.routes.lipsync import get_lipsync_job
    # ... call the route handler logic
```

**UI/UX Requirements**:

| State | Visual | Interaction |
|-------|--------|-------------|
| No video asset | Button grayed out, "No Video" text | Tooltip: "Generate video first" |
| No audio asset | Button grayed out, "No Audio" text | Tooltip: "Generate audio first" |
| Ready | Blue button, "Apply Lip Sync" | Click to start |
| Processing | Spinning loader, progress bar, percentage | Non-interactive |
| Completed | Green checkmark, "Lip Sync Applied" | Click to re-apply |
| Failed | Red X, "Retry Lip Sync" | Click to retry |

**Accessibility Requirements**:
- [ ] Button has aria-label describing current state
- [ ] aria-busy="true" during processing
- [ ] Screen reader announcement when processing starts
- [ ] Screen reader announcement when processing completes or fails
- [ ] Focus visible on button

**Acceptance Criteria**:
- [ ] Button appears on shots that have video assets
- [ ] Button disabled until audio is also present
- [ ] Click triggers lip sync job creation
- [ ] Progress bar updates in real-time
- [ ] Success toast shown on completion
- [ ] Error toast shown on failure with retry option
- [ ] Completed status persists across page navigation

**Testing Requirements**:

E2E Test (file: `apps/desktop/e2e/lipsync.spec.ts`):
```typescript
test('lip sync workflow', async ({ page }) => {
  // Navigate to a project with generated video and audio
  await page.goto('/project/test-project-id');
  await page.click('text=Generation');

  // Find a shot with both video and audio
  const shotCard = page.locator('[data-testid="shot-card"]').first();

  // Click lip sync button
  await shotCard.locator('button:has-text("Apply Lip Sync")').click();

  // Verify processing state
  await expect(shotCard.locator('text=Syncing')).toBeVisible();

  // Wait for completion (mock should be fast)
  await expect(shotCard.locator('text=Lip Sync Applied')).toBeVisible({ timeout: 10000 });

  // Verify toast
  await expect(page.locator('text=Lip Sync Complete')).toBeVisible();
});
```

---

### Epic 1.2: Audio Workflow Surfacing

**Goal**: Make the existing audio functionality discoverable and usable
**Current UX Score**: 5-6/10 → Target: 9/10
**Owner**: Frontend Engineer

---

#### Task 1.2.1: Add "Generate Dialogue" Button to Scene Planning

**Goal**: Allow users to generate TTS audio for all dialogue in a scene with one click.

**Scope**:
- INCLUDED: "Generate Dialogue" button on scene cards
- INCLUDED: Progress indicator during generation
- INCLUDED: Individual shot audio status indicators
- EXCLUDED: Voice selection (uses character's assigned voice)
- EXCLUDED: Per-word timing control

**Dependencies**:
- Characters must have assigned voices
- Scene must have shots with dialogue

**Prerequisites**:
- Understand the audio store in `apps/desktop/src/renderer/stores/audio-store.ts`
- Understand TTS API in `packages/core/scenemachine/api/routes/audio.py`

**Implementation Steps**:

1. Create `apps/desktop/src/renderer/components/audio/GenerateDialogueButton.tsx`:
```typescript
import React, { useState } from 'react';
import { Volume2, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { useToast } from '../toast';
import { announce } from '../../lib/accessibility';
import { cn } from '../../lib/utils';

interface DialogueShot {
  id: string;
  dialogue: string;
  characterId: string;
  hasAudio: boolean;
}

interface GenerateDialogueButtonProps {
  sceneId: string;
  shots: DialogueShot[];
  onComplete?: () => void;
  className?: string;
}

export function GenerateDialogueButton({
  sceneId,
  shots,
  onComplete,
  className,
}: GenerateDialogueButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const { addToast } = useToast();

  // Filter to shots with dialogue that don't have audio yet
  const shotsNeedingAudio = shots.filter((s) => s.dialogue && !s.hasAudio);
  const allHaveAudio = shotsNeedingAudio.length === 0;
  const dialogueShots = shots.filter((s) => s.dialogue);

  if (dialogueShots.length === 0) {
    return null; // No dialogue in this scene
  }

  const handleGenerate = async () => {
    if (isGenerating || allHaveAudio) return;

    setIsGenerating(true);
    setProgress({ current: 0, total: shotsNeedingAudio.length });
    announce(`Generating audio for ${shotsNeedingAudio.length} shots`);

    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < shotsNeedingAudio.length; i++) {
      const shot = shotsNeedingAudio[i];
      setProgress({ current: i + 1, total: shotsNeedingAudio.length });

      try {
        await window.electronAPI.backendRequest('audio.generateDialogue', {
          shot_id: shot.id,
          text: shot.dialogue,
          character_id: shot.characterId,
        });
        successCount++;
      } catch (error) {
        console.error(`Failed to generate audio for shot ${shot.id}:`, error);
        failCount++;
      }
    }

    setIsGenerating(false);

    if (failCount === 0) {
      addToast({
        type: 'success',
        title: 'Dialogue Generated',
        message: `Generated audio for ${successCount} shots`,
      });
      announce('All dialogue audio generated successfully');
    } else {
      addToast({
        type: 'warning',
        title: 'Partial Success',
        message: `Generated ${successCount} of ${shotsNeedingAudio.length} shots. ${failCount} failed.`,
      });
      announce(`Generated ${successCount} shots, ${failCount} failed`);
    }

    onComplete?.();
  };

  return (
    <button
      onClick={handleGenerate}
      disabled={isGenerating || allHaveAudio}
      className={cn(
        'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
        'transition-colors',
        allHaveAudio
          ? 'bg-green-500/20 text-green-400'
          : isGenerating
            ? 'bg-surface-700 text-surface-300'
            : 'bg-brand-500 hover:bg-brand-600 text-white',
        className
      )}
      aria-busy={isGenerating}
      aria-label={
        allHaveAudio
          ? 'All dialogue has audio'
          : `Generate audio for ${shotsNeedingAudio.length} shots`
      }
    >
      {isGenerating ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>
            Generating {progress.current}/{progress.total}...
          </span>
        </>
      ) : allHaveAudio ? (
        <>
          <CheckCircle className="w-4 h-4" />
          <span>All Dialogue Ready</span>
        </>
      ) : (
        <>
          <Volume2 className="w-4 h-4" />
          <span>Generate Dialogue ({shotsNeedingAudio.length})</span>
        </>
      )}
    </button>
  );
}
```

2. Add the button to scene cards in `apps/desktop/src/renderer/pages/scene-planning.tsx`:
```typescript
// Inside each scene card, after the shot list
<div className="mt-4 pt-4 border-t border-surface-700 flex justify-between items-center">
  <GenerateDialogueButton
    sceneId={scene.id}
    shots={scene.shots.map((s) => ({
      id: s.id,
      dialogue: s.dialogue,
      characterId: s.characterId,
      hasAudio: !!s.audioAssetId,
    }))}
    onComplete={() => refetchScenes()}
  />
  <span className="text-sm text-surface-400">
    {scene.shots.filter((s) => s.audioAssetId).length}/{scene.shots.filter((s) => s.dialogue).length} dialogue ready
  </span>
</div>
```

3. Add audio status indicator to individual shot cards:
```typescript
// In the shot card component
{shot.dialogue && (
  <div className="flex items-center gap-2 mt-2">
    {shot.audioAssetId ? (
      <div className="flex items-center gap-1 text-green-400 text-xs">
        <Volume2 className="w-3 h-3" />
        <span>Audio ready</span>
      </div>
    ) : (
      <div className="flex items-center gap-1 text-surface-500 text-xs">
        <Volume2 className="w-3 h-3" />
        <span>No audio</span>
      </div>
    )}
  </div>
)}
```

4. Add IPC handler for dialogue generation:
```python
@ipc_handler("audio.generateDialogue")
async def handle_generate_dialogue(params: dict, db: AsyncSession):
    """Generate TTS audio for a shot's dialogue."""
    shot_id = params["shot_id"]
    text = params["text"]
    character_id = params["character_id"]

    # Get character's voice settings
    character = await db.get(Character, character_id)
    if not character or not character.voice_id:
        raise ValueError(f"Character {character_id} has no voice assigned")

    # Generate audio
    audio_service = AudioService()
    result = await audio_service.generate_speech(
        text=text,
        voice_id=character.voice_id,
        provider=character.voice_provider or "elevenlabs",
    )

    # Create asset record
    asset = Asset(
        project_id=character.project_id,
        asset_type=AssetType.AUDIO,
        file_path=result.file_path,
        duration_seconds=result.duration,
    )
    db.add(asset)

    # Update shot with audio asset
    shot = await db.get(Shot, shot_id)
    shot.audio_asset_id = asset.id

    await db.commit()

    return {"asset_id": str(asset.id), "duration": result.duration}
```

**UI/UX Requirements**:

| State | Button Text | Icon | Color |
|-------|-------------|------|-------|
| Has shots needing audio | "Generate Dialogue (N)" | Volume2 | Blue/brand |
| Generating | "Generating X/Y..." | Loader spinning | Gray |
| All complete | "All Dialogue Ready" | CheckCircle | Green |
| Scene has no dialogue | (Button hidden) | - | - |

**Acceptance Criteria**:
- [ ] Button appears on scenes that have shots with dialogue
- [ ] Button shows count of shots needing audio
- [ ] Click generates audio for all shots without audio
- [ ] Progress updates during generation
- [ ] Shot cards show audio status indicator
- [ ] Counter updates after generation
- [ ] Button changes to green "All Dialogue Ready" when complete
- [ ] Failed shots show error and can be retried

**Testing Requirements**:
```typescript
test('generate dialogue for scene', async ({ page }) => {
  await page.goto('/project/test-id');
  await page.click('text=Scenes');

  // Find scene with dialogue
  const sceneCard = page.locator('[data-testid="scene-card"]').first();

  // Click generate dialogue
  await sceneCard.locator('button:has-text("Generate Dialogue")').click();

  // Wait for completion
  await expect(sceneCard.locator('text=All Dialogue Ready')).toBeVisible({ timeout: 30000 });
});
```

---

#### Task 1.2.2: Add Audio Track Mixer to Timeline

**Goal**: Allow users to adjust volume levels for voice, music, and SFX tracks in the timeline.

**Scope**:
- INCLUDED: Volume sliders for each audio track type
- INCLUDED: Mute/solo buttons per track
- INCLUDED: Master volume control
- INCLUDED: Real-time preview of audio changes
- EXCLUDED: Per-clip volume automation
- EXCLUDED: Audio waveform editing

**Dependencies**:
- Timeline must already show audio tracks
- Assembly service must support track-level mixing

**Prerequisites**:
- Understand timeline state in `apps/desktop/src/renderer/pages/timeline.tsx`
- Understand assembly service audio handling

**Implementation Steps**:

1. Create `apps/desktop/src/renderer/components/timeline/AudioMixer.tsx`:
```typescript
import React from 'react';
import { Volume2, VolumeX, Headphones } from 'lucide-react';
import { cn } from '../../lib/utils';

interface AudioTrack {
  id: string;
  name: string;
  type: 'voice' | 'music' | 'sfx' | 'master';
  volume: number; // 0-100
  muted: boolean;
  solo: boolean;
}

interface AudioMixerProps {
  tracks: AudioTrack[];
  onVolumeChange: (trackId: string, volume: number) => void;
  onMuteToggle: (trackId: string) => void;
  onSoloToggle: (trackId: string) => void;
  className?: string;
}

export function AudioMixer({
  tracks,
  onVolumeChange,
  onMuteToggle,
  onSoloToggle,
  className,
}: AudioMixerProps) {
  return (
    <div className={cn('bg-surface-900 border-t border-surface-700 p-4', className)}>
      <div className="flex items-center gap-2 mb-4">
        <Volume2 className="w-5 h-5 text-brand-400" />
        <h3 className="text-sm font-medium">Audio Mixer</h3>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {tracks.map((track) => (
          <div
            key={track.id}
            className="flex flex-col items-center gap-2 p-3 bg-surface-800 rounded-lg"
          >
            <span className="text-xs text-surface-400 uppercase tracking-wide">
              {track.name}
            </span>

            {/* Vertical volume slider */}
            <div className="relative h-24 w-2 bg-surface-700 rounded-full">
              <div
                className={cn(
                  'absolute bottom-0 w-full rounded-full transition-all',
                  track.muted ? 'bg-surface-600' : 'bg-brand-500'
                )}
                style={{ height: `${track.volume}%` }}
              />
              <input
                type="range"
                min="0"
                max="100"
                value={track.volume}
                onChange={(e) => onVolumeChange(track.id, parseInt(e.target.value))}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                style={{ writingMode: 'vertical-lr', direction: 'rtl' }}
                aria-label={`${track.name} volume`}
              />
            </div>

            {/* Volume value */}
            <span className={cn(
              'text-xs font-mono',
              track.muted ? 'text-surface-500' : 'text-surface-300'
            )}>
              {track.muted ? '--' : `${track.volume}%`}
            </span>

            {/* Mute/Solo buttons */}
            <div className="flex gap-1">
              <button
                onClick={() => onMuteToggle(track.id)}
                className={cn(
                  'p-1.5 rounded',
                  track.muted
                    ? 'bg-red-500/20 text-red-400'
                    : 'bg-surface-700 text-surface-400 hover:text-surface-200'
                )}
                aria-label={track.muted ? `Unmute ${track.name}` : `Mute ${track.name}`}
                aria-pressed={track.muted}
              >
                {track.muted ? (
                  <VolumeX className="w-4 h-4" />
                ) : (
                  <Volume2 className="w-4 h-4" />
                )}
              </button>

              {track.type !== 'master' && (
                <button
                  onClick={() => onSoloToggle(track.id)}
                  className={cn(
                    'p-1.5 rounded',
                    track.solo
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-surface-700 text-surface-400 hover:text-surface-200'
                  )}
                  aria-label={track.solo ? `Unsolo ${track.name}` : `Solo ${track.name}`}
                  aria-pressed={track.solo}
                >
                  <Headphones className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

2. Add mixer state to timeline page. In `apps/desktop/src/renderer/pages/timeline.tsx`:
```typescript
// Add state for audio mixer
const [audioTracks, setAudioTracks] = useState<AudioTrack[]>([
  { id: 'voice', name: 'Voice', type: 'voice', volume: 100, muted: false, solo: false },
  { id: 'music', name: 'Music', type: 'music', volume: 80, muted: false, solo: false },
  { id: 'sfx', name: 'SFX', type: 'sfx', volume: 100, muted: false, solo: false },
  { id: 'master', name: 'Master', type: 'master', volume: 100, muted: false, solo: false },
]);

const handleVolumeChange = useCallback((trackId: string, volume: number) => {
  setAudioTracks((prev) =>
    prev.map((t) => (t.id === trackId ? { ...t, volume } : t))
  );
  // Debounced save
  debouncedSaveMixerSettings();
}, []);

const handleMuteToggle = useCallback((trackId: string) => {
  setAudioTracks((prev) =>
    prev.map((t) => (t.id === trackId ? { ...t, muted: !t.muted } : t))
  );
  announce(`${trackId} ${audioTracks.find((t) => t.id === trackId)?.muted ? 'unmuted' : 'muted'}`);
}, [audioTracks]);

const handleSoloToggle = useCallback((trackId: string) => {
  setAudioTracks((prev) =>
    prev.map((t) => (t.id === trackId ? { ...t, solo: !t.solo } : t))
  );
}, []);
```

3. Add the mixer component below the timeline:
```typescript
// At the bottom of the timeline page
<AudioMixer
  tracks={audioTracks}
  onVolumeChange={handleVolumeChange}
  onMuteToggle={handleMuteToggle}
  onSoloToggle={handleSoloToggle}
/>
```

4. Pass mixer settings to export. Update assembly store:
```typescript
interface AssemblySettings {
  // ... existing fields
  audioMix: {
    voiceVolume: number;
    musicVolume: number;
    sfxVolume: number;
    masterVolume: number;
  };
}
```

5. Update assembly service to respect mixer settings:
```python
async def assemble_movie(
    project_id: str,
    clips: List[ClipInfo],
    audio_mix: AudioMixSettings,
) -> str:
    """Assemble movie with audio mixing."""
    # Build ffmpeg filter for audio mixing
    audio_filter = (
        f"[voice]volume={audio_mix.voice_volume/100}[v];"
        f"[music]volume={audio_mix.music_volume/100}[m];"
        f"[sfx]volume={audio_mix.sfx_volume/100}[s];"
        f"[v][m][s]amix=inputs=3[mixed];"
        f"[mixed]volume={audio_mix.master_volume/100}[out]"
    )
    # ... apply to ffmpeg command
```

**UI/UX Requirements**:
- Mixer panel is collapsible (default expanded)
- Vertical sliders match professional DAW conventions
- Color coding: Voice (blue), Music (purple), SFX (orange), Master (white)
- Mute shows red indicator
- Solo shows yellow indicator
- Changes are saved automatically with debounce

**Accessibility Requirements**:
- [ ] All sliders have aria-labels
- [ ] Mute/Solo buttons have aria-pressed
- [ ] Keyboard: Up/Down arrows adjust selected slider by 5%
- [ ] Screen reader announces changes

**Acceptance Criteria**:
- [ ] Mixer shows 4 tracks: Voice, Music, SFX, Master
- [ ] Volume sliders range 0-100
- [ ] Muting a track silences it in preview
- [ ] Soloing a track mutes all others
- [ ] Master volume affects all tracks
- [ ] Settings persist across sessions
- [ ] Settings passed to export/assembly

**Testing Requirements**:
```typescript
test('audio mixer controls', async ({ page }) => {
  await page.goto('/project/test-id');
  await page.click('text=Timeline');

  // Verify mixer visible
  await expect(page.locator('text=Audio Mixer')).toBeVisible();

  // Adjust voice volume
  const voiceSlider = page.locator('[aria-label="Voice volume"]');
  await voiceSlider.fill('50');

  // Mute music
  await page.click('[aria-label="Mute Music"]');
  await expect(page.locator('[aria-pressed="true"][aria-label*="Music"]')).toBeVisible();

  // Solo SFX
  await page.click('[aria-label="Solo SFX"]');
});
```

---

#### Task 1.2.3: Enable Drag-and-Drop Audio from Library to Timeline

**Goal**: Allow users to drag music/SFX from the audio library onto timeline tracks.

**Scope**:
- INCLUDED: Drag audio items from library panel
- INCLUDED: Drop onto Music or SFX timeline tracks
- INCLUDED: Visual drop zone indicators
- INCLUDED: Automatic clip creation on drop
- EXCLUDED: Audio trimming during drop (done after)
- EXCLUDED: Cross-fade between audio clips

**Dependencies**:
- Task 1.2.2 (Audio Mixer) must be complete
- Audio library must be populated

**Prerequisites**:
- Understand react-dnd or native HTML5 drag-drop
- Understand timeline clip data structure

**Implementation Steps**:

1. Add drag source to audio library items. Create `apps/desktop/src/renderer/components/audio/DraggableAudioItem.tsx`:
```typescript
import React from 'react';
import { useDrag } from 'react-dnd';
import { Music, Volume2 } from 'lucide-react';
import { cn } from '../../lib/utils';

interface AudioItem {
  id: string;
  name: string;
  type: 'music' | 'sfx';
  duration: number;
  previewUrl?: string;
}

interface DraggableAudioItemProps {
  item: AudioItem;
}

export const AUDIO_ITEM_TYPE = 'AUDIO_ITEM';

export function DraggableAudioItem({ item }: DraggableAudioItemProps) {
  const [{ isDragging }, drag] = useDrag({
    type: AUDIO_ITEM_TYPE,
    item: { ...item },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  return (
    <div
      ref={drag}
      className={cn(
        'flex items-center gap-3 p-3 bg-surface-800 rounded-lg cursor-grab',
        'hover:bg-surface-700 transition-colors',
        isDragging && 'opacity-50 cursor-grabbing'
      )}
      role="listitem"
      aria-grabbed={isDragging}
    >
      {item.type === 'music' ? (
        <Music className="w-4 h-4 text-purple-400" />
      ) : (
        <Volume2 className="w-4 h-4 text-orange-400" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{item.name}</p>
        <p className="text-xs text-surface-400">
          {Math.floor(item.duration / 60)}:{String(Math.floor(item.duration % 60)).padStart(2, '0')}
        </p>
      </div>
    </div>
  );
}
```

2. Add drop zone to timeline tracks. In timeline component:
```typescript
import { useDrop } from 'react-dnd';
import { AUDIO_ITEM_TYPE } from '../components/audio/DraggableAudioItem';

function TimelineTrack({
  trackType,
  clips,
  onAddClip,
  playheadPosition
}: TimelineTrackProps) {
  const [{ isOver, canDrop }, drop] = useDrop({
    accept: AUDIO_ITEM_TYPE,
    canDrop: (item) => {
      // Only allow music on music track, sfx on sfx track
      if (trackType === 'music' && item.type === 'music') return true;
      if (trackType === 'sfx' && item.type === 'sfx') return true;
      return false;
    },
    drop: (item, monitor) => {
      // Calculate drop position based on mouse position
      const dropOffset = monitor.getClientOffset();
      const trackRect = trackRef.current?.getBoundingClientRect();
      if (!dropOffset || !trackRect) return;

      const relativeX = dropOffset.x - trackRect.left;
      const timePosition = (relativeX / trackRect.width) * totalDuration;

      onAddClip({
        audioId: item.id,
        startTime: timePosition,
        duration: item.duration,
        type: item.type,
        name: item.name,
      });

      announce(`Added ${item.name} to ${trackType} track`);
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  });

  return (
    <div
      ref={drop}
      className={cn(
        'relative h-16 bg-surface-800 rounded',
        isOver && canDrop && 'ring-2 ring-brand-500 bg-brand-500/10',
        isOver && !canDrop && 'ring-2 ring-red-500 bg-red-500/10'
      )}
      role="region"
      aria-label={`${trackType} track`}
      aria-dropeffect={canDrop ? 'copy' : 'none'}
    >
      {/* Track label */}
      <div className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-surface-400 uppercase">
        {trackType}
      </div>

      {/* Clips */}
      {clips.map((clip) => (
        <TimelineClip key={clip.id} clip={clip} />
      ))}

      {/* Drop indicator */}
      {isOver && canDrop && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="text-brand-400 text-sm">Drop to add</span>
        </div>
      )}
    </div>
  );
}
```

3. Add audio library panel to timeline page:
```typescript
// In timeline.tsx, add collapsible library panel
const [showAudioLibrary, setShowAudioLibrary] = useState(false);

// In render
<div className="flex h-full">
  {/* Main timeline area */}
  <div className="flex-1">
    {/* Timeline content */}
  </div>

  {/* Audio library sidebar */}
  {showAudioLibrary && (
    <div className="w-64 border-l border-surface-700 p-4 overflow-y-auto">
      <h3 className="text-sm font-medium mb-4">Audio Library</h3>

      <div className="space-y-2 mb-6">
        <h4 className="text-xs text-surface-400 uppercase">Music</h4>
        {musicItems.map((item) => (
          <DraggableAudioItem key={item.id} item={item} />
        ))}
      </div>

      <div className="space-y-2">
        <h4 className="text-xs text-surface-400 uppercase">Sound Effects</h4>
        {sfxItems.map((item) => (
          <DraggableAudioItem key={item.id} item={item} />
        ))}
      </div>
    </div>
  )}
</div>

{/* Toggle button */}
<button
  onClick={() => setShowAudioLibrary(!showAudioLibrary)}
  className="absolute right-4 top-4 p-2 bg-surface-700 rounded-lg"
  aria-expanded={showAudioLibrary}
>
  <Music className="w-5 h-5" />
</button>
```

4. Handle clip creation and save:
```typescript
const handleAddAudioClip = useCallback((clipData: AudioClipData) => {
  const newClip: TimelineClip = {
    id: crypto.randomUUID(),
    audioAssetId: clipData.audioId,
    trackType: clipData.type,
    startTime: clipData.startTime,
    duration: clipData.duration,
    name: clipData.name,
  };

  setClips((prev) => [...prev, newClip]);

  // Save to backend
  saveTimeline([...clips, newClip]);

  addToast({
    type: 'success',
    title: 'Audio Added',
    message: `Added "${clipData.name}" to timeline`,
  });
}, [clips, saveTimeline, addToast]);
```

**UI/UX Requirements**:
- Drag cursor changes to grabbing hand
- Drop zone highlights green when valid drop target
- Drop zone highlights red when invalid (wrong track type)
- New clip appears immediately at drop position
- Clips can be repositioned after dropping
- Library panel is collapsible to save space

**Accessibility Requirements**:
- [ ] Audio items have role="listitem" and aria-grabbed
- [ ] Tracks have aria-dropeffect
- [ ] Keyboard alternative: Select item, then keyboard shortcut to add at playhead
- [ ] Screen reader announces successful drops

**Acceptance Criteria**:
- [ ] Music items can only be dropped on music track
- [ ] SFX items can only be dropped on SFX track
- [ ] Drop creates new clip at mouse position
- [ ] Clip appears immediately on timeline
- [ ] Timeline auto-saves after drop
- [ ] Clips can be moved after dropping
- [ ] Library panel toggle works

**Testing Requirements**:
```typescript
test('drag audio to timeline', async ({ page }) => {
  await page.goto('/project/test-id');
  await page.click('text=Timeline');

  // Open audio library
  await page.click('[aria-label="Toggle audio library"]');

  // Drag music item to music track
  const musicItem = page.locator('[data-testid="audio-item-music"]').first();
  const musicTrack = page.locator('[aria-label="music track"]');

  await musicItem.dragTo(musicTrack);

  // Verify clip created
  await expect(musicTrack.locator('[data-testid="timeline-clip"]')).toHaveCount(1);
});
```

---

### Epic 1.3: LatentSync Implementation

**Goal**: Implement the advertised LatentSync lip sync provider
**Current UX Score**: 0/10 → Target: 9/10
**Owner**: Backend Engineer + ML Engineer

---

#### Task 1.3.1: Implement LatentSync Provider

**Goal**: Add LatentSync as a lip sync provider option.

**Scope**:
- INCLUDED: LatentSync model integration
- INCLUDED: Provider abstraction following existing pattern
- INCLUDED: Fallback to Wav2Lip on failure
- EXCLUDED: Training custom models
- EXCLUDED: Real-time processing

**Dependencies**:
- LatentSync model must be available (local or API)
- GPU with sufficient VRAM (12GB+ recommended)

**Prerequisites**:
- Understand existing lip sync providers in `packages/core/scenemachine/services/lipsync.py`
- Research LatentSync API/usage

**Implementation Steps**:

1. Create LatentSync provider class in `packages/core/scenemachine/services/lipsync_providers/latentsync.py`:
```python
"""LatentSync lip sync provider implementation."""

import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

from .base import LipsyncProvider, LipsyncResult, LipsyncError


@dataclass
class LatentSyncConfig:
    """Configuration for LatentSync provider."""
    model_path: str = "models/latentsync"
    device: str = "cuda"
    batch_size: int = 4
    quality: str = "high"  # "draft", "standard", "high"


class LatentSyncProvider(LipsyncProvider):
    """LatentSync lip sync provider for high-quality mouth animation."""

    name = "latentsync"

    def __init__(self, config: Optional[LatentSyncConfig] = None):
        self.config = config or LatentSyncConfig()
        self._model = None

    async def initialize(self) -> None:
        """Load LatentSync model into memory."""
        if self._model is not None:
            return

        try:
            # Import LatentSync (assumed to be installed)
            from latentsync import LatentSyncModel

            self._model = LatentSyncModel.load(
                self.config.model_path,
                device=self.config.device,
            )
        except ImportError:
            raise LipsyncError(
                "LatentSync not installed. Run: pip install latentsync"
            )
        except Exception as e:
            raise LipsyncError(f"Failed to load LatentSync model: {e}")

    async def process(
        self,
        video_path: str,
        audio_path: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> LipsyncResult:
        """
        Apply lip sync to video using LatentSync.

        Args:
            video_path: Path to input video file
            audio_path: Path to audio file to sync
            output_path: Path for output video (generated if None)
            progress_callback: Optional callback for progress updates

        Returns:
            LipsyncResult with output path and metadata
        """
        await self.initialize()

        if output_path is None:
            output_path = tempfile.mktemp(suffix=".mp4")

        try:
            # Report starting
            if progress_callback:
                progress_callback(0.0)

            # Run LatentSync inference
            result = await asyncio.to_thread(
                self._process_sync,
                video_path,
                audio_path,
                output_path,
                progress_callback,
            )

            if progress_callback:
                progress_callback(1.0)

            return LipsyncResult(
                success=True,
                output_path=output_path,
                provider="latentsync",
                metadata={
                    "quality": self.config.quality,
                    "device": self.config.device,
                },
            )

        except Exception as e:
            raise LipsyncError(f"LatentSync processing failed: {e}")

    def _process_sync(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]],
    ) -> None:
        """Synchronous processing (runs in thread pool)."""
        from latentsync import process_video

        def on_progress(current: int, total: int):
            if progress_callback:
                progress_callback(current / total)

        process_video(
            video_path=video_path,
            audio_path=audio_path,
            output_path=output_path,
            model=self._model,
            batch_size=self.config.batch_size,
            quality=self.config.quality,
            progress_callback=on_progress,
        )

    async def is_available(self) -> bool:
        """Check if LatentSync is available."""
        try:
            import latentsync
            return True
        except ImportError:
            return False

    @property
    def estimated_time_per_second(self) -> float:
        """Estimated processing time per second of video."""
        # LatentSync is slower but higher quality
        quality_times = {
            "draft": 2.0,
            "standard": 5.0,
            "high": 10.0,
        }
        return quality_times.get(self.config.quality, 5.0)
```

2. Register provider in the lipsync service. Update `packages/core/scenemachine/services/lipsync.py`:
```python
from .lipsync_providers.latentsync import LatentSyncProvider

PROVIDERS = {
    "rhubarb": RhubarbProvider,
    "wav2lip": Wav2LipProvider,
    "sadtalker": SadTalkerProvider,
    "latentsync": LatentSyncProvider,  # Add this
    "mock": MockProvider,
}

async def get_available_providers() -> List[str]:
    """Get list of available lip sync providers."""
    available = []
    for name, provider_class in PROVIDERS.items():
        provider = provider_class()
        if await provider.is_available():
            available.append(name)
    return available
```

3. Add provider selection to API. Update `packages/core/scenemachine/api/routes/lipsync.py`:
```python
@router.get("/providers")
async def list_lipsync_providers():
    """List available lip sync providers with capabilities."""
    providers = await get_available_providers()

    provider_info = {
        "rhubarb": {
            "name": "Rhubarb Lip Sync",
            "quality": "good",
            "speed": "fast",
            "description": "Open-source phoneme-based lip sync",
        },
        "wav2lip": {
            "name": "Wav2Lip",
            "quality": "excellent",
            "speed": "medium",
            "description": "AI-based lip sync with natural mouth movements",
        },
        "latentsync": {
            "name": "LatentSync",
            "quality": "best",
            "speed": "slow",
            "description": "State-of-the-art latent diffusion lip sync",
        },
        "sadtalker": {
            "name": "SadTalker",
            "quality": "excellent",
            "speed": "medium",
            "description": "Talking head generation with expressions",
        },
    }

    return {
        "available": providers,
        "info": {k: v for k, v in provider_info.items() if k in providers},
    }
```

4. Add fallback logic for when LatentSync fails:
```python
async def process_with_fallback(
    video_path: str,
    audio_path: str,
    preferred_provider: str = "latentsync",
) -> LipsyncResult:
    """Process lip sync with automatic fallback on failure."""
    providers_to_try = [preferred_provider, "wav2lip", "rhubarb"]

    for provider_name in providers_to_try:
        if provider_name not in PROVIDERS:
            continue

        provider = PROVIDERS[provider_name]()
        if not await provider.is_available():
            continue

        try:
            return await provider.process(video_path, audio_path)
        except LipsyncError as e:
            logger.warning(f"{provider_name} failed: {e}, trying fallback")
            continue

    raise LipsyncError("All lip sync providers failed")
```

**Acceptance Criteria**:
- [ ] LatentSync provider can be selected via API
- [ ] Provider processes video with audio successfully
- [ ] Progress callback updates during processing
- [ ] Falls back to Wav2Lip if LatentSync fails
- [ ] API lists LatentSync in available providers (when installed)
- [ ] Quality setting affects output (draft/standard/high)

**Testing Requirements**:
```python
async def test_latentsync_provider():
    """Test LatentSync lip sync processing."""
    provider = LatentSyncProvider()

    if not await provider.is_available():
        pytest.skip("LatentSync not installed")

    result = await provider.process(
        video_path="test_data/face_video.mp4",
        audio_path="test_data/speech.wav",
    )

    assert result.success
    assert Path(result.output_path).exists()
    assert result.provider == "latentsync"

async def test_lipsync_fallback():
    """Test automatic fallback when preferred provider fails."""
    # Mock LatentSync to fail
    with patch.object(LatentSyncProvider, 'process', side_effect=LipsyncError("Failed")):
        result = await process_with_fallback(
            video_path="test.mp4",
            audio_path="test.wav",
            preferred_provider="latentsync",
        )

    # Should fall back to wav2lip or rhubarb
    assert result.success
    assert result.provider in ["wav2lip", "rhubarb"]
```

**Observability Requirements**:
- Log provider selection: `"Using lip sync provider: {provider}"`
- Log fallback events: `"Provider {provider} failed, falling back to {fallback}"`
- Metric: `lipsync_processing_seconds{provider=latentsync}`
- Metric: `lipsync_fallback_count{from_provider=latentsync,to_provider=wav2lip}`

---

## Phase 2: High Impact

**Duration**: 2 weeks
**Goal**: Surface hidden functionality and improve UX 5-6 features to 9/10
**Priority**: Features that exist technically but fail experientially

---

### Epic 2.1: Local GPU Setup Wizard

**Goal**: Guide users through ComfyUI setup for local generation
**Current UX Score**: 6/10 → Target: 9/10

---

#### Task 2.1.1: Create ComfyUI Detection and Setup Component

**Goal**: Detect if ComfyUI is installed and guide installation if not.

**Scope**:
- INCLUDED: Detect ComfyUI installation
- INCLUDED: Check ComfyUI server status
- INCLUDED: Installation instructions with links
- INCLUDED: Connection test button
- EXCLUDED: Automatic installation
- EXCLUDED: Model downloading

**Implementation Steps**:

1. Create `apps/desktop/src/renderer/components/settings/LocalGpuSetup.tsx`:
```typescript
import React, { useState, useEffect } from 'react';
import { Cpu, Check, X, ExternalLink, RefreshCw, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useToast } from '../toast';
import { announce } from '../../lib/accessibility';

interface ComfyUIStatus {
  installed: boolean;
  running: boolean;
  version?: string;
  error?: string;
}

export function LocalGpuSetup() {
  const [status, setStatus] = useState<ComfyUIStatus | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const { addToast } = useToast();

  const checkStatus = async () => {
    setIsChecking(true);
    announce('Checking ComfyUI status');

    try {
      const result = await window.electronAPI.backendRequest<ComfyUIStatus>(
        'comfyui.checkStatus',
        {}
      );
      setStatus(result);

      if (result.running) {
        announce('ComfyUI is running');
      } else if (result.installed) {
        announce('ComfyUI is installed but not running');
      } else {
        announce('ComfyUI is not installed');
      }
    } catch (error) {
      setStatus({
        installed: false,
        running: false,
        error: error.message,
      });
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  const handleTestConnection = async () => {
    setIsChecking(true);

    try {
      const result = await window.electronAPI.backendRequest<{ success: boolean; latency: number }>(
        'comfyui.testConnection',
        {}
      );

      if (result.success) {
        addToast({
          type: 'success',
          title: 'Connection Successful',
          message: `ComfyUI responded in ${result.latency}ms`,
        });
      }
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Connection Failed',
        message: error.message,
      });
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium flex items-center gap-2">
          <Cpu className="w-5 h-5 text-brand-400" />
          Local GPU (ComfyUI)
        </h3>
        <button
          onClick={checkStatus}
          disabled={isChecking}
          className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
        >
          {isChecking ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Refresh
        </button>
      </div>

      {/* Status indicators */}
      <div className="space-y-3 mb-6">
        <StatusRow
          label="ComfyUI Installed"
          status={status?.installed}
          isLoading={isChecking && !status}
        />
        <StatusRow
          label="ComfyUI Running"
          status={status?.running}
          isLoading={isChecking && !status}
        />
        {status?.version && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-surface-400">Version</span>
            <span className="font-mono">{status.version}</span>
          </div>
        )}
      </div>

      {/* Actions based on status */}
      {status && !status.installed && (
        <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg mb-4">
          <h4 className="font-medium text-yellow-400 mb-2">Setup Required</h4>
          <p className="text-sm text-surface-300 mb-4">
            ComfyUI enables free local video generation using your GPU.
            Follow these steps to install:
          </p>
          <ol className="list-decimal list-inside text-sm text-surface-400 space-y-2 mb-4">
            <li>Install Python 3.10+ if not already installed</li>
            <li>Clone or download ComfyUI from GitHub</li>
            <li>Install requirements: <code className="bg-surface-800 px-1 rounded">pip install -r requirements.txt</code></li>
            <li>Start the server: <code className="bg-surface-800 px-1 rounded">python main.py</code></li>
          </ol>
          <a
            href="https://github.com/comfyanonymous/ComfyUI"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-brand-400 hover:text-brand-300 text-sm"
          >
            View Installation Guide
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      )}

      {status?.installed && !status.running && (
        <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg mb-4">
          <h4 className="font-medium text-blue-400 mb-2">Start ComfyUI</h4>
          <p className="text-sm text-surface-300 mb-2">
            ComfyUI is installed but not running. Start the server to enable local generation:
          </p>
          <code className="block bg-surface-800 px-3 py-2 rounded text-sm font-mono">
            cd /path/to/ComfyUI && python main.py
          </code>
        </div>
      )}

      {status?.running && (
        <button
          onClick={handleTestConnection}
          disabled={isChecking}
          className="btn-primary w-full"
        >
          Test Connection
        </button>
      )}

      {status?.error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
          {status.error}
        </div>
      )}
    </div>
  );
}

function StatusRow({
  label,
  status,
  isLoading,
}: {
  label: string;
  status?: boolean;
  isLoading: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-surface-400">{label}</span>
      {isLoading ? (
        <Loader2 className="w-4 h-4 text-surface-500 animate-spin" />
      ) : status === undefined ? (
        <span className="text-surface-500 text-sm">Unknown</span>
      ) : status ? (
        <div className="flex items-center gap-1 text-green-400">
          <Check className="w-4 h-4" />
          <span className="text-sm">Yes</span>
        </div>
      ) : (
        <div className="flex items-center gap-1 text-red-400">
          <X className="w-4 h-4" />
          <span className="text-sm">No</span>
        </div>
      )}
    </div>
  );
}
```

2. Add backend handler for ComfyUI status check:
```python
@ipc_handler("comfyui.checkStatus")
async def check_comfyui_status(params: dict, db: AsyncSession):
    """Check if ComfyUI is installed and running."""
    import aiohttp

    comfyui_url = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{comfyui_url}/system_stats", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "installed": True,
                        "running": True,
                        "version": data.get("system", {}).get("comfyui_version", "unknown"),
                    }
    except aiohttp.ClientConnectorError:
        # Server not running, but might be installed
        # Check for common installation paths
        common_paths = [
            Path.home() / "ComfyUI",
            Path("C:/ComfyUI"),
            Path("/opt/ComfyUI"),
        ]
        installed = any(p.exists() for p in common_paths)
        return {
            "installed": installed,
            "running": False,
        }
    except Exception as e:
        return {
            "installed": False,
            "running": False,
            "error": str(e),
        }

@ipc_handler("comfyui.testConnection")
async def test_comfyui_connection(params: dict, db: AsyncSession):
    """Test ComfyUI connection with latency measurement."""
    import aiohttp
    import time

    comfyui_url = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")

    start = time.time()
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{comfyui_url}/system_stats", timeout=10) as resp:
            if resp.status == 200:
                latency = (time.time() - start) * 1000
                return {"success": True, "latency": round(latency)}
            else:
                raise ValueError(f"Unexpected status: {resp.status}")
```

3. Add component to settings page:
```typescript
// In settings.tsx, add LocalGpuSetup in the Generation Settings section
<LocalGpuSetup />
```

**Acceptance Criteria**:
- [ ] Component detects if ComfyUI is installed
- [ ] Component shows if ComfyUI server is running
- [ ] Clear installation instructions provided when not installed
- [ ] Start instructions shown when installed but not running
- [ ] Test connection button verifies connectivity
- [ ] Latency displayed on successful connection

---

### Epic 2.2: Booking UX Improvement

**Goal**: Make ActForge booking flow clear and intuitive
**Current UX Score**: 6/10 → Target: 9/10

---

#### Task 2.2.1: Redesign Booking Modal with Type Selection

**Goal**: Add clear booking type selector with descriptions and pricing.

**Scope**:
- INCLUDED: Booking type tabs/cards (Blink/Deep/Epic)
- INCLUDED: Clear descriptions of each type
- INCLUDED: Pricing display
- INCLUDED: Time/take estimates
- EXCLUDED: Payment processing (separate task)

**Implementation Steps**:

1. Update `apps/desktop/src/renderer/components/booking-modal.tsx`:
```typescript
import React, { useState } from 'react';
import { X, Zap, Layers, Star, Clock, DollarSign, Film } from 'lucide-react';
import { cn } from '../lib/utils';
import { announce } from '../lib/accessibility';

type BookingType = 'blink' | 'deep' | 'epic';

interface BookingTypeInfo {
  id: BookingType;
  name: string;
  icon: React.ReactNode;
  description: string;
  takes: string;
  turnaround: string;
  priceRange: string;
  features: string[];
  recommended?: boolean;
}

const BOOKING_TYPES: BookingTypeInfo[] = [
  {
    id: 'blink',
    name: 'Blink',
    icon: <Zap className="w-5 h-5" />,
    description: 'Quick single-take performance',
    takes: '1 take',
    turnaround: '< 1 hour',
    priceRange: '$5 - $25',
    features: [
      'Single performance take',
      'Basic motion capture',
      'Standard quality',
    ],
  },
  {
    id: 'deep',
    name: 'Deep',
    icon: <Layers className="w-5 h-5" />,
    description: 'Multiple takes with selection',
    takes: '3-5 takes',
    turnaround: '2-4 hours',
    priceRange: '$25 - $100',
    features: [
      'Multiple performance options',
      'Choose best take',
      'Higher quality motion',
      'Emotion variations',
    ],
    recommended: true,
  },
  {
    id: 'epic',
    name: 'Epic',
    icon: <Star className="w-5 h-5" />,
    description: 'Full creative session',
    takes: '10+ takes',
    turnaround: '24-48 hours',
    priceRange: '$100 - $500',
    features: [
      'Extended session',
      'Multiple scenes',
      'Director collaboration',
      'Revisions included',
      'Premium quality',
    ],
  },
];

interface BookingModalProps {
  performer: {
    id: string;
    name: string;
    avatar: string;
    pricing: {
      blink: number;
      deep: number;
      epic: number;
    };
  };
  onClose: () => void;
  onBook: (type: BookingType) => void;
}

export function BookingModal({ performer, onClose, onBook }: BookingModalProps) {
  const [selectedType, setSelectedType] = useState<BookingType>('deep');
  const [isBooking, setIsBooking] = useState(false);

  const handleBook = async () => {
    setIsBooking(true);
    announce(`Booking ${selectedType} session with ${performer.name}`);

    try {
      await onBook(selectedType);
    } finally {
      setIsBooking(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="booking-title"
    >
      <div
        className="bg-surface-900 rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-surface-700 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img
              src={performer.avatar}
              alt=""
              className="w-12 h-12 rounded-full"
            />
            <div>
              <h2 id="booking-title" className="text-lg font-medium">
                Book {performer.name}
              </h2>
              <p className="text-sm text-surface-400">
                Select a booking type to continue
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface-700 rounded-lg"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Booking Type Selection */}
        <div className="p-6">
          <div className="grid grid-cols-3 gap-4 mb-6">
            {BOOKING_TYPES.map((type) => (
              <button
                key={type.id}
                onClick={() => {
                  setSelectedType(type.id);
                  announce(`Selected ${type.name} booking`);
                }}
                className={cn(
                  'relative p-4 rounded-lg border-2 text-left transition-all',
                  selectedType === type.id
                    ? 'border-brand-500 bg-brand-500/10'
                    : 'border-surface-700 hover:border-surface-600'
                )}
                aria-pressed={selectedType === type.id}
              >
                {type.recommended && (
                  <span className="absolute -top-2 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-brand-500 text-xs rounded-full">
                    Recommended
                  </span>
                )}
                <div className={cn(
                  'w-10 h-10 rounded-lg flex items-center justify-center mb-3',
                  selectedType === type.id
                    ? 'bg-brand-500/20 text-brand-400'
                    : 'bg-surface-700 text-surface-400'
                )}>
                  {type.icon}
                </div>
                <h3 className="font-medium mb-1">{type.name}</h3>
                <p className="text-sm text-surface-400 mb-3">{type.description}</p>
                <div className="space-y-1 text-xs">
                  <div className="flex items-center gap-2 text-surface-400">
                    <Film className="w-3 h-3" />
                    <span>{type.takes}</span>
                  </div>
                  <div className="flex items-center gap-2 text-surface-400">
                    <Clock className="w-3 h-3" />
                    <span>{type.turnaround}</span>
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Selected Type Details */}
          <div className="bg-surface-800 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium">
                {BOOKING_TYPES.find((t) => t.id === selectedType)?.name} Booking
              </h3>
              <div className="text-2xl font-bold text-brand-400">
                ${performer.pricing[selectedType]}
              </div>
            </div>
            <ul className="space-y-2">
              {BOOKING_TYPES.find((t) => t.id === selectedType)?.features.map((feature, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-surface-300">
                  <div className="w-1.5 h-1.5 rounded-full bg-brand-400" />
                  {feature}
                </li>
              ))}
            </ul>
          </div>

          {/* Action */}
          <button
            onClick={handleBook}
            disabled={isBooking}
            className="w-full btn-primary py-3 text-lg"
          >
            {isBooking ? 'Processing...' : `Book ${BOOKING_TYPES.find((t) => t.id === selectedType)?.name} - $${performer.pricing[selectedType]}`}
          </button>
        </div>
      </div>
    </div>
  );
}
```

**Acceptance Criteria**:
- [ ] Three booking types displayed as cards
- [ ] "Deep" marked as recommended
- [ ] Each card shows: icon, name, description, takes, turnaround
- [ ] Selected card highlighted with border
- [ ] Price updates based on selection
- [ ] Features list shown for selected type
- [ ] Clear CTA button with price

---

## Phase 3: Polish

**Duration**: 1 week
**Goal**: Elevate all 7-9 UX features to 10/10
**Priority**: Micro-interactions, edge cases, accessibility perfection

---

### Epic 3.1: Video Assembly Clarity

#### Task 3.1.1: Add Assembly Progress Visualization

**Goal**: Show clear progress when assembling movie from timeline.

**Implementation**: Add step-by-step progress indicator showing: Collecting clips → Applying transitions → Mixing audio → Encoding → Complete

---

### Epic 3.2: Transition Preview

#### Task 3.2.1: Add Real-time Transition Preview

**Goal**: Preview transitions between clips before final render.

**Implementation**: Add hover preview on transition points showing fade/crossfade effect.

---

### Epic 3.3: Complete Accessibility Audit

#### Task 3.3.1: WCAG 2.1 AA Compliance Check

**Goal**: Ensure every component meets accessibility standards.

**Implementation**:
1. Run automated accessibility tests with axe-core
2. Manual keyboard navigation testing for all flows
3. Screen reader testing with NVDA/VoiceOver
4. Fix any identified issues

---

## Phase 4: Network Integration

**Duration**: 3 weeks
**Goal**: Bridge desktop app to network services
**Priority**: Enable distribution, monetization, social features

---

### Epic 4.1: Authentication Bridge

#### Task 4.1.1: Create Auth UI in Desktop App

**Goal**: Add login/register modals to desktop app.

**Scope**:
- INCLUDED: Login form (email/password)
- INCLUDED: Register form (email/username/password)
- INCLUDED: Password reset flow
- INCLUDED: Token storage in electron secure storage
- INCLUDED: Session persistence across app restarts

**Implementation Steps**:

1. Create `apps/desktop/src/renderer/components/auth/LoginModal.tsx`
2. Create `apps/desktop/src/renderer/components/auth/RegisterModal.tsx`
3. Create `apps/desktop/src/renderer/stores/auth-store.ts`
4. Create `apps/desktop/src/renderer/api/network-client.ts` for network API calls
5. Store tokens using `electron-store` or `keytar` for secure storage

---

#### Task 4.1.2: Create Network API Client

**Goal**: TypeScript client for network services.

**Scope**:
- INCLUDED: Base HTTP client with auth headers
- INCLUDED: Token refresh logic
- INCLUDED: All auth endpoints
- INCLUDED: Distribution endpoints
- INCLUDED: Error handling and retries

---

### Epic 4.2: Publish Flow

#### Task 4.2.1: Add "Publish to Story Heaven" Button

**Goal**: Allow publishing exported videos to Story Heaven.

**Scope**:
- INCLUDED: Publish button on export success
- INCLUDED: Title, description, tags input
- INCLUDED: Thumbnail selection
- INCLUDED: Upload progress
- INCLUDED: Success/error feedback

---

### Epic 4.3: Creator Dashboard

#### Task 4.3.1: Add Earnings Page

**Goal**: Show performer earnings and payout status.

**Scope**:
- INCLUDED: Earnings summary cards
- INCLUDED: Transaction history
- INCLUDED: Payout request button
- INCLUDED: Balance display

---

## Top 10 Highest-Leverage Improvements

| Rank | Improvement | Current UX | Target UX | Effort | Impact |
|------|-------------|------------|-----------|--------|--------|
| 1 | **Fix Lip Sync Backend TODOs** | 4/10 | 9/10 | 4 hours | Unlocks core "talking characters" value |
| 2 | **Add Generate Dialogue Button** | 6/10 | 9/10 | 1 day | Makes audio workflow discoverable |
| 3 | **Add Audio Mixer to Timeline** | 5/10 | 9/10 | 2 days | Enables audio control users expect |
| 4 | **Implement LatentSync Provider** | 0/10 | 9/10 | 1 week | Delivers advertised feature |
| 5 | **Create Auth Bridge** | 0/10 | 9/10 | 3 days | Enables monetization path |
| 6 | **Add Publish Flow** | 0/10 | 9/10 | 2 days | Enables distribution |
| 7 | **ComfyUI Setup Wizard** | 6/10 | 9/10 | 1 day | Reduces local GPU friction |
| 8 | **Redesign Booking Modal** | 6/10 | 9/10 | 1 day | Makes ActForge usable |
| 9 | **Add Creator Earnings Page** | 3/10 | 9/10 | 2 days | Performer trust and retention |
| 10 | **Transition Preview** | 7/10 | 10/10 | 1 day | Timeline polish |

---

## Rollout Plan

### Stage 1: Development (Weeks 1-4)

| Week | Phase | Focus |
|------|-------|-------|
| 1 | Phase 1 | Lip sync fixes, audio workflow surfacing |
| 2 | Phase 1 | LatentSync implementation |
| 3 | Phase 2 | Local GPU wizard, booking UX |
| 4 | Phase 3 | Polish, accessibility audit |

### Stage 2: Staging (Week 5)

1. Deploy all changes to staging environment
2. Full regression test suite
3. Performance benchmarking
4. Security review of auth changes
5. Load testing for network services

**Staging Checklist**:
- [ ] All E2E tests pass
- [ ] No console errors
- [ ] Lighthouse accessibility score > 90
- [ ] Core Web Vitals pass
- [ ] All API endpoints respond < 500ms (p95)
- [ ] Memory usage stable (no leaks over 1 hour)

### Stage 3: QA (Week 6)

**QA Test Plan**:

1. **Smoke Tests** (Day 1)
   - Create new project
   - Upload screenplay
   - Generate one shot
   - Export video

2. **Feature Tests** (Days 2-3)
   - Every new feature tested against acceptance criteria
   - Edge cases and error scenarios
   - Cross-browser testing (Chrome, Firefox, Safari)

3. **Regression Tests** (Days 4-5)
   - All existing functionality still works
   - Performance not degraded
   - No new accessibility issues

4. **User Acceptance Testing** (Day 5)
   - 5 external users test new features
   - Collect feedback
   - Prioritize any critical fixes

### Stage 4: Production (Week 7)

**Rollout Strategy**: Progressive rollout

1. **Day 1**: Deploy to 5% of users
   - Monitor error rates
   - Monitor performance metrics
   - 24-hour observation

2. **Day 2**: Expand to 25% of users
   - Continue monitoring
   - Address any reported issues

3. **Day 3**: Expand to 50% of users
   - Prepare rollback if needed

4. **Day 5**: Full rollout (100%)
   - Announce new features
   - Update documentation

**Rollback Criteria**:
- Error rate > 1% (baseline + 0.5%)
- P95 latency > 2x baseline
- Any critical security issue
- Any data loss or corruption

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LatentSync model not available | Medium | High | Implement with fallback to Wav2Lip, document as "coming soon" if delayed |
| ComfyUI API changes | Low | Medium | Version lock and test with specific ComfyUI version |
| Network services authentication issues | Medium | High | Extensive security testing, rate limiting, proper token handling |
| Performance regression from new features | Medium | Medium | Performance benchmarks in CI, monitor in staging |
| Accessibility issues missed | Low | Medium | Automated tests + manual screen reader testing |
| Database migrations fail | Low | High | Test migrations on production data copy, have rollback scripts ready |

---

## Appendix: File Locations Quick Reference

### Backend (packages/core/scenemachine/)

| Area | Location |
|------|----------|
| API Routes | `api/routes/` |
| Services | `services/` |
| Models | `models/` |
| IPC Handlers | `ipc/handlers.py` |
| Generators | `generators/` |
| Lip Sync | `services/lipsync.py`, `api/routes/lipsync.py` |
| Audio | `services/audio.py`, `api/routes/audio.py` |

### Frontend (apps/desktop/src/renderer/)

| Area | Location |
|------|----------|
| Pages | `pages/` |
| Components | `components/` |
| Stores | `stores/` |
| Lib/Utils | `lib/` |
| Styles | `styles/` |
| API Client | `api/client.ts` |

### Network Services (packages/network/services/)

| Service | Location |
|---------|----------|
| Auth | `auth/` |
| Distribution | `distribution/` |
| Social | `social/` |
| Monetization | `monetization/` |
| Streaming | `streaming/` |

---

**End of Road Home Implementation Plan**

*This document serves as the complete roadmap to achieve 10/10 UX across the entire SceneMachine platform. Execute phases sequentially, validate each task against acceptance criteria, and maintain the Definition of Done throughout implementation.*
