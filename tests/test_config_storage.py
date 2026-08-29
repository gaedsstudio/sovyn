from pathlib import Path

from sovyn.config import PermissionPolicy, load_config, write_default_config
from sovyn.memory import add_memory, forget_memory, list_memory
from sovyn.paths import default_paths
from sovyn.sessions import create_session, list_sessions
from sovyn.storage import Store, trajectory_for_session, record_trajectory
from sovyn.tools import ToolResult
from sovyn.trust import WorkspaceTrust


def test_config_loads_default_when_file_missing(tmp_path: Path) -> None:
    paths = default_paths(home=tmp_path, workspace=tmp_path)

    config = load_config(paths)

    assert config.model.provider == "mock"
    assert config.model.thinking is False
    assert config.permissions.write_files is PermissionPolicy.ASK


def test_config_roundtrip_when_default_written(tmp_path: Path) -> None:
    paths = default_paths(home=tmp_path, workspace=tmp_path)

    write_default_config(paths.config)
    config = load_config(paths)

    assert config.agent.max_steps == 30
    assert config.model.thinking is False
    assert config.ui.animations is True


def test_memory_crud_when_using_sqlite_store(tmp_path: Path) -> None:
    store = Store(tmp_path / "sovyn.db")

    memory_id = add_memory(store, "workspace facts", "pytest is configured")
    before = list_memory(store)
    forget_memory(store, memory_id)

    assert before[0].note == "pytest is configured"
    assert list_memory(store) == ()


def test_sessions_persist_metadata_when_created(tmp_path: Path) -> None:
    store = Store(tmp_path / "sovyn.db")

    session_id = create_session(store, "fix tests", "success", 2, 1.5)
    sessions = list_sessions(store)

    assert sessions[0].id == session_id
    assert sessions[0].tool_calls == 2


def test_workspace_trust_is_stored_locally(tmp_path: Path) -> None:
    trust = WorkspaceTrust(Store(tmp_path / "sovyn.db"))

    trust.trust(tmp_path)

    assert trust.is_trusted(tmp_path) is True


def test_trajectory_is_recorded_for_session(tmp_path: Path) -> None:
    store = Store(tmp_path / "sovyn.db")
    session_id = create_session(store, "inspect", "success", 1, 0.2)

    record_trajectory(store, session_id, (ToolResult("git.status", "1 changed path"),))

    assert trajectory_for_session(store, session_id)[0].name == "git.status"
