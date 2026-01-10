"""LLM Service Module.

Provides AI-powered analysis and generation capabilities using LLM providers.
Supports multiple providers (Anthropic Claude, OpenAI GPT) with automatic fallback.
"""

from scenemachine.services.llm.service import (
    LLMService,
    LLMProvider,
    LLMResponse,
    get_llm_service,
)
from scenemachine.services.llm.prompts import (
    PromptTemplates,
    CopilotPrompts,
)

__all__ = [
    "LLMService",
    "LLMProvider",
    "LLMResponse",
    "get_llm_service",
    "PromptTemplates",
    "CopilotPrompts",
]
