import os, logging, json
from fastmcp import MCPClient
from mcp_scheduler.models import Task

# Base URL for relative tool references; leave blank if every task
# passes a full URL (e.g. https://mcp.pipeboard.co/meta-ads-mcp)
BASE = os.getenv("MCP_BASE_URL", "")

# One client instance is fine; transport="sse" keeps Claude happy
client = MCPClient(BASE, transport="sse")


def execute(task: Task) -> dict:
    """
    Execute a TOOL_CALL task by invoking the specified MCP tool & method.
    """
    try:
        logging.info("Tool-call %s.%s", task.tool, task.method)
        result = client.invoke(
            tool=task.tool,
            method=task.method,
            params=task.params or {},
        )
        # Serialise result to a compact JSON string for logs / DB
        return {"status": "success", "data": json.dumps(result)}
    except Exception as exc:
        logging.exception("Tool-call failed")
        return {"status": "error", "error": str(exc)}
