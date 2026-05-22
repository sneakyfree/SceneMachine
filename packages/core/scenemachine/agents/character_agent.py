"""
Character Agent - Character consistency and reference management.

Responsibilities:
- Generate reference images for characters
- Extract face embeddings for consistency
- Select and clone voice profiles
- Monitor character consistency across shots
"""

import logging
from typing import Any
from uuid import UUID

from scenemachine.agents.base import (
    ActionContext,
    ActionResult,
    ActionStatus,
    AgentType,
    BaseAgent,
)

logger = logging.getLogger(__name__)


class CharacterAgent(BaseAgent):
    """
    Agent responsible for character consistency management.

    Autonomous actions:
    - generate_reference: Generate reference image from description
    - extract_embedding: Extract face embedding from reference
    - select_voice: Select voice profile for character
    - check_consistency: Verify character looks consistent

    Requires approval:
    - use_real_likeness: When using real person's likeness
    - clone_voice: When cloning a real person's voice
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.CHARACTER

    @property
    def capabilities(self) -> list[str]:
        return [
            "generate_reference",
            "extract_embedding",
            "select_voice",
            "clone_voice",
            "check_consistency",
            "use_real_likeness",
        ]

    @property
    def requires_approval(self) -> list[str]:
        return ["use_real_likeness", "clone_voice"]

    async def _execute_action(
        self,
        action_name: str,
        context: ActionContext,
        **kwargs,
    ) -> ActionResult:
        """Execute character management actions."""
        if action_name == "generate_reference":
            return await self._generate_reference(context, **kwargs)
        elif action_name == "extract_embedding":
            return await self._extract_embedding(context, **kwargs)
        elif action_name == "select_voice":
            return await self._select_voice(context, **kwargs)
        elif action_name == "check_consistency":
            return await self._check_consistency(context, **kwargs)
        else:
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=f"Unknown action: {action_name}",
            )

    async def _generate_reference(
        self,
        context: ActionContext,
        character_name: str,
        description: str,
        style: str = "realistic",
    ) -> ActionResult:
        """Generate a reference image for a character."""
        try:
            from scenemachine.services.character_image_generator import (
                CharacterImageGenerator,
            )

            generator = CharacterImageGenerator()
            result = await generator.generate(
                name=character_name,
                description=description,
                style=style,
            )

            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED,
                success=result.success,
                output={
                    "image_path": result.image_path,
                    "thumbnail_path": result.thumbnail_path,
                },
                confidence=0.85,
                cost_usd=result.cost_usd or 0.0,
            )
        except Exception as e:
            logger.exception(f"Reference generation failed: {e}")
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=str(e),
            )

    async def _extract_embedding(
        self,
        context: ActionContext,
        image_path: str,
    ) -> ActionResult:
        """Extract face embedding from a reference image."""
        try:
            from scenemachine.services.face_embedding import FaceEmbeddingService

            service = FaceEmbeddingService()
            embedding = await service.extract(image_path)

            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED,
                success=embedding is not None,
                output={
                    "embedding": embedding.tolist() if embedding is not None else None,
                    "embedding_dim": len(embedding) if embedding is not None else 0,
                },
                confidence=0.9 if embedding is not None else 0.3,
            )
        except Exception as e:
            logger.exception(f"Embedding extraction failed: {e}")
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=str(e),
            )

    async def _select_voice(
        self,
        context: ActionContext,
        character_description: str,
        gender: str = "neutral",
    ) -> ActionResult:
        """Select an appropriate voice profile for a character."""
        from scenemachine.services.audio import MockTTSProvider

        provider = MockTTSProvider()
        voices = await provider.get_voices()

        # Filter by gender
        matching = [v for v in voices if gender == "neutral" or v.gender.value == gender]

        if not matching:
            matching = voices

        # Return first match (would use LLM for better selection in production)
        selected = matching[0] if matching else None

        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=selected is not None,
            output={
                "voice_id": selected.id if selected else None,
                "voice_name": selected.name if selected else None,
                "available_count": len(voices),
            },
            confidence=0.7,  # Heuristic selection
        )

    async def _check_consistency(
        self,
        context: ActionContext,
        character_id: UUID,
        shot_paths: list[str],
    ) -> ActionResult:
        """Check character consistency across multiple shots."""
        # This would use face embedding similarity in production
        # For now, return a mock result

        consistency_scores = []
        for path in shot_paths:
            # Mock: random-ish score based on path hash
            score = 0.7 + (hash(path) % 30) / 100
            consistency_scores.append(
                {
                    "path": path,
                    "score": min(score, 1.0),
                }
            )

        avg_score = (
            sum(s["score"] for s in consistency_scores) / len(consistency_scores)
            if consistency_scores
            else 0
        )

        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={
                "character_id": str(character_id),
                "shot_count": len(shot_paths),
                "average_consistency": avg_score,
                "scores": consistency_scores,
                "is_consistent": avg_score >= 0.8,
            },
            confidence=0.75,
        )

    # ============================================================
    # S-P2-01: Parallel Processing Enhancement
    # ============================================================

    # Concurrency settings
    MAX_CONCURRENT_GENERATIONS = 4  # Max simultaneous image generations
    MAX_CONCURRENT_EMBEDDINGS = 8  # Max simultaneous embedding extractions
    BATCH_SIZE = 10  # Characters per batch

    async def process_characters_parallel(
        self,
        context: ActionContext,
        characters: list[dict[str, Any]],
        actions: list[str] = None,
    ) -> dict[str, Any]:
        """Process multiple characters in parallel.

        S-P2-01: Enables concurrent processing of characters for:
        - Faster project initialization
        - Efficient batch operations
        - Resource-aware concurrency control

        Args:
            context: Action context
            characters: List of character dicts with name, description, etc.
            actions: Actions to perform ['generate_reference', 'extract_embedding', 'select_voice']

        Returns:
            Aggregated results for all characters
        """
        import time

        if actions is None:
            actions = ["generate_reference", "extract_embedding", "select_voice"]

        start_time = time.time()
        results = {
            "total_characters": len(characters),
            "successful": 0,
            "failed": 0,
            "character_results": [],
            "actions_performed": actions,
        }

        # Process in batches to avoid overwhelming resources
        for batch_start in range(0, len(characters), self.BATCH_SIZE):
            batch = characters[batch_start : batch_start + self.BATCH_SIZE]
            batch_results = await self._process_batch(context, batch, actions)

            for char_result in batch_results:
                results["character_results"].append(char_result)
                if char_result.get("success"):
                    results["successful"] += 1
                else:
                    results["failed"] += 1

        results["processing_time_seconds"] = time.time() - start_time
        results["characters_per_second"] = (
            len(characters) / results["processing_time_seconds"]
            if results["processing_time_seconds"] > 0
            else 0
        )

        logger.info(
            f"Parallel processing complete: {results['successful']}/{len(characters)} "
            f"characters in {results['processing_time_seconds']:.2f}s"
        )

        return results

    async def _process_batch(
        self,
        context: ActionContext,
        batch: list[dict[str, Any]],
        actions: list[str],
    ) -> list[dict[str, Any]]:
        """Process a batch of characters concurrently."""
        import asyncio

        # Create semaphore for controlled concurrency
        generation_sem = asyncio.Semaphore(self.MAX_CONCURRENT_GENERATIONS)

        async def process_single_character(character: dict[str, Any]) -> dict[str, Any]:
            """Process a single character through all requested actions."""
            char_result = {
                "character_name": character.get("name", "Unknown"),
                "success": True,
                "actions": {},
            }

            try:
                # Generate reference image
                if "generate_reference" in actions:
                    async with generation_sem:
                        result = await self._generate_reference(
                            context,
                            character_name=character.get("name", "Character"),
                            description=character.get("description", ""),
                            style=character.get("style", "realistic"),
                        )
                        char_result["actions"]["generate_reference"] = {
                            "success": result.success,
                            "output": result.output,
                        }
                        if not result.success:
                            char_result["success"] = False

                # Extract embedding (can run with higher concurrency)
                if "extract_embedding" in actions and char_result["actions"].get(
                    "generate_reference", {}
                ).get("success"):
                    image_path = char_result["actions"]["generate_reference"]["output"].get(
                        "image_path"
                    )
                    if image_path:
                        result = await self._extract_embedding(context, image_path)
                        char_result["actions"]["extract_embedding"] = {
                            "success": result.success,
                            "has_embedding": result.output.get("embedding") is not None
                            if result.output
                            else False,
                        }

                # Select voice (lightweight, no limit needed)
                if "select_voice" in actions:
                    result = await self._select_voice(
                        context,
                        character_description=character.get("description", ""),
                        gender=character.get("gender", "neutral"),
                    )
                    char_result["actions"]["select_voice"] = {
                        "success": result.success,
                        "voice_id": result.output.get("voice_id") if result.output else None,
                    }

            except Exception as e:
                logger.warning(f"Character processing failed: {character.get('name')}: {e}")
                char_result["success"] = False
                char_result["error"] = str(e)

            return char_result

        # Run all characters in batch concurrently
        tasks = [process_single_character(char) for char in batch]
        return await asyncio.gather(*tasks)

    async def batch_extract_embeddings(
        self,
        context: ActionContext,
        image_paths: list[str],
    ) -> dict[str, Any]:
        """Extract embeddings from multiple images in parallel.

        Optimized for batch face embedding extraction with
        controlled concurrency to avoid GPU memory issues.

        Args:
            context: Action context
            image_paths: List of image file paths

        Returns:
            Batch extraction results
        """
        import asyncio
        import time

        start_time = time.time()
        sem = asyncio.Semaphore(self.MAX_CONCURRENT_EMBEDDINGS)

        async def extract_one(path: str) -> dict[str, Any]:
            async with sem:
                result = await self._extract_embedding(context, path)
                return {
                    "path": path,
                    "success": result.success,
                    "has_embedding": result.output.get("embedding") is not None
                    if result.output
                    else False,
                    "confidence": result.confidence,
                }

        tasks = [extract_one(path) for path in image_paths]
        extraction_results = await asyncio.gather(*tasks)

        successful = sum(1 for r in extraction_results if r["success"])

        return {
            "total_images": len(image_paths),
            "successful_extractions": successful,
            "failed_extractions": len(image_paths) - successful,
            "results": extraction_results,
            "processing_time_seconds": time.time() - start_time,
        }

    async def parallel_consistency_check(
        self,
        context: ActionContext,
        character_shot_map: dict[UUID, list[str]],
    ) -> dict[str, Any]:
        """Check consistency for multiple characters in parallel.

        Args:
            context: Action context
            character_shot_map: {character_id: [shot_paths]}

        Returns:
            Parallel consistency check results
        """
        import asyncio
        import time

        start_time = time.time()

        async def check_one(char_id: UUID, paths: list[str]) -> dict[str, Any]:
            result = await self._check_consistency(context, char_id, paths)
            return {
                "character_id": str(char_id),
                "result": result.output,
                "success": result.success,
            }

        tasks = [check_one(char_id, paths) for char_id, paths in character_shot_map.items()]

        check_results = await asyncio.gather(*tasks)

        # Aggregate stats
        consistent_count = sum(
            1 for r in check_results if r.get("result", {}).get("is_consistent", False)
        )

        return {
            "total_characters": len(character_shot_map),
            "consistent_characters": consistent_count,
            "inconsistent_characters": len(character_shot_map) - consistent_count,
            "results": check_results,
            "processing_time_seconds": time.time() - start_time,
        }
