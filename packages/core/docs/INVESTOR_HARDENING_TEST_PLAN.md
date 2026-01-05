# SceneMachine Investor-Ready Hardening Test Plan

## Executive Summary

This plan outlines a comprehensive end-to-end hardening test strategy to demonstrate SceneMachine's full feature set and production readiness to investors. The goal is to showcase all platform capabilities while ensuring stability and reliability.

---

## Current State Analysis

### Existing Test Infrastructure
- **Mock Data Generator**: Generates realistic test data but has SQLite ARRAY type limitations
- **Smoke Tests**: 48 tests covering basic functionality
- **API Endpoint Tests**: 59 tests covering all routes
- **IPC Handler Tests**: 159 tests for Electron IPC
- **Workflow Tests**: 3 integration tests (1 skipped for SQLite)
- **Current Pass Rate**: 99.6% (268/269)

### Known Limitations
1. **SQLite ARRAY Incompatibility**: Character and Scene models use PostgreSQL ARRAY types
2. **No Real Video Generation**: Tests use mock providers
3. **Limited Audio Testing**: Audio assets skipped for SQLite
4. **Frontend Not Tested**: Current tests only cover backend

---

## Phase 1: Fix Mock Data Generator for PostgreSQL (2 hours)

### Problem
The mock data generator skips characters, scenes, shots, and audio for SQLite compatibility. This means we're not testing the full data model.

### Solution
Create a PostgreSQL test environment for comprehensive testing.

### Tasks
1. **Set up PostgreSQL test database**
   ```bash
   # Create dedicated test database
   docker run -d --name scenemachine-test-db \
     -e POSTGRES_DB=scenemachine_test \
     -e POSTGRES_USER=test \
     -e POSTGRES_PASSWORD=test \
     -p 5433:5432 postgres:15
   ```

2. **Update mock data generator for full entity generation**
   - Remove SQLite skip conditions
   - Run against PostgreSQL for full data generation
   - Generate:
     - 10+ projects in various states
     - 100+ characters with full physical descriptions
     - 200+ scenes with breakdowns
     - 500+ shots in all states
     - 50+ audio assets (SFX + music)
     - Export history with various statuses

3. **Verification criteria**
   - All entity types populated
   - Proper relationships between entities
   - Realistic data distribution across states

---

## Phase 2: Enhanced Workflow Tests (3 hours)

### New Workflow Test Scenarios

#### 2.1 Complete Movie Production Workflow
```python
class InvestorDemoWorkflow:
    """Full production workflow from screenplay to export."""

    async def test_complete_pipeline(self):
        # Step 1: Create project
        # Step 2: Upload screenplay (Fountain format)
        # Step 3: Parse screenplay - verify scenes/characters extracted
        # Step 4: Generate movie plan - verify AI analysis
        # Step 5: Approve movie plan
        # Step 6: Set up characters - add physical descriptions
        # Step 7: Upload character references
        # Step 8: Lock characters
        # Step 9: Generate scene breakdowns
        # Step 10: Approve shot breakdowns
        # Step 11: Queue shots for generation
        # Step 12: Simulate generation completion
        # Step 13: Approve generated shots
        # Step 14: Export final movie
        # Step 15: Verify export history
```

#### 2.2 Collaboration Workflow
```python
async def test_sharing_workflow(self):
    # Step 1: Create project with content
    # Step 2: Create share link with edit permissions
    # Step 3: Accept share invitation
    # Step 4: Add comments to shots
    # Step 5: Resolve comments
    # Step 6: Revoke share access
    # Step 7: Verify access revoked
```

#### 2.3 Generation Queue Workflow
```python
async def test_generation_queue(self):
    # Step 1: Queue multiple shots
    # Step 2: Verify priority ordering
    # Step 3: Pause queue worker
    # Step 4: Resume queue worker
    # Step 5: Cancel pending job
    # Step 6: Retry failed job
    # Step 7: Batch approve completed shots
```

#### 2.4 Timeline Editing Workflow
```python
async def test_timeline_workflow(self):
    # Step 1: Load project timeline
    # Step 2: Reorder shots
    # Step 3: Add transitions
    # Step 4: Add text overlays
    # Step 5: Apply color grading
    # Step 6: Preview export settings
```

---

## Phase 3: Provider Integration Tests (2 hours)

### Mock Provider Verification
Test all video generation providers work correctly with mock responses:

```python
class ProviderIntegrationTests:
    """Test all generation providers."""

    async def test_replicate_provider(self):
        # Verify request formatting
        # Verify response handling
        # Verify cost calculation

    async def test_fal_provider(self):
        # Same as above

    async def test_comfyui_provider(self):
        # Local provider tests

    async def test_runpod_provider(self):
        # Serverless provider tests

    async def test_circuit_breaker_behavior(self):
        # Simulate failures
        # Verify circuit opens
        # Verify half-open recovery
        # Verify fallback behavior
```

### Audio Provider Tests
```python
async def test_elevenlabs_provider(self):
    # Voice listing
    # TTS generation (mock)
    # Cost estimation

async def test_openai_tts_provider(self):
    # Same as above
```

---

## Phase 4: API Comprehensive Tests (3 hours)

### Expand API Test Coverage

#### 4.1 Analytics Endpoints (Full)
```python
async def test_analytics_comprehensive(self):
    # Dashboard stats with real data
    # Generation stats by time range
    # Cost stats by provider/model
    # Daily trends
    # Budget alerts
```

#### 4.2 Assembly/Export Endpoints (Full)
```python
async def test_assembly_comprehensive(self):
    # Check readiness with incomplete project
    # Check readiness with complete project
    # Export with all format options
    # Export with color grading
    # Export with watermark
    # Export with subtitles
    # Cancel in-progress export
    # Export history retrieval
```

#### 4.3 Generation Endpoints (Full)
```python
async def test_generation_comprehensive(self):
    # Queue single shot
    # Queue scene (all shots)
    # Queue project (all shots)
    # Get queue status
    # Get pending jobs with filters
    # Job progress tracking
    # Cost estimation
    # Provider health checks
    # Worker status and controls
```

#### 4.4 Error Handling Tests
```python
async def test_error_handling(self):
    # 400 Bad Request scenarios
    # 404 Not Found scenarios
    # 422 Validation Error scenarios
    # 500 Internal Error handling
    # Rate limiting behavior
    # Authentication failures
```

---

## Phase 5: Performance Benchmarks (2 hours)

### Benchmark Suite
```python
class PerformanceBenchmarks:
    """Performance tests for investor demo."""

    async def benchmark_screenplay_parsing(self):
        # Parse 10-page screenplay: target <1s
        # Parse 100-page screenplay: target <5s

    async def benchmark_shot_breakdown_generation(self):
        # Generate breakdown for 1 scene: target <3s
        # Generate breakdown for full movie: target <30s

    async def benchmark_api_latency(self):
        # GET endpoints: target <50ms avg
        # POST endpoints: target <100ms avg
        # List endpoints with pagination: target <200ms

    async def benchmark_database_queries(self):
        # Project with 50 scenes, 200 shots: <100ms
        # Analytics aggregation: <500ms

    async def benchmark_export_preparation(self):
        # Timeline assembly check: <1s
        # Export job creation: <500ms
```

### Load Testing
```python
async def test_concurrent_requests(self):
    # 10 concurrent API requests
    # 50 concurrent queue operations
    # Measure degradation

async def test_queue_throughput(self):
    # Queue 100 shots rapidly
    # Measure processing rate
    # Verify no drops
```

---

## Phase 6: Security Validation (1 hour)

### Security Tests
```python
class SecurityTests:
    """Validate security measures."""

    async def test_rate_limiting(self):
        # Hit rate limit
        # Verify 429 response
        # Verify recovery after window

    async def test_input_validation(self):
        # SQL injection attempts
        # XSS payload handling
        # Path traversal attempts

    async def test_authentication(self):
        # Invalid API key handling
        # Missing auth handling
        # Session management

    async def test_security_headers(self):
        # CSP headers present
        # X-Frame-Options
        # HSTS headers
```

---

## Phase 7: Investor Demo Data Setup (1 hour)

### Create Showcase Dataset
```python
class InvestorDemoData:
    """Generate impressive demo data."""

    async def create_demo_projects(self):
        # Project 1: "The Phoenix Protocol" - Complete film, exported
        # Project 2: "Midnight's Edge" - In generation, 80% complete
        # Project 3: "Echoes of Tomorrow" - Scene planning stage
        # Project 4: "Crimson Dawn" - Character design stage
        # Project 5: "Beyond the Veil" - Just uploaded screenplay

    async def create_demo_analytics(self):
        # 30 days of generation history
        # Cost data showing reasonable spending
        # Impressive success rates (95%+)
        # Provider usage distribution

    async def create_demo_exports(self):
        # Multiple export formats completed
        # Various resolutions
        # Show processing times
```

---

## Phase 8: Comprehensive Test Runner (1 hour)

### New Hardening Test Script
Create enhanced test runner that:

1. **Setup Phase**
   - Start PostgreSQL container
   - Initialize clean database
   - Generate comprehensive mock data

2. **Test Execution Phase**
   - Run all test categories in order
   - Capture detailed logs
   - Generate screenshots/artifacts

3. **Report Generation**
   - Executive summary for investors
   - Detailed technical report
   - Performance metrics
   - Coverage analysis

4. **Cleanup Phase**
   - Preserve reports
   - Optionally keep database for demo

### Expected Output
```
================================================================================
SCENEMACHINE INVESTOR HARDENING TEST REPORT
================================================================================

TEST ENVIRONMENT
----------------
Database: PostgreSQL 15
Python: 3.11
Test Duration: 8 minutes 32 seconds

EXECUTIVE SUMMARY
-----------------
Overall Success Rate: 99.8%
Total Tests Run: 450+
Critical Features: ALL PASSING

MOCK DATA GENERATED
-------------------
Projects: 10 (across all workflow states)
Characters: 85 (with full physical descriptions)
Scenes: 180 (with AI-generated breakdowns)
Shots: 520 (various generation states)
Generation Jobs: 600+ (showing queue history)
Audio Assets: 50 (SFX + Music library)
Export History: 25 (various formats)
Shares/Comments: 40 (collaboration features)

TEST RESULTS BY CATEGORY
------------------------
[✓] Smoke Tests: 48/48 (100%)
[✓] API Endpoints: 75/75 (100%)
[✓] IPC Handlers: 159/159 (100%)
[✓] Workflow Integration: 8/8 (100%)
[✓] Provider Integration: 20/20 (100%)
[✓] Performance Benchmarks: 15/15 (100%)
[✓] Security Validation: 12/12 (100%)
[✓] Error Handling: 18/18 (100%)
[⚠] Load Tests: 14/15 (93% - 1 timeout at 100 concurrent)

PERFORMANCE HIGHLIGHTS
----------------------
API Response Time (avg): 42ms
Screenplay Parsing (100 pages): 3.2s
Shot Breakdown Generation: 2.8s
Database Query Time (avg): 18ms
Queue Throughput: 25 jobs/second

FEATURES DEMONSTRATED
---------------------
✓ Screenplay Upload & Parsing (Fountain, FDX, PDF)
✓ AI Movie Planning with Genre/Theme Analysis
✓ Character Management with Physical Descriptions
✓ Voice Assignment with TTS Preview
✓ Scene Planning with AI Breakdowns
✓ Video Generation Queue with Priority
✓ Multi-Provider Support (Replicate, Fal, ComfyUI, RunPod)
✓ Circuit Breaker for Provider Resilience
✓ Timeline Editor with Transitions
✓ Color Grading with LUT Support
✓ Text Overlays and Subtitles
✓ Multi-Format Export (MP4, ProRes, WebM)
✓ Project Sharing and Collaboration
✓ Cost Tracking and Budget Alerts
✓ Admin Health Dashboard

OVERALL STATUS: PASS
Ready for Investor Demo
================================================================================
```

---

## Implementation Checklist

### Prerequisites
- [ ] Docker installed for PostgreSQL
- [ ] Python 3.11+ environment
- [ ] All dependencies installed

### Phase 1: Database Setup
- [ ] Create PostgreSQL test container
- [ ] Update database URL configuration
- [ ] Verify connection

### Phase 2: Mock Data Enhancement
- [ ] Remove SQLite skip conditions
- [ ] Add character generation with ARRAY handling
- [ ] Add scene generation with relationships
- [ ] Add shot generation with states
- [ ] Add audio asset generation
- [ ] Verify all entities created

### Phase 3: Workflow Tests
- [ ] Implement complete production workflow test
- [ ] Implement collaboration workflow test
- [ ] Implement generation queue workflow test
- [ ] Implement timeline editing workflow test

### Phase 4: Provider Tests
- [ ] Test all video providers
- [ ] Test audio providers
- [ ] Test circuit breaker behavior

### Phase 5: API Tests
- [ ] Expand analytics tests
- [ ] Expand assembly tests
- [ ] Expand generation tests
- [ ] Add error handling tests

### Phase 6: Performance Tests
- [ ] Add benchmark suite
- [ ] Add load tests
- [ ] Document performance targets

### Phase 7: Security Tests
- [ ] Rate limiting tests
- [ ] Input validation tests
- [ ] Auth tests
- [ ] Header tests

### Phase 8: Demo Data
- [ ] Create showcase projects
- [ ] Generate realistic analytics
- [ ] Create export history

### Phase 9: Test Runner
- [ ] Create comprehensive test script
- [ ] Add detailed reporting
- [ ] Create investor-friendly summary

---

## Estimated Timeline

| Phase | Description | Duration |
|-------|-------------|----------|
| 1 | PostgreSQL Setup & Mock Data | 2 hours |
| 2 | Enhanced Workflow Tests | 3 hours |
| 3 | Provider Integration Tests | 2 hours |
| 4 | API Comprehensive Tests | 3 hours |
| 5 | Performance Benchmarks | 2 hours |
| 6 | Security Validation | 1 hour |
| 7 | Investor Demo Data | 1 hour |
| 8 | Test Runner & Reports | 1 hour |
| **Total** | | **15 hours** |

---

## Success Criteria

1. **Pass Rate**: 99%+ across all test categories
2. **Coverage**: All major features tested
3. **Performance**: Meet benchmark targets
4. **Stability**: No crashes or critical errors
5. **Demo Ready**: Impressive data for investor presentation

---

## Files to Create/Modify

### New Files
1. `tests/investor_hardening_test.py` - Comprehensive test runner
2. `tests/workflows/test_investor_workflows.py` - Full workflow tests
3. `tests/integration/test_providers_full.py` - Provider integration tests
4. `tests/demo_data_generator.py` - Investor demo data creator
5. `docs/INVESTOR_TEST_RESULTS.md` - Results documentation

### Modified Files
1. `tests/mock_data_generator.py` - PostgreSQL support
2. `tests/hardening_test_harness.py` - Enhanced reporting
3. `tests/e2e_test_suite.py` - Additional test cases

---

## Notes for Execution

1. **Use PostgreSQL** for full testing - SQLite limitations prevent testing ~40% of the data model
2. **Run overnight** if needed - some performance tests may take time
3. **Capture logs** - Detailed logs help debug any issues
4. **Screenshot key metrics** - For investor presentation
5. **Document any failures** - Be prepared to explain limitations
