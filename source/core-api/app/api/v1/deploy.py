from fastapi import APIRouter, Depends

from app.deps import CurrentUser, DbSession, require_Permission
from app.domains.deploy import service as deploy_service
from app.domains.deploy.schemas import DeployAgentIn, DeployAgentOut
from app.domains.rbac import service as rbac_service
from app.domains.rbac.permissions import PERM_DEPLOY_WRITE

router = APIRouter(prefix="/deploy", tags=["deploy"])


@router.post("/agent", response_model=DeployAgentOut)
def deploy_Agent(
	db: DbSession,
	body: DeployAgentIn,
	operator: CurrentUser = Depends(require_Permission(PERM_DEPLOY_WRITE)),
) -> DeployAgentOut:
	"""Поставить агент на хост ловушки по SSH и вернуть pairing-код."""
	out = deploy_service.install_AgentOverSsh(body)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="deploy.agent",
		resource_type="host",
		resource_id=body.host,
		payload={"user": body.user, "port": body.port},
	)
	return out
