from typing import Protocol

from daily_win_api.ai.exceptions import ModelGatewayConfigurationError
from daily_win_api.ai.providers.openai import OpenAIModelGateway
from daily_win_api.ai.schemas import DailyWinGenerationResult, DailyWinModelContext
from daily_win_api.core.config import Settings, get_settings


class ModelGateway(Protocol):
    def generate_daily_win(
        self, context: DailyWinModelContext
    ) -> DailyWinGenerationResult: ...


def build_model_gateway(settings: Settings | None = None) -> ModelGateway:
    resolved = settings or get_settings()
    provider = resolved.ai_provider.strip().lower()
    if provider != "openai":
        raise ModelGatewayConfigurationError("unsupported_provider")
    if not resolved.openai_configured:
        raise ModelGatewayConfigurationError("not_configured")
    return OpenAIModelGateway(
        api_key=resolved.openai_api_key or "",
        model=resolved.openai_model,
    )
