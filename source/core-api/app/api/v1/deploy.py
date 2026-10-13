from fastapi import APIRouter

from app.deps import Operator
from app.domains.deploy import service as deploy_service
from app.domains.deploy.schemas import DeployAgentIn, DeployAgentOut

router = APIRouter(prefix="/deploy", tags=["deploy"])


@router.post("/agent", response_model=DeployAgentOut)
def deploy_Agent(_operator: Operator, body: DeployAgentIn) -> DeployAgentOut:
	"""Поставить агент на хост ловушки по SSH и вернуть pairing-код."""
	return deploy_service.install_AgentOverSsh(body)
