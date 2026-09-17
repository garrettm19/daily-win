from fastapi import APIRouter

from daily_win_api.api.routes import health

api_router = APIRouter()
api_router.include_router(health.router)
