# SceneMachine Troubleshooting Guide

This guide helps diagnose and resolve common issues in SceneMachine.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Generation Issues](#generation-issues)
3. [Provider Issues](#provider-issues)
4. [Database Issues](#database-issues)
5. [Performance Issues](#performance-issues)
6. [Frontend Issues](#frontend-issues)
7. [Export Issues](#export-issues)

---

## Quick Diagnostics

### System Status Check

```bash
# Check all health endpoints
curl -s http://localhost:8000/health | jq '.'
curl -s http://localhost:8000/health/detailed | jq '.'
curl -s http://localhost:8000/health/providers | jq '.'
```

### Common First Steps

1. **Check logs for errors**
   ```bash
   tail -100 /var/log/scenemachine/app.log | grep ERROR
   ```

2. **Check service status**
   ```bash
   systemctl status scenemachine
   ```

3. **Check resource usage**
   ```bash
   top -p $(pgrep -f scenemachine)
   free -h
   df -h
   ```

---

## Generation Issues

### Jobs Stuck in "Pending" State

**Symptoms**: Jobs remain pending, not starting

**Causes**:
- Queue worker not running
- Max concurrent jobs reached
- All providers unavailable

**Solutions**:

1. Check worker status:
   ```bash
   curl http://localhost:8000/api/v1/generation/worker/status
   ```

2. Check queue status:
   ```bash
   curl http://localhost:8000/api/v1/generation/queue
   ```

3. Restart worker if needed:
   ```bash
   curl -X POST http://localhost:8000/api/v1/generation/worker/resume
   ```

### Jobs Stuck in "Running" State

**Symptoms**: Jobs show "running" but never complete

**Causes**:
- Provider timeout
- Network issues
- Job processing crash

**Solutions**:

1. Check job details:
   ```bash
   curl http://localhost:8000/api/v1/generation/jobs/{job_id}
   ```

2. Cancel stuck job:
   ```bash
   curl -X POST http://localhost:8000/api/v1/generation/jobs/{job_id}/cancel
   ```

3. Check provider health:
   ```bash
   curl http://localhost:8000/health/providers
   ```

### Jobs Failing Immediately

**Symptoms**: Jobs fail within seconds of starting

**Causes**:
- Invalid API key
- Provider authentication failed
- Invalid prompt or parameters

**Solutions**:

1. Check error message in job details
2. Verify API keys in settings:
   ```bash
   curl http://localhost:8000/api/v1/settings/providers
   ```
3. Test provider directly with simple request

---

## Provider Issues

### Circuit Breaker Open

**Symptoms**: All requests to a provider fail immediately with "Circuit open" error

**Causes**:
- Multiple consecutive failures
- Provider outage
- Rate limiting

**Solutions**:

1. Check circuit breaker status:
   ```bash
   curl http://localhost:8000/api/v1/settings/circuit-breakers
   ```

2. Wait for automatic recovery (typically 60 seconds)

3. Manual reset (after fixing underlying issue):
   ```bash
   curl -X POST http://localhost:8000/api/v1/settings/circuit-breakers/reset?provider=replicate
   ```

### Provider Returns Errors

**Symptoms**: Jobs fail with provider-specific errors

**Common Errors**:

| Error | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Invalid API key | Update API key in settings |
| 402 Payment Required | Insufficient credits | Add credits to provider account |
| 429 Too Many Requests | Rate limited | Reduce request rate |
| 503 Service Unavailable | Provider down | Wait or use different provider |

### Provider Timeout

**Symptoms**: Jobs fail after long delay with timeout error

**Causes**:
- Slow generation (complex prompt)
- Network latency
- Provider overloaded

**Solutions**:

1. Increase timeout in configuration:
   ```python
   # circuit_breaker.py
   call_timeout=600.0  # 10 minutes
   ```

2. Simplify prompt
3. Use different provider

---

## Database Issues

### Connection Errors

**Symptoms**: "Connection refused" or "Connection pool exhausted"

**Solutions**:

1. Check database is running:
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. Check connection pool:
   ```bash
   psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='scenemachine_db';"
   ```

3. Increase pool size if needed

### Migration Errors

**Symptoms**: Application fails to start with migration error

**Solutions**:

1. Check current migration:
   ```bash
   cd packages/core
   alembic current
   ```

2. Check migration history:
   ```bash
   alembic history
   ```

3. Run pending migrations:
   ```bash
   alembic upgrade head
   ```

4. If migration fails, check for data conflicts

### Constraint Violations

**Symptoms**: Insert/update fails with constraint error

**Common Constraints**:

| Constraint | Table | Rule |
|------------|-------|------|
| ck_projects_state | projects | Valid state values only |
| ck_shots_duration_positive | shots | Duration 0-60s |
| ck_generation_jobs_progress | generation_jobs | Progress 0-100 |
| ix_scenes_project_scene_number | scenes | Unique scene number per project |

**Solution**: Fix data to comply with constraints before saving

---

## Performance Issues

### Slow API Responses

**Symptoms**: API calls take several seconds

**Causes**:
- Database queries slow
- Too many concurrent requests
- Memory pressure

**Diagnostics**:

1. Check response times in logs
2. Check database query times:
   ```bash
   grep "duration_ms" /var/log/scenemachine/app.log | sort -t: -k2 -rn | head
   ```

**Solutions**:

1. Add database indexes for slow queries
2. Enable query caching
3. Reduce concurrent requests

### High Memory Usage

**Symptoms**: Memory usage grows continuously

**Causes**:
- Video processing memory leak
- Cache not being cleared
- Too many concurrent jobs

**Solutions**:

1. Reduce `max_concurrent_jobs`
2. Restart worker periodically
3. Check for memory leaks in custom code

### Queue Processing Slow

**Symptoms**: Long queue wait times

**Solutions**:

1. Increase worker concurrency:
   ```bash
   curl -X POST http://localhost:8000/api/v1/settings/worker?max_concurrent=5
   ```

2. Use faster provider
3. Scale horizontally (multiple instances)

---

## Frontend Issues

### Desktop App Won't Start

**Symptoms**: Electron app crashes or shows blank screen

**Solutions**:

1. Check developer console (Ctrl+Shift+I)
2. Clear app cache:
   ```bash
   rm -rf ~/.config/scenemachine/
   ```
3. Reinstall application

### WebSocket Connection Failed

**Symptoms**: Real-time updates not working

**Causes**:
- Backend not running
- Firewall blocking WebSocket
- SSL/TLS issues

**Solutions**:

1. Check WebSocket endpoint:
   ```bash
   wscat -c ws://localhost:8000/ws
   ```
2. Check backend logs for WebSocket errors
3. Verify CORS configuration

### Auto-Save Not Working

**Symptoms**: Changes not being saved automatically

**Causes**:
- localStorage full
- Conflicting browser extensions
- Session expired

**Solutions**:

1. Clear localStorage:
   - Open DevTools → Application → Local Storage → Clear
2. Check auto-save status in settings
3. Disable conflicting extensions

---

## Export Issues

### Export Fails

**Symptoms**: Final movie export fails or produces corrupt file

**Causes**:
- FFmpeg not installed
- Disk space insufficient
- Video codec issues

**Diagnostics**:

1. Check FFmpeg:
   ```bash
   ffmpeg -version
   ```

2. Check disk space:
   ```bash
   df -h /path/to/exports
   ```

**Solutions**:

1. Install FFmpeg:
   ```bash
   apt-get install ffmpeg
   ```
2. Free disk space
3. Try different export format

### Missing Audio

**Symptoms**: Exported video has no audio

**Causes**:
- TTS not configured
- Audio generation failed
- Audio track missing

**Solutions**:

1. Check TTS provider settings
2. Regenerate audio for scenes
3. Verify audio files exist in project

### Poor Video Quality

**Symptoms**: Exported video looks worse than previews

**Causes**:
- Low quality setting
- Re-encoding degradation
- Wrong resolution

**Solutions**:

1. Use higher quality preset
2. Match source resolution
3. Use ProRes for intermediate exports

---

## Getting Help

### Information to Collect

When reporting issues, include:

1. **System information**
   ```bash
   uname -a
   python --version
   ffmpeg -version
   ```

2. **Error logs**
   - Last 50 lines of application log
   - Full stack trace

3. **Steps to reproduce**
   - What you were doing
   - Expected behavior
   - Actual behavior

4. **Configuration**
   - Provider settings (without API keys)
   - Export settings
   - Project size (scenes, shots)

### Log Collection Script

```bash
#!/bin/bash
# collect_diagnostics.sh

echo "=== System Info ===" > diagnostics.txt
uname -a >> diagnostics.txt
python --version >> diagnostics.txt

echo "=== Health Status ===" >> diagnostics.txt
curl -s http://localhost:8000/health/detailed >> diagnostics.txt

echo "=== Recent Errors ===" >> diagnostics.txt
tail -100 /var/log/scenemachine/app.log | grep -E "(ERROR|WARNING)" >> diagnostics.txt

echo "=== Resource Usage ===" >> diagnostics.txt
free -h >> diagnostics.txt
df -h >> diagnostics.txt

echo "Diagnostics collected in diagnostics.txt"
```

### Support Resources

- GitHub Issues: Report bugs and feature requests
- Documentation: `/docs/` directory
- Logs: `/var/log/scenemachine/`
