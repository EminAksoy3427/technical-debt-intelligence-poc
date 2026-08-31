from fastapi import APIRouter
from pydantic import BaseModel

from app.api.v1.candidates import router as candidates_router

router = APIRouter()


class HealthResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


router.include_router(candidates_router)
