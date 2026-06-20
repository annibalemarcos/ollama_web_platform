from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

import requests

from ai_providers import AI_PROVIDERS, provider_by_id


class CloudAIError(RuntimeError):
    pass


SUPPORTED_CLOUD_IDS = {"chatgpt", "gemini", "claude", "perplexity"}
CLOUD_AUTO_ID = "web_cloud"


def is_cloud_response_engine(engine_id: str) -> bool:
    return str(engine_id or "").strip() in SUPPORTED_CLOUD_IDS | {CLOUD_AUTO_ID}


def _enabled_and_configured(env: Dict[str, str], provider: Dict[str, str]) -> bool:
    return bool(env.get(provider.get("key_env", ""), "")) and env.get(provider.get("enabled_env", ""), "0") == "1"


def _select_provider(env: Dict[str, str], engine_id: str) -> Dict[str, str]:
    engine_id = str(engine_id or "").strip()
    if engine_id in SUPPORTED_CLOUD_IDS:
        provider = provider_by_id(engine_id)
        if provider and _enabled_and_configured(env, provider):
            return provider
        raise CloudAIError("Este motor web/cloud não está ativo ou não tem API key salva em Configurações.")

    # Auto cloud: prioriza motores que geram resposta sem depender do Ollama local.
    for provider_id in ("perplexity", "chatgpt", "claude", "gemini"):
        provider = provider_by_id(provider_id)
        if provider and _enabled_and_configured(env, provider):
            return provider

    raise CloudAIError(
        "Para rodar Web/Cloud sem motor local, ative e salve uma API key de Perplexity, ChatGPT/OpenAI, Claude ou Gemini em Configurações."
    )


def _system_prompt() -> str:
    return (
        "Você é um assistente de pesquisa em português do Brasil. "
        "Seja claro, prático e honesto. Se houver fontes no prompt, cite no formato [1], [2]. "
        "Não invente dados. Se as fontes forem insuficientes, diga isso."
    )


def _raise_for_response(response: requests.Response, provider_name: str) -> None:
    if response.status_code >= 400:
        raise CloudAIError(f"Erro HTTP em {provider_name}: {response.status_code} - {response.text[:700]}")


def _normalize_gemini_model_name(model_name: str) -> str:
    model_name = str(model_name or "").strip()
    if model_name.startswith("models/"):
        return model_name.split("/", 1)[1]
    return model_name


def _gemini_generate_content_models(api_key: str, timeout: int) -> List[str]:
    """Lista modelos Gemini disponíveis que suportam generateContent.

    A API do Gemini muda nomes e disponibilidade de modelos com alguma frequência.
    Por isso o app evita depender de um único ID fixo quando possível.
    """
    response = requests.get(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
        timeout=min(timeout, 30),
    )
    _raise_for_response(response, "Gemini")
    data = response.json()
    models: List[str] = []
    for item in data.get("models", []):
        methods = item.get("supportedGenerationMethods") or item.get("supported_methods") or []
        if methods and "generateContent" not in methods:
            continue
        name = _normalize_gemini_model_name(item.get("name", ""))
        if name and name not in models:
            models.append(name)
    return models


def _gemini_model_candidates(api_key: str, preferred_model: str, timeout: int) -> List[str]:
    preferred_model = _normalize_gemini_model_name(preferred_model)
    preferred = [model for model in [preferred_model] if model]
    modern_defaults = [
        "gemini-3.1-flash-lite",
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ]
    try:
        available = _gemini_generate_content_models(api_key, timeout)
    except Exception:
        available = []

    ordered: List[str] = []
    for model in preferred + modern_defaults:
        if model and model not in ordered:
            ordered.append(model)

    # Se a API listar modelos, prioriza Flash para respostas rápidas e baratas;
    # depois adiciona qualquer outro que suporte generateContent.
    for model in sorted(available, key=lambda m: ("flash" not in m.lower(), m.lower())):
        if model not in ordered:
            ordered.append(model)
    return ordered


def cloud_chat(
    prompt: str,
    env: Dict[str, str],
    response_engine: str,
    temperature: float = 0.2,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    if should_cancel and should_cancel():
        raise CloudAIError("Execução cancelada antes de chamar o motor web/cloud.")

    provider = _select_provider(env, response_engine)
    provider_id = provider["id"]
    provider_name = provider["name"]
    api_key = env.get(provider["key_env"], "")
    timeout = int(os.getenv("CLOUD_AI_TIMEOUT", "120") or "120")

    headers: Dict[str, str]
    payload: Dict[str, Any]
    content = ""
    model = ""
    raw: Dict[str, Any] = {}

    try:
        if provider_id == "chatgpt":
            model = os.getenv("AI_CHATGPT_MODEL", "gpt-4o-mini")
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": prompt},
                ],
            }
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=timeout)
            _raise_for_response(response, provider_name)
            raw = response.json()
            content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = raw.get("usage", {})

        elif provider_id == "perplexity":
            model = os.getenv("AI_PERPLEXITY_MODEL", "sonar")
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": prompt},
                ],
            }
            response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=timeout)
            _raise_for_response(response, provider_name)
            raw = response.json()
            content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = raw.get("usage", {})

        elif provider_id == "claude":
            model = os.getenv("AI_CLAUDE_MODEL", "claude-3-5-haiku-latest")
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "temperature": temperature,
                "max_tokens": 1200,
                "system": _system_prompt(),
                "messages": [{"role": "user", "content": prompt}],
            }
            response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=timeout)
            _raise_for_response(response, provider_name)
            raw = response.json()
            content = "".join(block.get("text", "") for block in raw.get("content", []) if block.get("type") == "text")
            usage = raw.get("usage", {})

        elif provider_id == "gemini":
            preferred_model = env.get("AI_GEMINI_MODEL") or os.getenv("AI_GEMINI_MODEL", "gemini-3.1-flash-lite")
            payload = {
                "systemInstruction": {"parts": [{"text": _system_prompt()}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature},
            }

            last_error: CloudAIError | None = None
            for candidate_model in _gemini_model_candidates(api_key, preferred_model, timeout):
                model = candidate_model
                response = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                    json=payload,
                    timeout=timeout,
                )
                if response.status_code == 404:
                    last_error = CloudAIError(
                        f"Modelo Gemini indisponível: {model}. Tentando outro modelo compatível com generateContent."
                    )
                    continue
                _raise_for_response(response, provider_name)
                raw = response.json()
                break
            else:
                if last_error:
                    raise CloudAIError(
                        "Nenhum modelo Gemini compatível com generateContent respondeu. "
                        "Abra Configurações e teste a API novamente; se necessário, gere outra chave ou ajuste AI_GEMINI_MODEL."
                    ) from last_error
                raise CloudAIError("Nenhum modelo Gemini disponível para generateContent foi encontrado.")

            parts = raw.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            content = "".join(part.get("text", "") for part in parts)
            usage = raw.get("usageMetadata", {})

        else:
            raise CloudAIError(f"Motor web/cloud ainda não implementado para {provider_name}.")

        if should_cancel and should_cancel():
            raise CloudAIError("Execução cancelada pelo usuário.")

        content = (content or "").strip()
        if not content:
            raise CloudAIError(f"{provider_name} respondeu vazio.")

        return {
            "content": content,
            "metrics": usage,
            "provider": provider_id,
            "provider_name": provider_name,
            "model": model,
            "model_label": f"{provider_name} · {model}",
            "raw": raw,
        }
    except requests.RequestException as exc:
        raise CloudAIError(f"Falha ao chamar {provider_name}: {exc}") from exc
