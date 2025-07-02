import pytest
from mcp_scheduler.config import Config
from mcp_scheduler.executor import Executor
from mcp_scheduler.persistence import Database
from mcp_scheduler.scheduler import Scheduler
from mcp_scheduler.task import Task, TaskType
import tempfile
import os
import asyncio


@pytest.fixture
def temp_db():
    db_file = tempfile.NamedTemporaryFile(delete=False)
    db_file.close()
    yield db_file.name
    os.unlink(db_file.name)


@pytest.mark.asyncio
async def test_scheduler_add_and_list_tasks(temp_db):
    config = Config()
    db = Database(temp_db)
    executor = Executor(None, config.ai_model)
    scheduler = Scheduler(db, executor)
    await scheduler.start()

    task = Task(
        name="Test", schedule="* * * * *", type=TaskType.SHELL_COMMAND, command="echo hi"
    )
    await scheduler.add_task(task)
    tasks = await scheduler.get_all_tasks()
    assert any(t.name == "Test" for t in tasks)

    await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_run_task_now(temp_db):
    config = Config()
    db = Database(temp_db)
    executor = Executor(None, config.ai_model)
    scheduler = Scheduler(db, executor)
    await scheduler.start()

    task = Task(
        name="Test2", schedule="* * * * *", type=TaskType.SHELL_COMMAND, command="echo hi"
    )
    t = await scheduler.add_task(task)
    execution = await scheduler.run_task_now(t.id)
    assert execution is not None

    await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_enable_disable_task(temp_db):
    config = Config()
    db = Database(temp_db)
    executor = Executor(None, config.ai_model)
    scheduler = Scheduler(db, executor)
    await scheduler.start()

    task = Task(
        name="Test3", schedule="* * * * *", type=TaskType.SHELL_COMMAND, command="echo hi"
    )
    t = await scheduler.add_task(task)
    await scheduler.disable_task(t.id)
    t2 = await scheduler.get_task(t.id)
    assert not t2.enabled
    await scheduler.enable_task(t.id)
    t3 = await scheduler.get_task(t.id)
    assert t3.enabled

    await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_remove_task(temp_db):
    config = Config()
    db = Database(temp_db)
    executor = Executor(None, config.ai_model)
    scheduler = Scheduler(db, executor)
    await scheduler.start()

    task = Task(
        name="Test4", schedule="* * * * *", type=TaskType.SHELL_COMMAND, command="echo hi"
    )
    t = await scheduler.add_task(task)
    await scheduler.delete_task(t.id)
    t2 = await scheduler.get_task(t.id)
    assert t2 is None

    await scheduler.stop()


# ---------------------------------------------------------------------------
# NEW test for TOOL_CALL task type
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scheduler_tool_call(temp_db, monkeypatch):
    """Ensure TOOL_CALL tasks invoke an MCP tool without network dependency."""

    # --- Monkey-patch MCP client so the test stays offline ---------------------------------
    from mcp_scheduler.executors import tool_call as tc_exec

    def fake_invoke(tool, method, params):
        assert tool == "meta-ads-mcp"
        assert method == "ping"
        return {"pong": True}

    monkeypatch.setattr(tc_exec.client, "invoke", fake_invoke)

    # --- Set up scheduler -----------------------------------------------------------------
    config = Config()
    db = Database(temp_db)
    executor = Executor(None, config.ai_model)
    scheduler = Scheduler(db, executor)
    await scheduler.start()

    # Create the TOOL_CALL task
    task = Task(
        name="Ping MCP",
        schedule="@once",
        type=TaskType.TOOL_CALL,
        tool="meta-ads-mcp",
        method="ping",
        params={},
    )

    t = await scheduler.add_task(task)
    execution = await scheduler.run_task_now(t.id)

    assert execution is not None
    assert execution.status == "success"
    assert "pong" in (execution.output or "").lower()

    await scheduler.stop()
