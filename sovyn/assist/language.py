import re
from collections.abc import Iterable

from sovyn.config import InterfaceLanguage, SovynConfig

from .types import CapabilityLevel, ModelCapabilityProfile, PreparedRequest

LANGUAGE_LABELS = {
    InterfaceLanguage.AUTO: "Auto",
    InterfaceLanguage.KO: "한국어",
    InterfaceLanguage.EN: "English",
    InterfaceLanguage.JA: "日本語",
    InterfaceLanguage.ZH: "中文",
}


def infer_capabilities(model_name: str) -> ModelCapabilityProfile:
    lowered = model_name.lower()
    if "qwen3:1.7b" in lowered or "1.7b" in lowered:
        return ModelCapabilityProfile(
            multilingual=CapabilityLevel.WEAK,
            tool_calling=CapabilityLevel.MEDIUM,
            completion=CapabilityLevel.WEAK,
        )
    return ModelCapabilityProfile()


def resolve_language(request: str, configured: InterfaceLanguage) -> InterfaceLanguage:
    if _explicit_english(request):
        return InterfaceLanguage.EN
    if configured is not InterfaceLanguage.AUTO:
        return configured
    return detect_language(request)


def detect_language(text: str) -> InterfaceLanguage:
    if re.search(r"[\uac00-\ud7a3]", text):
        return InterfaceLanguage.KO
    if re.search(r"[\u3040-\u30ff]", text):
        return InterfaceLanguage.JA
    if re.search(r"[\u4e00-\u9fff]", text):
        return InterfaceLanguage.ZH
    return InterfaceLanguage.EN


def prepare_request(request: str, config: SovynConfig, model_name: str) -> PreparedRequest:
    language = resolve_language(request, config.interface.language)
    profile = infer_capabilities(model_name)
    if config.assist.enabled and _should_wrap(config.assist.mode.value, language, profile):
        prompt = _wrapped_request(request, language)
    else:
        prompt = request
    return PreparedRequest(request, prompt, language)


def identity_instruction(language: InterfaceLanguage, model_name: str) -> str:
    return (
        "You are SOVYN, a local-first agent on the user's machine. "
        f"Underlying model: {model_name}. "
        "Say you are SOVYN unless the user asks what model is used. "
        "Never claim success without execution evidence. "
        f"Final answer language: {LANGUAGE_LABELS[language]}."
    )


def direct_identity_answer(request: str, language: InterfaceLanguage, model_name: str) -> str | None:
    lowered = request.lower().strip()
    if _asks_model(lowered):
        return _model_answer(language, model_name)
    if _asks_identity(lowered):
        return _identity_answer(language)
    return None


def language_options(include_auto: bool = True) -> tuple[InterfaceLanguage, ...]:
    base = (InterfaceLanguage.KO, InterfaceLanguage.EN, InterfaceLanguage.JA, InterfaceLanguage.ZH)
    return (InterfaceLanguage.AUTO, *base) if include_auto else base


def language_label(language: InterfaceLanguage) -> str:
    return LANGUAGE_LABELS[language]


def preserve_literals(text: str) -> tuple[str, ...]:
    patterns: Iterable[str] = (
        r"`[^`]+`",
        r'"[^"]+"',
        r"'[^']+'",
        r"https?://\S+",
        r"[A-Za-z]:\\[^\s]+",
        r"[\w.-]+\.(?:py|md|txt|json|toml|yaml|yml|js|ts|tsx|html|css)",
        r"\b(?:pytest|ruff|git|python|sovyn|ollama)(?:\s+[^\n]+)?",
    )
    literals: list[str] = []
    for pattern in patterns:
        literals.extend(match.group(0).strip() for match in re.finditer(pattern, text))
    return tuple(dict.fromkeys(literals))


def _wrapped_request(request: str, language: InterfaceLanguage) -> str:
    literals = preserve_literals(request)
    literal_block = "\n".join(f"- {item}" for item in literals) if literals else "- none"
    return (
        "GOAL:\n"
        f"{request}\n\n"
        "USER_LANGUAGE:\n"
        f"{language.value}\n\n"
        "PRESERVE_LITERALS:\n"
        f"{literal_block}\n\n"
        "RULE:\n"
        "Use tools when needed. Return the final answer in the user language."
    )


def _should_wrap(mode: str, language: InterfaceLanguage, profile: ModelCapabilityProfile) -> bool:
    if mode == "off":
        return False
    if mode == "always":
        return True
    return language is not InterfaceLanguage.EN or profile.multilingual is CapabilityLevel.WEAK


def _explicit_english(request: str) -> bool:
    lowered = request.lower()
    return "answer in english" in lowered or "영어로" in lowered


def _asks_identity(lowered: str) -> bool:
    return lowered in {"who are you?", "who are you"} or "너는 누구" in lowered


def _asks_model(lowered: str) -> bool:
    return "what model" in lowered or "무슨 모델" in lowered or "어떤 모델" in lowered


def _identity_answer(language: InterfaceLanguage) -> str:
    match language:
        case InterfaceLanguage.KO:
            return "나는 SOVYN이야. 네 컴퓨터에서 실행되는 로컬 에이전트야."
        case InterfaceLanguage.JA:
            return "私はSOVYNです。あなたのコンピューター上で動くローカルエージェントです。"
        case InterfaceLanguage.ZH:
            return "我是 SOVYN，在你的电脑上运行的本地代理。"
        case InterfaceLanguage.AUTO | InterfaceLanguage.EN:
            return "I am SOVYN, a local-first agent running on your machine."
        case unreachable:
            raise AssertionError(f"unknown language: {unreachable}")


def _model_answer(language: InterfaceLanguage, model_name: str) -> str:
    match language:
        case InterfaceLanguage.KO:
            return f"현재 {model_name}를 사용하고 있어."
        case InterfaceLanguage.JA:
            return f"現在 {model_name} を使用しています。"
        case InterfaceLanguage.ZH:
            return f"当前使用的是 {model_name}。"
        case InterfaceLanguage.AUTO | InterfaceLanguage.EN:
            return f"SOVYN is currently using {model_name}."
        case unreachable:
            raise AssertionError(f"unknown language: {unreachable}")
