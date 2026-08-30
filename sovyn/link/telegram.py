from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum, unique
from typing import TypeAlias

import httpx

from sovyn.tool_protocol import JsonValue

RawPayload: TypeAlias = Mapping[str, JsonValue]

TELEGRAM_TEXT_LIMIT = 3900


class TelegramError(RuntimeError):
    pass


class TelegramConfigError(RuntimeError):
    pass


@unique
class ChatKind(StrEnum):
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TelegramUser:
    id: int
    username: str = ""


@dataclass(frozen=True, slots=True)
class TelegramChat:
    id: int
    kind: ChatKind


@dataclass(frozen=True, slots=True)
class TelegramMessage:
    message_id: int
    chat: TelegramChat
    user: TelegramUser | None
    text: str


@dataclass(frozen=True, slots=True)
class TelegramCallback:
    id: str
    user: TelegramUser
    message: TelegramMessage | None
    data: str


@dataclass(frozen=True, slots=True)
class TelegramUpdate:
    update_id: int
    message: TelegramMessage | None = None
    callback: TelegramCallback | None = None


@dataclass(frozen=True, slots=True)
class TelegramBot:
    id: int
    username: str


@dataclass(frozen=True, slots=True)
class InlineButton:
    text: str
    callback_data: str


PostForm: TypeAlias = dict[str, JsonValue]


class TelegramClient:
    def __init__(
        self,
        token: str,
        *,
        timeout: float = 35.0,
        post: Callable[[str, PostForm], RawPayload] | None = None,
    ) -> None:
        self._base_url = f"https://api.telegram.org/bot{token}"
        self._client = httpx.Client(timeout=timeout)
        self._post = post

    def get_me(self) -> TelegramBot:
        payload = self._request("getMe", {})
        result = _mapping(payload.get("result"))
        return TelegramBot(_int(result.get("id")), str(result.get("username") or ""))

    def get_updates(self, offset: int | None, timeout: int) -> tuple[TelegramUpdate, ...]:
        form: PostForm = {"timeout": timeout}
        if offset is not None:
            form["offset"] = offset
        payload = self._request("getUpdates", form)
        return tuple(_parse_update(item) for item in _sequence(payload.get("result")))

    def send_message(
        self,
        chat_id: int,
        text: str,
        buttons: tuple[tuple[InlineButton, ...], ...] = (),
    ) -> None:
        for chunk in chunk_text(text):
            form: PostForm = {"chat_id": chat_id, "text": chunk}
            if buttons:
                form["reply_markup"] = {
                    "inline_keyboard": tuple(
                        tuple({"text": button.text, "callback_data": button.callback_data} for button in row)
                        for row in buttons
                    )
                }
            self._request("sendMessage", form)

    def answer_callback_query(self, callback_id: str, text: str = "") -> None:
        form: PostForm = {"callback_query_id": callback_id}
        if text:
            form["text"] = text
        self._request("answerCallbackQuery", form)

    def edit_message_text(self, chat_id: int, message_id: int, text: str) -> None:
        self._request("editMessageText", {"chat_id": chat_id, "message_id": message_id, "text": text})

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, form: PostForm) -> RawPayload:
        if self._post is not None:
            payload = self._post(method, form)
        else:
            try:
                response = self._client.post(f"{self._base_url}/{method}", json=form)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise TelegramError(f"Telegram request failed: {method}") from exc
            payload = response.json()
        if payload.get("ok") is not True:
            description = str(payload.get("description") or "Telegram API error")
            raise TelegramError(description)
        return payload


def chunk_text(text: str, limit: int = TELEGRAM_TEXT_LIMIT) -> tuple[str, ...]:
    if len(text) <= limit:
        return (text,)
    chunks: list[str] = []
    remaining = text
    while remaining:
        chunk = remaining[:limit]
        split_at = max(chunk.rfind("\n"), chunk.rfind(" "))
        if split_at > limit // 2:
            chunk = chunk[:split_at]
        chunks.append(chunk)
        remaining = remaining[len(chunk) :].lstrip()
    return tuple(chunks)


def parse_allowed_users(raw: str | None) -> tuple[int, ...]:
    if raw is None or raw.strip() == "":
        return ()
    users: list[int] = []
    for item in raw.split(","):
        trimmed = item.strip()
        if not trimmed.isdecimal():
            raise TelegramConfigError("SOVYN_TELEGRAM_ALLOWED_USERS must contain integer Telegram user IDs.")
        users.append(int(trimmed))
    return tuple(users)


def _parse_update(raw: JsonValue) -> TelegramUpdate:
    payload = _mapping(raw)
    return TelegramUpdate(
        _int(payload.get("update_id")),
        _parse_message(payload.get("message")),
        _parse_callback(payload.get("callback_query")),
    )


def _parse_callback(raw: JsonValue) -> TelegramCallback | None:
    if raw is None:
        return None
    payload = _mapping(raw)
    return TelegramCallback(
        str(payload.get("id") or ""),
        _parse_user(payload.get("from")),
        _parse_message(payload.get("message")),
        str(payload.get("data") or ""),
    )


def _parse_message(raw: JsonValue) -> TelegramMessage | None:
    if raw is None:
        return None
    payload = _mapping(raw)
    chat = _mapping(payload.get("chat"))
    return TelegramMessage(
        _int(payload.get("message_id")),
        TelegramChat(_int(chat.get("id")), _chat_kind(str(chat.get("type") or ""))),
        _parse_optional_user(payload.get("from")),
        str(payload.get("text") or ""),
    )


def _parse_optional_user(raw: JsonValue) -> TelegramUser | None:
    if raw is None:
        return None
    return _parse_user(raw)


def _parse_user(raw: JsonValue) -> TelegramUser:
    payload = _mapping(raw)
    return TelegramUser(_int(payload.get("id")), str(payload.get("username") or ""))


def _chat_kind(value: str) -> ChatKind:
    match value:
        case "private":
            return ChatKind.PRIVATE
        case "group":
            return ChatKind.GROUP
        case "supergroup":
            return ChatKind.SUPERGROUP
        case "channel":
            return ChatKind.CHANNEL
        case _:
            return ChatKind.UNKNOWN


def _mapping(raw: JsonValue) -> RawPayload:
    if isinstance(raw, Mapping):
        return raw
    raise TelegramError("Malformed Telegram payload.")


def _sequence(raw: JsonValue) -> Sequence[JsonValue]:
    if isinstance(raw, Sequence) and not isinstance(raw, str):
        return raw
    raise TelegramError("Malformed Telegram payload.")


def _int(raw: JsonValue) -> int:
    if isinstance(raw, int):
        return raw
    raise TelegramError("Malformed Telegram payload.")
