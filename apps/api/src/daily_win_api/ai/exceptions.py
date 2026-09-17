from daily_win_api.ai.error_codes import sanitize_error_code


class ModelGatewayError(Exception):
    """Provider-boundary failure. Do not include child narrative or provider text."""

    def __init__(self, code: str = "provider_error") -> None:
        self.code = sanitize_error_code(code)
        super().__init__(self.code)


class ModelGatewayConfigurationError(ModelGatewayError):
    """Missing or invalid provider configuration."""

    def __init__(self, code: str = "configuration_error") -> None:
        super().__init__(code)


class ModelGatewaySchemaError(ModelGatewayError):
    """Structured output was missing or could not be parsed."""

    def __init__(self, code: str = "schema_validation_failed") -> None:
        super().__init__(code)
