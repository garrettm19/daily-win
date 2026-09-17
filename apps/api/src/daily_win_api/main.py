from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from daily_win_api.api.errors import SanitizedClientError, sanitized_error_response
from daily_win_api.api.router import api_router
from daily_win_api.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    application = FastAPI(title="Daily Win API")
    application.include_router(api_router)

    @application.exception_handler(SanitizedClientError)
    async def handle_sanitized_client_error(
        _request: Request, exc: SanitizedClientError
    ) -> JSONResponse:
        return sanitized_error_response(
            status_code=exc.status_code,
            detail=exc.detail,
            error_code=exc.error_code,
            include_error_code=resolved.demo_routes_enabled,
        )

    if resolved.demo_routes_enabled:
        from daily_win_api.api.v1.demo import router as demo_router

        application.include_router(demo_router)
        # Local Expo/LAN access only. This middleware applies to the whole
        # development app, not solely the demo router.
        application.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
    return application


app = create_app()