"""
Task model implementation for MCP Scheduler with TOOL_CALL support.
"""
from __future__ import annotations

import uuid
import re
from datetime import datetime
from enum import Enum
from typing import Literal, Optional, List, Dict, Any

from pydantic import BaseModel, Field, validator


class TaskStatus(str, Enum):
    """Status of a scheduled task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


class TaskType(str, Enum):
    """Type of a scheduled task."""
    SHELL_COMMAND = "shell_command"
    API_CALL = "api_call"
    AI = "ai"
    REMINDER = "reminder"  # reminder notification
    TOOL_CALL = "tool_call"  # NEW – invoke arbitrary MCP tool


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def sanitize_ascii(text: str) -> str:
    """Strips non‑ASCII characters from a string."""
    if not text:
        return text
    return re.sub(r"[^\x00-\x7F]+", "", text)


# ---------------------------------------------------------------------------
# Core Task data model
# ---------------------------------------------------------------------------

class Task(BaseModel):
    """Model representing a scheduled task."""

    # —— core metadata ——
    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    name: str
    schedule: str
    type: TaskType = TaskType.SHELL_COMMAND

    # —— shell_command fields ——
    command: Optional[str] = None

    # —— api_call fields ——
    api_url: Optional[str] = None
    api_method: Optional[str] = None
    api_headers: Optional[Dict[str, str]] = None
    api_body: Optional[Dict[str, Any]] = None

    # —— AI fields ——
    prompt: Optional[str] = None

    # —— TOOL_CALL fields ——
    tool: Optional[str] = None  # MCP tool name, e.g. "meta-ads-mcp"
    method: Optional[str] = None  # MCP method name, e.g. "mcp_meta_ads_get_insights"
    params: Optional[Dict[str, Any]] = None  # kwargs for the call

    # —— reminder fields ——
    reminder_title: Optional[str] = None
    reminder_message: Optional[str] = None

    # —— misc ——
    description: Optional[str] = None
    enabled: bool = True
    do_only_once: bool = True  # default: run a single time unless rescheduled
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @validator(
        "name",
        "command",
        "prompt",
        "description",
        "reminder_title",
        "reminder_message",
        pre=True,
    )
    def _ascii_only(cls, v):
        return sanitize_ascii(v) if isinstance(v, str) else v

    @validator("command")
    def _require_command(cls, v, values):
        if values.get("type") == TaskType.SHELL_COMMAND and not v:
            raise ValueError("Command is required for shell_command tasks")
        return v

    @validator("api_url")
    def _require_api_url(cls, v, values):
        if values.get("type") == TaskType.API_CALL and not v:
            raise ValueError("API URL is required for api_call tasks")
        return v

    @validator("prompt")
    def _require_prompt(cls, v, values):
        if values.get("type") == TaskType.AI and not v:
            raise ValueError("Prompt is required for AI tasks")
        return v

    @validator("reminder_message")
    def _require_reminder_msg(cls, v, values):
        if values.get("type") == TaskType.REMINDER and not v:
            raise ValueError("Message is required for reminder tasks")
        return v

    @validator("tool", "method")
    def _require_tool_fields(cls, v, values, field):
        if values.get("type") == TaskType.TOOL_CALL and not v:
            raise ValueError(f"{field.name.capitalize()} is required for tool_call tasks")
        return v

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a serialisable dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "schedule": self.schedule,
            "type": self.type.value,
            "command": self.command,
            "api_url": self.api_url,
            "api_method": self.api_method,
            "api_headers": self.api_headers,
            "api_body": self.api_body,
            "prompt": self.prompt,
            "tool": self.tool,
            "method": self.method,
            "params": self.params,
            "description": self.description,
            "enabled": self.enabled,
            "do_only_once": self.do_only_once,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "reminder_title": self.reminder_title,
            "reminder_message": self.reminder_message,
        }


# ---------------------------------------------------------------------------
# Execution record model (unchanged)
# ---------------------------------------------------------------------------

class TaskExecution(BaseModel):
    """Model representing a task execution."""

    id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:12]}")
    task_id: str
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    status: TaskStatus = TaskStatus.RUNNING
    output: Optional[str] = None
    error: Optional[str] = None

    @validator("output", "error", pre=True)
    def _ascii_output(cls, v):
        return sanitize_ascii(v) if isinstance(v, str) else v

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
        }
