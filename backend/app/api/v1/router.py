from fastapi import APIRouter
from pydantic import BaseModel

from app.api.v1.candidates import router as candidates_router
from app.api.v1.connectors import router as connectors_router

router = APIRouter()


class HealthResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


router.include_router(candidates_router)
router.include_router(connectors_router)
