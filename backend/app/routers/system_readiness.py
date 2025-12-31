"""System readiness router for NFA and other system checks."""

from __future__ import annotations

from fastapi import APIRouter

from app.models import NFAReadinessResponse
from app.services import nfa_readiness
from app.services.logging_utils import get_logger

router = APIRouter(prefix="/system", tags=["system"])
logger = get_logger(__name__)


@router.get("/nfa-readiness", response_model=NFAReadinessResponse)
async def get_nfa_readiness() -> NFAReadinessResponse:
    """
    Check NFA system readiness.

    Verifies:
    - FBP socket exists at /tmp/fbp.sock
    - FBP health endpoint is reachable (1 second timeout)
    - Required environment variables are set:
      - NFA_USERNAME
      - NFA_PASSWORD
      - NFA_EMITENTE_CNPJ

    Returns:
        NFAReadinessResponse with readiness status:
        - fbp_socket: Whether socket exists
        - fbp_health: "ok" or "error"
        - env_vars: Dictionary with username, password, cnpj (bool each)
        - status: "READY" or "BLOCKED"
    """
    logger.info("NFA readiness check requested")
    result = await nfa_readiness.check_nfa_readiness()
    return NFAReadinessResponse(**result)
