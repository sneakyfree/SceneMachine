#!/usr/bin/env python3
"""
E2E Pipeline Test - End-to-End Verification

Tests the complete screenplay-to-movie pipeline:
1. Parse screenplay
2. Setup characters
3. Generate shots
4. Assemble movie
5. Export final

Run with: python scripts/test_e2e_pipeline.py
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "core"))

from scenemachine.agents import (
    OrchestratorAgent,
    ParserAgent,
    CharacterAgent,
    GeneratorAgent,
    AssemblerAgent,
    ReviewerAgent,
    ActionContext,
)


class E2EPipelineTest:
    """End-to-end pipeline test runner."""
    
    def __init__(self):
        self.orchestrator = OrchestratorAgent(name="E2E_Director")
        self.results = {}
        
        # Register agents
        self.orchestrator.register_agent(ParserAgent(name="E2E_Parser"))
        self.orchestrator.register_agent(CharacterAgent(name="E2E_Character"))
        self.orchestrator.register_agent(GeneratorAgent(name="E2E_Generator"))
        self.orchestrator.register_agent(AssemblerAgent(name="E2E_Assembler"))
        self.orchestrator.register_agent(ReviewerAgent(name="E2E_Reviewer"))
    
    async def test_parse_phase(self) -> bool:
        """Test 1: Parse a sample screenplay."""
        print("\n[1/5] Testing Parse Phase...")
        
        context = ActionContext(project_id=uuid4())
        result = await self.orchestrator.execute(
            "run_phase",
            context,
            phase="parse",
            input_data={},
        )
        
        self.results["parse"] = result.success
        
        if result.success:
            print("  ✅ Parse phase completed")
        else:
            print(f"  ❌ Parse phase failed: {result.error_message}")
        
        return result.success
    
    async def test_character_phase(self) -> bool:
        """Test 2: Character setup phase."""
        print("\n[2/5] Testing Character Phase...")
        
        context = ActionContext(project_id=uuid4())
        result = await self.orchestrator.execute(
            "run_phase",
            context,
            phase="characters",
            input_data={
                "parse": {
                    "characters": [
                        {"name": "ALICE", "description": "Young woman, 25 years old"},
                        {"name": "BOB", "description": "Middle-aged man, gray hair"},
                    ]
                }
            },
        )
        
        self.results["characters"] = result.success
        
        if result.success:
            print(f"  ✅ Character phase completed")
            if result.output:
                print(f"     Characters: {result.output.get('count', 0)}")
        else:
            print(f"  ❌ Character phase failed: {result.error_message}")
        
        return result.success
    
    async def test_generate_phase(self) -> bool:
        """Test 3: Video generation phase."""
        print("\n[3/5] Testing Generate Phase...")
        
        context = ActionContext(project_id=uuid4())
        result = await self.orchestrator.execute(
            "run_phase",
            context,
            phase="generate",
            input_data={
                "shots": {
                    "shots": [
                        {"id": str(uuid4()), "prompt": "A sunset over the ocean"},
                        {"id": str(uuid4()), "prompt": "Two people walking on the beach"},
                    ]
                }
            },
        )
        
        self.results["generate"] = result.success
        
        if result.success:
            print(f"  ✅ Generate phase completed")
            if result.output:
                print(f"     Generated: {result.output.get('count', 0)} clips")
                print(f"     Cost: ${result.cost_usd:.4f}")
        else:
            print(f"  ❌ Generate phase failed: {result.error_message}")
        
        return result.success
    
    async def test_review_phase(self) -> bool:
        """Test 4: Quality review phase."""
        print("\n[4/5] Testing Review Phase...")
        
        context = ActionContext(project_id=uuid4())
        result = await self.orchestrator.execute(
            "run_phase",
            context,
            phase="review",
            input_data={
                "generate": {
                    "generated": [
                        {"video_path": "/tmp/test_video_1.mp4"},
                        {"video_path": "/tmp/test_video_2.mp4"},
                    ]
                }
            },
        )
        
        self.results["review"] = result.success
        
        if result.success:
            print(f"  ✅ Review phase completed")
            if result.output:
                print(f"     Pass rate: {result.output.get('pass_rate', 0) * 100:.0f}%")
        else:
            print(f"  ❌ Review phase failed: {result.error_message}")
        
        return result.success
    
    async def test_export_phase(self) -> bool:
        """Test 5: Export phase."""
        print("\n[5/5] Testing Export Phase...")
        
        context = ActionContext(project_id=uuid4())
        result = await self.orchestrator.execute(
            "run_phase",
            context,
            phase="export",
            input_data={},
        )
        
        self.results["export"] = result.success
        
        if result.success:
            print(f"  ✅ Export phase completed")
        else:
            print(f"  ❌ Export phase failed: {result.error_message}")
        
        return result.success
    
    async def run_all_tests(self) -> int:
        """Run all E2E tests."""
        print("=" * 60)
        print("SCENEMACHINE E2E PIPELINE TEST")
        print("=" * 60)
        
        # Run all phase tests
        await self.test_parse_phase()
        await self.test_character_phase()
        await self.test_generate_phase()
        await self.test_review_phase()
        await self.test_export_phase()
        
        # Summary
        print("\n" + "=" * 60)
        print("E2E TEST SUMMARY")
        print("=" * 60)
        
        all_passed = True
        for phase, passed in self.results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {phase.upper():15} {status}")
            if not passed:
                all_passed = False
        
        print("=" * 60)
        if all_passed:
            print("🎉 ALL E2E TESTS PASSED!")
            return 0
        else:
            print("⚠️  SOME E2E TESTS FAILED - Review above for details")
            return 1


async def main():
    """Main entry point."""
    test = E2EPipelineTest()
    return await test.run_all_tests()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
