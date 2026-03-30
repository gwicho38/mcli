import os
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

from mcli.workflow.daemon.daemon import DaemonService

MCLI_DAEMON_API_KEY = os.environ.get("MCLI_DAEMON_API_KEY", "")


async def verify_api_key(x_api_key: str = Header(default="")):
    """Verify API key for daemon endpoints."""
    if not MCLI_DAEMON_API_KEY:
        return  # No key configured = local-only mode (no auth required)
    if x_api_key != MCLI_DAEMON_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


app = FastAPI(title="MCLI Daemon API")
service = DaemonService()


class CommandOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    language: str
    group: Optional[str]
    tags: List[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    execution_count: int
    last_executed: Optional[str]
    is_active: bool


class ExecuteRequest(BaseModel):
    command_name: str
    args: Optional[List[str]] = []


@app.get("/commands", response_model=List[CommandOut])
def list_commands(all: bool = Query(False, description="Show all commands, including inactive")):
    commands = service.db.get_all_commands(include_inactive=all)
    return [
        CommandOut(
            id=cmd.id,
            name=cmd.name,
            description=cmd.description,
            language=cmd.language,
            group=cmd.group,
            tags=cmd.tags,
            created_at=cmd.created_at.isoformat() if cmd.created_at else None,
            updated_at=cmd.updated_at.isoformat() if cmd.updated_at else None,
            execution_count=cmd.execution_count,
            last_executed=cmd.last_executed.isoformat() if cmd.last_executed else None,
            is_active=cmd.is_active,
        )
        for cmd in commands
    ]


@app.post("/execute")
def execute_command(req: ExecuteRequest, _=Depends(verify_api_key)):
    commands = service.db.get_all_commands()
    cmd = next((c for c in commands if c.name == req.command_name), None)
    if not cmd:
        raise HTTPException(status_code=404, detail=f"Command '{req.command_name}' not found.")
    result = service.executor.execute_command(cmd, req.args or [])
    return result
