from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] | None = None
    input_type: str = "text"  # "text", "voice", "screenshot", "share", "camera"
    source: str = "shortcuts"  # "shortcuts", "cli", "obsidian", etc.
    model: str | None = None  # Optional model override
    metadata: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    reply: str
    raw: dict[str, Any] | None = None


class VisionRequest(BaseModel):
    description: str
    image_url: str | None = None
    image_base64: str | None = None
    source: str = "shortcuts"
    metadata: dict[str, Any] | None = None


class VisionResponse(BaseModel):
    summary: str
    details: dict[str, Any] | None = None


class TaskRequest(BaseModel):
    type: str = Field(..., alias="task_name")
    args: dict[str, Any] = Field(default_factory=dict, alias="params")
    timeout: int | None = None
    source: str = "shortcuts"
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True)


class TaskResult(BaseModel):
    task: str
    success: bool
    duration_ms: int
    payload: dict[str, Any] | None = None
    error: str | None = None


# Conversation models
class ConversationCreate(BaseModel):
    user_id: str
    title: str | None = None
    source: str = "shortcuts"


class ConversationResponse(BaseModel):
    id: int
    user_id: str
    title: str | None
    source: str
    created_at: str
    updated_at: str
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int
    limit: int
    offset: int


# Dashboard tools models
class DailyEngineeringBriefingRequest(BaseModel):
    """Request model for daily engineering briefing."""
    repo_path: str | None = Field(
        None,
        description="Path to git repository (defaults to current project root)",
    )
    obsidian_path: str | None = Field(
        None,
        description="Optional path to Obsidian vault for recent notes",
    )
    include_fbp_health: bool = Field(
        True,
        description="Whether to include FBP backend health check",
    )


class DailyEngineeringBriefingResponse(BaseModel):
    """Response model for daily engineering briefing."""
    markdown: str = Field(..., description="Markdown-formatted engineering briefing")


# NFA Readiness models
class NFAReadinessResponse(BaseModel):
    """Response model for NFA readiness check."""
    fbp_socket: bool = Field(..., description="Whether FBP socket exists")
    fbp_health: str = Field(..., description="FBP health status: 'ok' or 'error'")
    env_vars: dict[str, bool] = Field(
        ...,
        description="Environment variables check: username, password, cnpj",
    )
    status: str = Field(..., description="Overall status: 'READY' or 'BLOCKED'")


# NFA Trigger models
class NFATriggerRequest(BaseModel):
    """Request model for NFA trigger."""
    cpf: str = Field(..., description="CPF (Brazilian tax ID) - 11 digits")
    test: bool = Field(default=False, description="Test mode flag")


class NFATriggerResponse(BaseModel):
    """Response model for NFA trigger."""
    success: bool = Field(..., description="Whether the NFA trigger was successful")
    message: str = Field(..., description="Human-readable message")
    fbp_response: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw FBP response payload",
    )


# FBP Diagnostics models
class SocketCheck(BaseModel):
    """Socket check result."""
    exists: bool = Field(..., description="Whether socket file exists")
    is_socket: bool = Field(..., description="Whether path is a socket file")
    accessible: bool = Field(..., description="Whether socket has read/write permissions")
    path: str = Field(..., description="Socket file path")


class VersionCheck(BaseModel):
    """Version check result."""
    success: bool = Field(..., description="Whether version check succeeded")
    status: int | None = Field(None, description="HTTP status code")
    version: str | None = Field(None, description="FBP version string")
    machine: str | None = Field(None, description="Machine identifier")
    project: str | None = Field(None, description="Project name")
    data: dict[str, Any] = Field(default_factory=dict, description="Full health response data")
    error: str | None = Field(None, description="Error message if check failed")
    error_type: str | None = Field(None, description="Error type if check failed")


class PingCheck(BaseModel):
    """Ping check result."""
    success: bool = Field(..., description="Whether ping succeeded")
    status: int | None = Field(None, description="HTTP status code")
    response_time_ms: int | None = Field(None, description="Response time in milliseconds")
    data: dict[str, Any] = Field(default_factory=dict, description="Ping response data")
    error: str | None = Field(None, description="Error message if ping failed")
    error_type: str | None = Field(None, description="Error type if ping failed")


class FBPDiagnosticsResponse(BaseModel):
    """Response model for FBP diagnostics."""
    socket_check: SocketCheck = Field(..., description="Socket existence and accessibility check")
    version_check: VersionCheck = Field(..., description="Version/health information check")
    ping_check: PingCheck = Field(..., description="Simple ping task result")
    overall_status: str = Field(..., description="Overall status: 'READY' or 'BLOCKED'")


# NFA ATF Task models
class NFAATFTaskArgs(BaseModel):
    """Request arguments for NFA ATF automation task."""

    from_date: str = Field(..., description="Start date in dd/mm/yyyy format")
    to_date: str = Field(..., description="End date in dd/mm/yyyy format")
    matricula: str = Field(..., description="Matricula number")
    nfa_number: str | None = Field(None, description="Specific NFA number to select (optional)")
    max_nfas: int | None = Field(3, description="Maximum number of NFAs to process (default: 3)")
    download_dar: bool | None = Field(False, description="Also download DAR (emitir taxa servico). Default: only DANFE (imprimir)")
    output_dir: str | None = Field(
        None,
        description="Output directory for PDFs (defaults to /Users/dnigga/Downloads/NFA_Outputs)",
    )
    headless: bool = Field(True, description="Run browser in headless mode")


class NFAATFTaskResult(BaseModel):
    """Result model for NFA ATF automation task."""

    status: str = Field(..., description="Status: 'success' or 'error'")
    nfa_number: str | None = Field(None, description="NFA number processed")
    danfe_path: str | None = Field(None, description="Path to downloaded DANFE PDF")
    dar_path: str | None = Field(None, description="Path to downloaded DAR PDF")
    error_type: str | None = Field(
        None,
        description="Error type if status is 'error': login_failed, filtro_vazio, no_results, download_failure, playwright_exception",
    )
    message: str | None = Field(None, description="Human-readable message or error message")
    context: dict[str, Any] | None = Field(None, description="Additional context or error details")

