from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from threading import Event, Thread
from time import sleep

import pytest

from sovyn.agent import AgentResult, AgentRuntime, RunStatus, run_agent
from sovyn.config import DEFAULT_CONFIG, InterfaceLanguage, load_config
from sovyn.interaction import Approval, Interaction
from sovyn.link.bridge import TelegramBridge, TelegramPrompter, load_telegram_settings
from sovyn.link.telegram import (
    ChatKind,
    TelegramBot,
    TelegramCallback,
    TelegramChat,
    TelegramConfigError,
    TelegramError,
    TelegramMessage,
    TelegramUpdate,
    TelegramUser,
    parse_allowed_users,
)
from sovyn.paths import default_paths
from sovyn.permissions import ActionKind, PermissionRequest
from sovyn.provider_init import ProviderResolution, ProviderStatus
from sovyn.providers import MockProvider
from sovyn.runtime import AppRuntime
from sovyn.storage import Store
from sovyn.trust import WorkspaceTrust
from sovyn.ui import Renderer


@dataclass(slots=True)
class SentMessage:
    chat_id: int
    text: str
    buttons: tuple = ()


@dataclass(slots=True)
class FakeTelegramClient:
    sent: list[SentMessage] = field(default_factory=list)
    answered: list[tuple[str, str]] = field(default_factory=list)
    updates: list[tuple[TelegramUpdate, ...] | TelegramError | KeyboardInterrupt] = field(default_factory=list)
    offsets: list[int | None] = field(default_factory=list)
    closed: bool = False

    def get_updates(self, offset: int | None, timeout: int) -> tuple[TelegramUpdate, ...]:
        self.offsets.append(offset)
        item = self.updates.pop(0)
        match item:
            case TelegramError():
                raise item
            case KeyboardInterrupt():
                raise item
            case tuple():
                return item
            case unreachable:
                raise AssertionError(f"unexpected fake update item: {unreachable}")

    def send_message(self, chat_id: int, text: str, buttons: tuple = ()) -> None:
        self.sent.append(SentMessage(chat_id, text, buttons))

    def answer_callback_query(self, callback_id: str, text: str = "") -> None:
        self.answered.append((callback_id, text))

    def close(self) -> None:
        self.closed = True


@dataclass(slots=True)
class RunnerProbe:
    result: AgentResult
    calls: list[str] = field(default_factory=list)
    started: Event = field(default_factory=Event)
    release: Event = field(default_factory=Event)
    block: bool = False

    def __call__(self, request: str, runtime: AgentRuntime) -> AgentResult:
        self.calls.append(request)
        self.started.set()
        if self.block:
            self.release.wait()
        return self.result


def test_missing_token_reports_clear_startup_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SOVYN_TELEGRAM_TOKEN", raising=False)

    with pytest.raises(TelegramConfigError, match="SOVYN_TELEGRAM_TOKEN"):
        load_telegram_settings(tmp_path, 30, False)


def test_invalid_allowed_user_parsing() -> None:
    with pytest.raises(TelegramConfigError):
        parse_allowed_users("123,abc")


def test_whoami_works_without_agent_when_locked(tmp_path: Path) -> None:
    bridge, runner, client = _bridge(tmp_path, allowed_users=())

    bridge.handle_update(_message_update("/whoami", user_id=123))

    assert runner.calls == []
    assert client.sent[-1].text == "Your Telegram user ID: 123"


def test_unauthorized_user_never_reaches_agent(tmp_path: Path) -> None:
    bridge, runner, client = _bridge(tmp_path, allowed_users=(123,))

    bridge.handle_update(_message_update("README.md 읽어줘", user_id=999))

    assert runner.calls == []
    assert client.sent[-1].text == "Unauthorized."


def test_group_message_is_ignored(tmp_path: Path) -> None:
    bridge, runner, client = _bridge(tmp_path, allowed_users=(123,))

    bridge.handle_update(_message_update("run this", user_id=123, chat_kind=ChatKind.GROUP))

    assert runner.calls == []
    assert client.sent == []


def test_authorized_normal_dm_invokes_agent_once(tmp_path: Path) -> None:
    bridge, runner, client = _bridge(tmp_path, allowed_users=(123,))

    bridge.handle_update(_message_update("README.md 읽어줘", user_id=123))
    assert bridge.wait_for_idle()

    assert runner.calls == ["README.md 읽어줘"]
    assert client.sent[-1].text == "ok"


def test_status_and_model_do_not_call_agent(tmp_path: Path) -> None:
    bridge, runner, client = _bridge(tmp_path, allowed_users=(123,))

    bridge.handle_update(_message_update("/status", user_id=123))
    bridge.handle_update(_message_update("/model", user_id=123))

    assert runner.calls == []
    assert "Provider: ready" in client.sent[-2].text
    assert client.sent[-1].text == "mock/mock-local"


def test_agent_failure_states_are_honest(tmp_path: Path) -> None:
    stalled, _, stalled_client = _bridge(tmp_path, allowed_users=(123,), status=RunStatus.STALLED)
    provider_error, _, provider_client = _bridge(tmp_path, allowed_users=(123,), status=RunStatus.PROVIDER_ERROR)

    stalled.handle_update(_message_update("stall", user_id=123))
    provider_error.handle_update(_message_update("provider", user_id=123))
    assert stalled.wait_for_idle()
    assert provider_error.wait_for_idle()

    assert stalled_client.sent[-1].text == "SOVYN couldn't complete this task reliably.\nStatus: stalled"
    assert provider_client.sent[-1].text == "SOVYN provider is unavailable."


def test_permission_allow_once_and_deny_map_to_existing_approvals() -> None:
    allow_client = FakeTelegramClient()
    deny_client = FakeTelegramClient()
    allow = TelegramPrompter(allow_client, 123, 1)
    deny = TelegramPrompter(deny_client, 123, 1)
    request = PermissionRequest(ActionKind.WRITE_FILES, "Create or modify hello.txt")

    allow_result = _resolve_permission(allow, allow_client, request, "y")
    deny_result = _resolve_permission(deny, deny_client, request, "n")

    assert allow_result is Approval.ONCE
    assert deny_result is Approval.DENY


def test_unauthorized_and_stale_callbacks_cannot_approve(tmp_path: Path) -> None:
    bridge, _, client = _bridge(tmp_path, allowed_users=(123,), real_agent=True)
    bridge.handle_update(_message_update("create a file called hello.txt containing hello", user_id=123))
    _wait_for_button(client)
    callback_data = client.sent[-1].buttons[0][0].callback_data

    bridge.handle_update(_callback_update(callback_data, user_id=999, callback_id="bad"))
    bridge.handle_update(_callback_update(callback_data, user_id=123, callback_id="good"))
    assert bridge.wait_for_idle()
    bridge.handle_update(_callback_update(callback_data, user_id=123, callback_id="stale"))

    assert ("bad", "not authorized") in client.answered
    assert ("good", "received") in client.answered
    assert ("stale", "approval expired") in client.answered


def test_no_op_write_does_not_create_second_remote_permission(tmp_path: Path) -> None:
    bridge, _, client = _bridge(tmp_path, allowed_users=(123,), real_agent=True)
    task = "create a file called hello.txt containing hello"

    bridge.handle_update(_message_update(task, user_id=123))
    _wait_for_button(client)
    bridge.handle_update(_callback_update(client.sent[-1].buttons[0][0].callback_data, user_id=123))
    assert bridge.wait_for_idle()
    first_prompt_count = _permission_prompt_count(client)

    bridge.handle_update(_message_update(task, user_id=123))
    assert bridge.wait_for_idle()

    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert first_prompt_count == 1
    assert _permission_prompt_count(client) == 1


def test_destructive_remote_permission_is_denied() -> None:
    client = FakeTelegramClient()
    prompter = TelegramPrompter(client, 123, 1)

    result = prompter.request_permission(
        PermissionRequest(ActionKind.DELETE_FILES, "Delete file", destructive=True),
        None,
        allow_task=True,
    )

    assert result is not None
    assert client.sent[-1].text == "This action requires local confirmation."


def test_concurrent_second_task_is_rejected(tmp_path: Path) -> None:
    result = _agent_result(RunStatus.SUCCESS)
    runner = RunnerProbe(result, block=True)
    bridge, _, client = _bridge(tmp_path, allowed_users=(123,), runner=runner)

    bridge.handle_update(_message_update("first", user_id=123))
    assert runner.started.wait(2)
    bridge.handle_update(_message_update("second", user_id=123))
    runner.release.set()
    assert bridge.wait_for_idle()

    assert runner.calls == ["first"]
    assert client.sent[-1].text == "ok"
    assert any(item.text == "SOVYN is currently working on another task." for item in client.sent)


def test_long_response_is_chunked_by_client() -> None:
    from sovyn.link.telegram import chunk_text

    chunks = chunk_text("한글" * 2500, limit=1000)

    assert len(chunks) > 1
    assert all(len(chunk) <= 1000 for chunk in chunks)


def test_polling_offset_prevents_reprocessing(tmp_path: Path) -> None:
    bridge, _, client = _bridge(tmp_path, allowed_users=(123,))
    client.updates = [(_message_update("/model", update_id=10, user_id=123),), KeyboardInterrupt()]

    bridge.run_forever()

    assert client.offsets == [None, 11]
    assert client.closed is True


def test_transient_telegram_failure_retries_without_crashing(tmp_path: Path) -> None:
    bridge, _, client = _bridge(tmp_path, allowed_users=(123,))
    client.updates = [TelegramError("temporary"), KeyboardInterrupt()]

    bridge.run_forever()

    assert client.offsets == [None, None]
    assert client.closed is True


def test_workspace_command_reports_current_workspace(tmp_path: Path) -> None:
    bridge, _, client = _bridge(tmp_path, allowed_users=(123,))

    bridge.handle_update(_message_update("/workspace", user_id=123))

    assert client.sent[-1].text == str(tmp_path)


def test_language_command_and_callback_do_not_call_agent(tmp_path: Path) -> None:
    bridge, runner, client = _bridge(tmp_path, allowed_users=(123,))

    bridge.handle_update(_message_update("/language", user_id=123))
    bridge.handle_update(_callback_update("sovyn:lang:ko", user_id=123, callback_id="lang"))

    assert runner.calls == []
    assert client.answered[-1] == ("lang", "language updated")
    assert load_config(bridge.runtime.paths).interface.language is InterfaceLanguage.KO


def _bridge(
    tmp_path: Path,
    *,
    allowed_users: tuple[int, ...],
    status: RunStatus = RunStatus.SUCCESS,
    runner: RunnerProbe | None = None,
    real_agent: bool = False,
) -> tuple[TelegramBridge, RunnerProbe, FakeTelegramClient]:
    paths = default_paths(home=tmp_path / "home", workspace=tmp_path)
    paths.ensure()
    store = Store(paths.database)
    trust = WorkspaceTrust(store)
    trust.trust(tmp_path)
    renderer = Renderer(StringIO(), interactive=False)
    interaction = Interaction(DEFAULT_CONFIG, renderer, TelegramPrompter(FakeTelegramClient(), 123, 1), trust, True)
    runtime = AppRuntime(
        paths,
        DEFAULT_CONFIG,
        ProviderResolution(MockProvider(), ProviderStatus.READY, "ready"),
        renderer,
        interaction,
        store,
    )
    client = FakeTelegramClient()
    probe = runner or RunnerProbe(_agent_result(status))
    selected_runner = run_agent if real_agent else probe
    bridge = TelegramBridge(
        client,
        runtime,
        TelegramBot(1, "sovyn_bot"),
        allowed_users,
        poll_timeout=0,
        runner=selected_runner,
    )
    return bridge, probe, client


def _agent_result(status: RunStatus) -> AgentResult:
    return AgentResult(1, "ok", (), 0.1, status=status)


def _message_update(
    text: str,
    *,
    update_id: int = 1,
    user_id: int,
    chat_kind: ChatKind = ChatKind.PRIVATE,
) -> TelegramUpdate:
    return TelegramUpdate(
        update_id,
        TelegramMessage(1, TelegramChat(1, chat_kind), TelegramUser(user_id), text),
    )


def _callback_update(data: str, *, user_id: int, callback_id: str = "callback") -> TelegramUpdate:
    return TelegramUpdate(
        2,
        callback=TelegramCallback(callback_id, TelegramUser(user_id), None, data),
    )


def _wait_for_button(client: FakeTelegramClient) -> None:
    for _ in range(100):
        if client.sent and client.sent[-1].buttons:
            return
        sleep(0.01)
    raise AssertionError("permission prompt was not sent")


def _permission_prompt_count(client: FakeTelegramClient) -> int:
    return sum(1 for item in client.sent if item.text.startswith("Permission required"))


def _resolve_permission(
    prompter: TelegramPrompter,
    client: FakeTelegramClient,
    request: PermissionRequest,
    action: str,
) -> Approval | None:
    result: list[Approval] = []

    def run_request() -> None:
        result.append(prompter.request_permission(request, None, allow_task=True))

    thread = Thread(target=run_request)
    thread.start()
    _wait_for_button(client)
    callback_data = client.sent[-1].buttons[0][0].callback_data.replace(":y:", f":{action}:")
    prompter.resolve_callback(TelegramCallback("cb", TelegramUser(123), None, callback_data))
    thread.join(2)
    return result[0] if result else None
