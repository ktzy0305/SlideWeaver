"""Model provider configuration for Strands agents."""

import os
from typing import Any


def get_model(model_id: str | None = None, api_key: str | None = None) -> Any:
    """Get a configured model for Strands agents.

    Checks for available credentials in order:
    1. Provided api_key parameter -> OpenAI
    2. OPENAI_API_KEY env var -> OpenAI
    3. AWS credentials -> Bedrock (default)

    Args:
        model_id: Optional model ID to use. If not specified, uses defaults.
        api_key: Optional OpenAI API key. If not provided, checks env var.

    Returns:
        Configured model instance for Strands Agent
    """
    openai_key = api_key or os.getenv("OPENAI_API_KEY")

    if openai_key:
        # Use OpenAI
        from strands.models.openai import OpenAIModel

        return OpenAIModel(
            client_args={"api_key": openai_key},
            model_id=model_id or "gpt-5-mini",
        )

    # Fall back to Bedrock (requires AWS credentials)
    from strands.models import BedrockModel

    return BedrockModel(
        model_id=model_id or "anthropic.claude-sonnet-4-20250514-v1:0",
    )
