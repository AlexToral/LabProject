from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Verificar disponibilidad del backend."""
    return {"status": "ok"}
