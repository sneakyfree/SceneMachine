#!/usr/bin/env python3
"""
Core Pipeline Verification Script

Tests all core services in the SceneMachine pipeline:
1. Video Generation (MockGenerationProvider)
2. TTS Audio Generation (MockTTSProvider) 
3. Lip-sync (MockLipSyncProvider)
4. Assembly/Export (AssemblyService)

Run with: python scripts/verify_pipeline.py
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "core"))

from scenemachine.services.generation import (
    MockGenerationProvider,
    GenerationRequest,
)
from scenemachine.services.audio import (
    MockTTSProvider,
    TTSRequest,
)
from scenemachine.services.lipsync import (
    MockLipSyncProvider,
    LipSyncData,
)

# Results tracking
results = {
    "generation": None,
    "tts": None,
    "lipsync": None,
    "assembly": None,
}


async def verify_generation():
    """Test 1.1: Verify video generation with mock provider."""
    print("\n[1/4] Testing Video Generation Service...")
    provider = MockGenerationProvider()
    
    # Check availability
    available = await provider.check_availability()
    print(f"  Provider availability: {available}")
    
    # Create test request
    request = GenerationRequest(
        shot_id=uuid4(),
        prompt="A beautiful sunset over the ocean",
        negative_prompt="blur, distortion",
        width=1280,
        height=720,
        duration_seconds=3.0,
    )
    
    # Track progress (async callback)
    async def on_progress(progress):
        print(f"  Progress: {progress.percent:.0f}% - {progress.message}")
    
    # Generate
    result = await provider.generate(request, progress_callback=on_progress)
    
    if result.success:
        print(f"  ✅ Generation SUCCESS")
        print(f"     Output: {result.output_path}")
        print(f"     Duration: {result.duration_seconds}s")
        print(f"     Cost: ${result.cost_usd or 0:.4f}")
    else:
        print(f"  ❌ Generation FAILED: {result.error_message}")
    
    return result.success, result


async def verify_tts():
    """Test 1.4: Verify TTS audio generation."""
    print("\n[2/4] Testing TTS Audio Service...")
    provider = MockTTSProvider()
    
    # Check availability
    available = await provider.check_availability()
    print(f"  Provider availability: {available}")
    
    # List voices
    voices = await provider.get_voices()
    print(f"  Available voices: {len(voices)}")
    
    # Create test request
    request = TTSRequest(
        text="Hello, this is a test of the text to speech system.",
        voice_id="mock_female_1",
    )
    
    # Track progress (async callback)
    async def on_progress(progress):
        print(f"  Progress: {progress.percent:.0f}% - {progress.message}")
    
    # Generate
    result = await provider.generate(request, progress_callback=on_progress)
    
    if result.success:
        print(f"  ✅ TTS Generation SUCCESS")
        print(f"     Output: {result.audio_path}")
        print(f"     Duration: {result.duration_seconds}s")
    else:
        print(f"  ❌ TTS Generation FAILED: {result.error_message}")
    
    return result.success, result


async def verify_lipsync():
    """Test 1.2: Verify lip-sync service."""
    print("\n[3/4] Testing Lip-sync Service...")
    provider = MockLipSyncProvider()
    
    # Check availability
    available = await provider.check_availability()
    print(f"  Provider availability: {available}")
    
    # Create temp audio file for testing
    temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_audio.close()
    
    # Track progress (async callback)
    async def on_progress(progress):
        print(f"  Progress: {progress.percent:.0f}% - {progress.message}")
    
    try:
        # Analyze audio
        result = await provider.analyze_audio(
            temp_audio.name,
            progress_callback=on_progress
        )
        
        if result.success:
            print(f"  ✅ Lip-sync Analysis SUCCESS")
            print(f"     Phonemes: {len(result.lip_sync_data.phonemes)}")
            print(f"     Duration: {result.lip_sync_data.duration_seconds}s")
        else:
            print(f"  ❌ Lip-sync Analysis FAILED: {result.error_message}")
        
        return result.success, result
    finally:
        os.unlink(temp_audio.name)


async def verify_assembly():
    """Test 1.3: Verify assembly produces MP4."""
    print("\n[4/4] Testing Assembly/Export Service...")
    
    # Check FFmpeg availability
    try:
        from scenemachine.utils.ffmpeg import FFmpeg
        ffmpeg = FFmpeg()
        info = await ffmpeg.ensure_available()
        print(f"  FFmpeg available: {info.ffmpeg_path}")
        print(f"  FFmpeg version: {info.version[:50] if info.version else 'unknown'}...")
        
        # Create a simple test video with FFmpeg
        temp_dir = tempfile.mkdtemp()
        test_output = Path(temp_dir) / "test_output.mp4"
        
        # Generate a 2-second test video
        cmd = [
            info.ffmpeg_path,
            "-y",
            "-f", "lavfi",
            "-i", "color=c=blue:s=640x360:d=2",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "2",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(test_output)
        ]
        
        import subprocess
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if test_output.exists() and test_output.stat().st_size > 0:
            file_size = test_output.stat().st_size
            print(f"  ✅ Assembly/Export SUCCESS")
            print(f"     Output: {test_output}")
            print(f"     Size: {file_size / 1024:.1f} KB")
            
            # Cleanup
            os.unlink(test_output)
            os.rmdir(temp_dir)
            return True, {"output": str(test_output), "size": file_size}
        else:
            print(f"  ❌ Assembly FAILED: No output file")
            return False, {"error": "No output file"}
            
    except Exception as e:
        print(f"  ❌ Assembly FAILED: {e}")
        return False, {"error": str(e)}


async def main():
    """Run all verification tests."""
    print("=" * 60)
    print("SCENEMACHINE CORE PIPELINE VERIFICATION")
    print("=" * 60)
    
    # Run all tests
    results["generation"] = await verify_generation()
    results["tts"] = await verify_tts()
    results["lipsync"] = await verify_lipsync()
    results["assembly"] = await verify_assembly()
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, (success, _) in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {name.upper():15} {status}")
        if not success:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 ALL CORE PIPELINE TESTS PASSED!")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - Review above for details")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
