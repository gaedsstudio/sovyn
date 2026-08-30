import os
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from secrets import token_urlsafe
from threading import Event, Lock, Thread
from time import sleep
from typing import TextIO, assert_never

from sovyn.agent import AgentResult, AgentRuntime, RunStatus, run_agent
from sovyn.assist.language import language_label, language_options
from sovyn.config import InterfaceLanguage, InterfaceSettings, write_config
from sovyn.diffing import DiffPreview
from sovyn.interaction import Approval, Interaction
from sovyn.permissions import ActionKind, PermissionDecision, PermissionRequest, decide_permission
from sovyn.provider_init import ProviderStatus
from sovyn.runtime import AppRuntime, boot
from sovyn.storage import has_permission_grant
from sovyn.trust import WorkspaceTrust
from sovyn.ui import DiamondState

from .telegram import (
    ChatKind,
    InlineButton,
    TelegramBot,
    TelegramCallback,
    TelegramClient,
    TelegramConfigError,
    TelegramError,
    TelegramMessage,
    TelegramUpdate,
    parse_allowed_users,
)


@dataclass(frozen=True, slots=True)
class TelegramLinkSettings:
    token: str
    allowed_users: tuple[int, ...]
    poll_timeout: int
    debug: bool
    workspace: Path


@dataclass(slots=True)
class PendingApproval:
    user_id: int
    chat_id: int
    approval_id: str
    event: Event
    answer: str | None = None


AgentRunner = Callable[[str, AgentRuntime], AgentResult]


class TelegramPrompter:
    def __init__(self, client: TelegramClient, user_id: int, chat_id: int) -> None:
        self._client = client
        self._user_id = user_id
        self._chat_id = chat_id
        self._pending: dict[str, PendingApproval] = {}
        self._lock = Lock()

    def ask(self, prompt: str) -> str:
        self._client.send_message(self._chat_id, prompt)
        return "n"

    def request_permission(
        self,
        request: PermissionRequest,
        diff: DiffPreview | None,
        *,
        allow_task: bool,
    ) -> Approval:
        if request.destructive:
            self._client.send_message(self._chat_id, "This action requires local confirmation.")
            return Approval.DENY
        approval_id = token_urlsafe(8)
        event = Event()
        pending = PendingApproval(self._user_id, self._chat_id, approval_id, event)
        with self._lock:
            self._pending[approval_id] = pending
        self._client.send_message(
            self._chat_id,
            _permission_text(request, diff),
            _approval_buttons(approval_id, allow_task),
        )
        event.wait()
        with self._lock:
            answer = pending.answer
            self._pending.pop(approval_id, None)
        match answer:
            case "a":
                return Approval.TASK
            case "y":
                return Approval.ONCE
            case "n" | None:
                return Approval.DENY
            case unreachable:
                assert_never(unreachable)

    def resolve_callback(self, callback: TelegramCallback) -> bool:
        parsed = _parse_approval_callback(callback.data)
        if parsed is None:
            return False
        action, approval_id = parsed
        with self._lock:
            pending = self._pending.get(approval_id)
            if pending is None:
                self._client.answer_callback_query(callback.id, "approval expired")
                return True
            if callback.user.id != pending.user_id:
                self._client.answer_callback_query(callback.id, "not authorized")
                return True
            pending.answer = action
            pending.event.set()
        self._client.answer_callback_query(callback.id, "received")
        return True


@dataclass(frozen=True, slots=True)
class TelegramInteraction(Interaction):
    telegram_prompter: TelegramPrompter | None = None

    def _ask_permission(self, request: PermissionRequest, diff: DiffPreview | None) -> Approval:
        approval = self._telegram_prompter().request_permission(request, diff, allow_task=True)
        if approval is Approval.TASK:
            self.task_grants.add((request.action.value, request.description))
            self.task_grants.add((request.action.value, "*"))
        return approval

    def approve_network(self, method: str, url: str, host: str) -> Approval:
        request = PermissionRequest(ActionKind.NETWORK_READ, f"{method} {host}")
        if has_permission_grant(self.trust.store, request.action.value, host):
            return Approval.ALWAYS
        decision = decide_permission(self.config.permissions, request, self.interactive)
        match decision:
            case PermissionDecision.ALLOW:
                return Approval.ONCE
            case PermissionDecision.BLOCK:
                return Approval.DENY
            case PermissionDecision.ASK:
                return self._telegram_prompter().request_permission(
                    PermissionRequest(ActionKind.NETWORK_READ, f"{method} {host}", reason=url),
                    None,
                    allow_task=False,
                )
            case unreachable:
                assert_never(unreachable)

    def offer_workflow(self, workflow, workflows_dir: Path) -> bool:
        return False

    def _telegram_prompter(self) -> TelegramPrompter:
        if self.telegram_prompter is None:
            raise TelegramConfigError("Telegram prompter is not configured.")
        return self.telegram_prompter


@dataclass(slots=True)
class TelegramBridge:
    client: TelegramClient
    runtime: AppRuntime
    bot: TelegramBot
    allowed_users: tuple[int, ...]
    poll_timeout: int = 30
    runner: AgentRunner = run_agent
    _offset: int | None = None
    _busy: Lock = field(default_factory=Lock)
    _active_prompter: TelegramPrompter | None = None
    _worker: Thread | None = None
    _stopping: bool = False

    @property
    def locked(self) -> bool:
        return not self.allowed_users

    def run_forever(self) -> None:
        backoff = 1.0
        while not self._stopping:
            try:
                for update in self.client.get_updates(self._offset, self.poll_timeout):
                    self._offset = update.update_id + 1
                    self.handle_update(update)
                backoff = 1.0
            except KeyboardInterrupt:
                self.stop()
            except TelegramError as exc:
                self.runtime.renderer.line(DiamondState.ATTENTION, f"Telegram unavailable: {exc}")
                sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    def stop(self) -> None:
        self._stopping = True
        self.client.close()

    def handle_update(self, update: TelegramUpdate) -> None:
        if update.callback is not None:
            self._handle_callback(update.callback)
            return
        if update.message is not None:
            self._handle_message(update.message)

    def wait_for_idle(self, timeout: float = 5.0) -> bool:
        worker = self._worker
        if worker is None:
            return True
        worker.join(timeout)
        return not worker.is_alive()

    def _handle_callback(self, callback: TelegramCallback) -> None:
        if self._handle_language_callback(callback):
            return
        if self._active_prompter is None or not self._active_prompter.resolve_callback(callback):
            self.client.answer_callback_query(callback.id, "approval expired")

    def _handle_message(self, message: TelegramMessage) -> None:
        if message.chat.kind is not ChatKind.PRIVATE:
            return
        if message.user is None:
            return
        text = message.text.strip()
        if text == "":
            return
        if text.startswith("/"):
            self._handle_command(message, text.split(maxsplit=1)[0])
            return
        if not self._authorized(message.user.id):
            self.client.send_message(message.chat.id, _locked_text(message.user.id) if self.locked else "Unauthorized.")
            return
        if not self._busy.acquire(blocking=False):
            self.client.send_message(message.chat.id, "SOVYN is currently working on another task.")
            return
        self.client.send_message(message.chat.id, "SOVYN is working...")
        self._worker = Thread(target=self._run_task, args=(message,), daemon=True)
        self._worker.start()

    def _handle_command(self, message: TelegramMessage, command: str) -> None:
        if message.user is None:
            return
        if command == "/whoami":
            self.client.send_message(message.chat.id, f"Your Telegram user ID: {message.user.id}")
            return
        if not self._authorized(message.user.id):
            self.client.send_message(message.chat.id, _locked_text(message.user.id) if self.locked else "Unauthorized.")
            return
        match command:
            case "/start":
                self.client.send_message(
                    message.chat.id,
                    "SOVYN Link is connected.\n\nSend a task to your local SOVYN agent.",
                )
            case "/help":
                self.client.send_message(
                    message.chat.id,
                    (
                        "Commands: /status, /model, /workspace, /language, /whoami, /help.\n"
                        "Send any other private message as a SOVYN task."
                    ),
                )
            case "/status":
                self.client.send_message(
                    message.chat.id,
                    (
                        "SOVYN\n"
                        "PC: online\n"
                        f"Provider: {_provider_status(self.runtime)}\n"
                        f"Model: {self.runtime.provider.provider.name}\n"
                        f"Workspace: {self.runtime.paths.workspace}"
                    ),
                )
            case "/model":
                self.client.send_message(message.chat.id, self.runtime.provider.provider.name)
            case "/workspace":
                self.client.send_message(message.chat.id, str(self.runtime.paths.workspace))
            case "/language":
                self._send_language_menu(message.chat.id)
            case _:
                self.client.send_message(message.chat.id, "Unknown command. Send /help for available commands.")

    def _run_task(self, message: TelegramMessage) -> None:
        if message.user is None:
            self._busy.release()
            return
        prompter = TelegramPrompter(self.client, message.user.id, message.chat.id)
        self._active_prompter = prompter
        interaction = TelegramInteraction(
            self.runtime.config,
            self.runtime.renderer,
            prompter,
            WorkspaceTrust(self.runtime.store),
            True,
            telegram_prompter=prompter,
        )
        try:
            result = self.runner(
                message.text,
                AgentRuntime(
                    self.runtime.provider.provider,
                    self.runtime.store,
                    self.runtime.renderer,
                    self.runtime.paths.workspace,
                    interaction,
                    self.runtime.debug,
                    self.runtime.paths.workflows,
                ),
            )
            self.client.send_message(message.chat.id, _agent_message(result))
        finally:
            self._active_prompter = None
            self._busy.release()

    def _authorized(self, user_id: int) -> bool:
        return user_id in self.allowed_users

    def _send_language_menu(self, chat_id: int) -> None:
        language = self.runtime.config.interface.language
        buttons = tuple(
            (InlineButton(language_label(item), f"sovyn:lang:{item.value}"),)
            for item in language_options(include_auto=False)
        )
        self.client.send_message(chat_id, f"Current language: {language_label(language)}", buttons)

    def _handle_language_callback(self, callback: TelegramCallback) -> bool:
        if not callback.data.startswith("sovyn:lang:"):
            return False
        if callback.user.id not in self.allowed_users:
            self.client.answer_callback_query(callback.id, "not authorized")
            return True
        raw = callback.data.removeprefix("sovyn:lang:")
        try:
            language = InterfaceLanguage(raw)
        except ValueError:
            self.client.answer_callback_query(callback.id, "invalid language")
            return True
        config = replace(self.runtime.config, interface=InterfaceSettings(language, True))
        write_config(self.runtime.paths.config, config)
        self.runtime = replace(self.runtime, config=config)
        self.client.answer_callback_query(callback.id, "language updated")
        chat_id = callback.message.chat.id if callback.message is not None else callback.user.id
        self.client.send_message(chat_id, f"Language set to {language_label(language)}.")
        return True


def load_telegram_settings(workspace: Path | None, poll_timeout: int, debug: bool) -> TelegramLinkSettings:
    token = os.environ.get("SOVYN_TELEGRAM_TOKEN", "")
    if token == "":
        raise TelegramConfigError("SOVYN_TELEGRAM_TOKEN is not configured.")
    allowed_users = parse_allowed_users(os.environ.get("SOVYN_TELEGRAM_ALLOWED_USERS"))
    return TelegramLinkSettings(token, allowed_users, poll_timeout, debug, workspace or Path.cwd())


def start_telegram_link(
    input_stream: TextIO,
    output_stream: TextIO,
    *,
    workspace: Path | None,
    poll_timeout: int,
    debug: bool,
    client_factory: Callable[[str], TelegramClient] = TelegramClient,
) -> None:
    settings = load_telegram_settings(workspace, poll_timeout, debug)
    runtime = boot(input_stream, output_stream, interactive=True, workspace=settings.workspace, debug=debug)
    if not runtime.interaction.ensure_workspace_trusted(runtime.paths.workspace):
        runtime.renderer.line(DiamondState.FAILED, "Workspace is not trusted")
        return
    if runtime.provider.status is ProviderStatus.UNAVAILABLE:
        runtime.renderer.line(DiamondState.FAILED, runtime.provider.detail)
        return
    client = client_factory(settings.token)
    bot = client.get_me()
    _render_startup(runtime, bot, settings.allowed_users)
    TelegramBridge(client, runtime, bot, settings.allowed_users, settings.poll_timeout).run_forever()


def _render_startup(runtime: AppRuntime, bot: TelegramBot, allowed_users: tuple[int, ...]) -> None:
    runtime.renderer.stream_text("SOVYN Link")
    runtime.renderer.stream_text("")
    runtime.renderer.stream_text(f"Telegram    @{bot.username}")
    runtime.renderer.stream_text(f"Model       {runtime.provider.provider.name}")
    runtime.renderer.stream_text(f"Workspace   {runtime.paths.workspace}")
    users = f"{len(allowed_users)} authorized" if allowed_users else "locked; use /whoami"
    runtime.renderer.stream_text(f"Users       {users}")
    runtime.renderer.stream_text("Status      Waiting for messages")


def _permission_text(request: PermissionRequest, diff: DiffPreview | None) -> str:
    lines = ["Permission required", "", request.description, "", "Reason:", request.reason]
    if diff is not None:
        lines.extend(("", "Changes:", f"+{diff.additions} -{diff.deletions}"))
    return "\n".join(lines)


def _approval_buttons(approval_id: str, allow_task: bool) -> tuple[tuple[InlineButton, ...], ...]:
    buttons = [InlineButton("Allow once", f"sovyn:y:{approval_id}")]
    if allow_task:
        buttons.append(InlineButton("Allow for task", f"sovyn:a:{approval_id}"))
    buttons.append(InlineButton("Deny", f"sovyn:n:{approval_id}"))
    return (tuple(buttons),)


def _parse_approval_callback(data: str) -> tuple[str, str] | None:
    parts = data.split(":", maxsplit=2)
    if len(parts) != 3 or parts[0] != "sovyn" or parts[1] not in {"y", "a", "n"}:
        return None
    return parts[1], parts[2]


def _agent_message(result: AgentResult) -> str:
    match result.status:
        case RunStatus.SUCCESS:
            changed = tuple(
                dict.fromkeys(
                    tool.output
                    for tool in result.tools
                    if tool.success and tool.name == "filesystem.write" and not tool.no_change
                )
            )
            suffix = "\n\nChanged:\n" + "\n".join(Path(path).name for path in changed) if changed else ""
            return f"{result.response or 'Done.'}{suffix}"
        case RunStatus.STALLED:
            return "SOVYN couldn't complete this task reliably.\nStatus: stalled"
        case RunStatus.PROVIDER_ERROR:
            return "SOVYN provider is unavailable."
        case RunStatus.FAILED:
            return "Task failed."
        case RunStatus.CANCELLED:
            return "Task cancelled."
        case RunStatus.STEP_LIMIT:
            return "SOVYN couldn't complete this task reliably.\nStatus: step_limit"
        case unreachable:
            assert_never(unreachable)


def _provider_status(runtime: AppRuntime) -> str:
    match runtime.provider.status:
        case ProviderStatus.READY:
            return "ready"
        case ProviderStatus.UNAVAILABLE:
            return "unavailable"
        case unreachable:
            assert_never(unreachable)


def _locked_text(user_id: int) -> str:
    return (
        f"Your Telegram user ID: {user_id}\n\n"
        "Set:\n"
        f"SOVYN_TELEGRAM_ALLOWED_USERS={user_id}\n\n"
        "Then restart SOVYN Link."
    )
