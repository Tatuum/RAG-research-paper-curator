from fastapi import APIRouter
from src.schemas.api.health import HealthResponse

router = APIRouter(
    prefix="/health",
    tags=["health"],
)

@router.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "healthy", "version": "1.0.0", "environment": "development", "service_name": "database"}
