"""
Pydantic schemas for Telegram Bot ACP integration.

These schemas define the data structures used for ACP interactions
in the Telegram bot context. They provide a simplified interface
on top of the core ACP protocol models.
"""

from typing import Optional
from pydantic import BaseModel, Field


class TGAgentListItem(BaseModel):
    """Schema for an agent item displayed in Telegram messages."""
    name: str = Field(..., description="Agent identifier/name")
    description: str = Field(default="No description", description="Agent description")


class TGAgentInvocationRequest(BaseModel):
    """Schema for agent invocation from Telegram."""
    agent_name: str = Field(..., description="Name of the agent to invoke")
    message: str = Field(..., description="User message to send to agent")
    user_id: int = Field(..., description="Telegram user ID for session tracking")
    session_id: Optional[str] = Field(default=None, description="Optional explicit session ID")

    def get_session_id(self) -> str:
        """Get or generate session ID from user ID."""
        return self.session_id or f"tg_user_{self.user_id}"


class TGAgentInvocationResponse(BaseModel):
    """Schema for agent invocation response in Telegram."""
    status: str = Field(..., description="Run status (completed, failed, etc.)")
    output: str = Field(..., description="Agent response text")
    run_id: Optional[str] = Field(default=None, description="Unique run identifier")
    truncated: bool = Field(default=False, description="Whether output was truncated for TG")


class TGACPServerStatus(BaseModel):
    """Schema for ACP server status displayed in Telegram."""
    available: bool = Field(..., description="Whether the server is reachable")
    url: str = Field(..., description="ACP server URL")
    agent_count: Optional[int] = Field(default=None, description="Number of available agents")
    timeout: int = Field(..., description="Request timeout in seconds")
