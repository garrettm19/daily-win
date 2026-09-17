from daily_win_api.ai.exceptions import ModelGatewayConfigurationError
from daily_win_api.ai.gateway import ModelGateway, build_model_gateway
from daily_win_api.api.errors import SanitizedClientError
from daily_win_api.core.config import get_settings
from daily_win_api.domains.daily_wins.schemas import CLIENT_GENERATION_FAILED


def get_model_gateway() -> ModelGateway:
    try:
        return build_model_gateway(get_settings())
    except ModelGatewayConfigurationError:
        raise SanitizedClientError(
            status_code=503,
            detail=CLIENT_GENERATION_FAILED,
            error_code="configuration_error",
        ) from None
