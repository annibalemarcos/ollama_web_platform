from __future__ import annotations

from typing import Any, Dict, List

import requests


AI_PROVIDERS: List[Dict[str, str]] = [
    {"id": "copilot", "name": "Microsoft Copilot", "site_url": "https://copilot.microsoft.com/", "key_env": "AI_COPILOT_API_KEY", "enabled_env": "AI_COPILOT_ENABLED", "category": "Assistente", "test": "manual", "note": "Serviço web; API pública geral não fica padronizada no app."},
    {"id": "you", "name": "You.com", "site_url": "https://you.com/platform", "key_env": "AI_YOU_API_KEY", "enabled_env": "AI_YOU_ENABLED", "category": "Busca + IA", "test": "manual", "note": "Use chave da plataforma You.com, se disponível."},
    {"id": "exa", "name": "Exa", "site_url": "https://exa.ai/", "key_env": "AI_EXA_API_KEY", "enabled_env": "AI_EXA_ENABLED", "category": "Busca neural", "test": "exa", "note": "Teste chama a API de busca da Exa."},
    {"id": "websets_exa", "name": "Exa Websets", "site_url": "https://websets.exa.ai/websets/", "key_env": "AI_EXA_WEBSETS_API_KEY", "enabled_env": "AI_EXA_WEBSETS_ENABLED", "category": "Websets", "test": "manual", "note": "Área Websets da Exa; teste automático genérico no app."},
    {"id": "kagi", "name": "Kagi", "site_url": "https://kagi.com/", "key_env": "AI_KAGI_API_KEY", "enabled_env": "AI_KAGI_ENABLED", "category": "Busca", "test": "kagi", "note": "Teste tenta consulta simples na API de busca da Kagi."},
    {"id": "brave", "name": "Brave Search", "site_url": "https://search.brave.com/", "key_env": "AI_BRAVE_API_KEY", "enabled_env": "AI_BRAVE_ENABLED", "category": "Busca", "test": "brave", "note": "Teste usa Brave Search API."},
    {"id": "andi", "name": "Andi Search", "site_url": "https://andisearch.com/", "key_env": "AI_ANDI_API_KEY", "enabled_env": "AI_ANDI_ENABLED", "category": "Busca", "test": "manual", "note": "Serviço web; teste automático não padronizado."},
    {"id": "consensus", "name": "Consensus", "site_url": "https://consensus.app/", "key_env": "AI_CONSENSUS_API_KEY", "enabled_env": "AI_CONSENSUS_ENABLED", "category": "Pesquisa acadêmica", "test": "manual", "note": "Pesquisa científica; teste automático não padronizado."},
    {"id": "elicit", "name": "Elicit", "site_url": "https://elicit.com/", "key_env": "AI_ELICIT_API_KEY", "enabled_env": "AI_ELICIT_ENABLED", "category": "Pesquisa acadêmica", "test": "manual", "note": "Pesquisa científica; teste automático não padronizado."},
    {"id": "notebooklm", "name": "NotebookLM", "site_url": "https://notebooklm.google.com/", "key_env": "AI_NOTEBOOKLM_API_KEY", "enabled_env": "AI_NOTEBOOKLM_ENABLED", "category": "Notas/documentos", "test": "manual", "note": "Produto web do Google; API pública geral não fica padronizada no app."},
    {"id": "wolframalpha", "name": "WolframAlpha", "site_url": "https://www.wolframalpha.com/", "key_env": "AI_WOLFRAMALPHA_API_KEY", "enabled_env": "AI_WOLFRAMALPHA_ENABLED", "category": "Cálculo/conhecimento", "test": "wolfram", "note": "Teste usa consulta 2+2 na API do WolframAlpha."},
    {"id": "ithy", "name": "Ithy", "site_url": "https://ithy.com/", "key_env": "AI_ITHY_API_KEY", "enabled_env": "AI_ITHY_ENABLED", "category": "Pesquisa/IA", "test": "manual", "note": "Serviço web; teste automático não padronizado."},
    {"id": "gemini", "name": "Gemini", "site_url": "https://gemini.google.com/", "key_env": "AI_GEMINI_API_KEY", "enabled_env": "AI_GEMINI_ENABLED", "category": "LLM", "test": "gemini", "note": "Teste lista modelos da Gemini API."},
    {"id": "iask", "name": "iAsk", "site_url": "https://iask.ai/", "key_env": "AI_IASK_API_KEY", "enabled_env": "AI_IASK_ENABLED", "category": "Busca + IA", "test": "manual", "note": "Serviço web; teste automático não padronizado."},
    {"id": "perplexity", "name": "Perplexity", "site_url": "https://www.perplexity.ai/", "key_env": "AI_PERPLEXITY_API_KEY", "enabled_env": "AI_PERPLEXITY_ENABLED", "category": "Busca + LLM", "test": "perplexity", "note": "Teste tenta acessar endpoint de modelos da API Perplexity."},
    {"id": "claude", "name": "Claude / Anthropic", "site_url": "https://claude.ai/", "key_env": "AI_CLAUDE_API_KEY", "enabled_env": "AI_CLAUDE_ENABLED", "category": "LLM", "test": "anthropic", "note": "Teste lista modelos via Anthropic API."},
    {"id": "chatgpt", "name": "ChatGPT / OpenAI", "site_url": "https://chatgpt.com/", "key_env": "AI_CHATGPT_API_KEY", "enabled_env": "AI_CHATGPT_ENABLED", "category": "LLM", "test": "openai", "note": "Teste lista modelos via OpenAI API."},
]


def provider_env_defaults() -> Dict[str, str]:
    data: Dict[str, str] = {}
    for provider in AI_PROVIDERS:
        data[provider["key_env"]] = ""
        data[provider["enabled_env"]] = "0"
    return data


def provider_by_id(provider_id: str) -> Dict[str, str] | None:
    for provider in AI_PROVIDERS:
        if provider["id"] == provider_id:
            return provider
    return None


def providers_for_ui(env: Dict[str, str], mask_func) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for provider in AI_PROVIDERS:
        key_value = env.get(provider["key_env"], "")
        enabled = env.get(provider["enabled_env"], "0") == "1"
        item = dict(provider)
        item["configured"] = bool(key_value)
        item["masked_key"] = mask_func(key_value)
        item["enabled"] = enabled
        item["status_label"] = "Ativo" if enabled else "Desativado"
        item["test_label"] = "Teste real" if provider.get("test") != "manual" else "Teste básico"
        items.append(item)
    return items


def _status_message(response: requests.Response) -> Dict[str, Any]:
    ok = 200 <= response.status_code < 300
    return {
        "ok": ok,
        "status_code": response.status_code,
        "message": "Conexão OK." if ok else f"Falha HTTP {response.status_code}: {response.text[:240]}",
    }


def test_provider_connection(provider: Dict[str, str], api_key: str) -> Dict[str, Any]:
    if not api_key:
        return {"ok": False, "message": "API key não definida para este provedor."}

    test_type = provider.get("test", "manual")
    timeout = 12

    try:
        if test_type == "openai":
            r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout)
            return _status_message(r)
        if test_type == "gemini":
            r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}", timeout=timeout)
            return _status_message(r)
        if test_type == "anthropic":
            r = requests.get("https://api.anthropic.com/v1/models", headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"}, timeout=timeout)
            return _status_message(r)
        if test_type == "perplexity":
            r = requests.get("https://api.perplexity.ai/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout)
            return _status_message(r)
        if test_type == "brave":
            r = requests.get("https://api.search.brave.com/res/v1/web/search", headers={"X-Subscription-Token": api_key, "Accept": "application/json"}, params={"q": "teste"}, timeout=timeout)
            return _status_message(r)
        if test_type == "exa":
            r = requests.post("https://api.exa.ai/search", headers={"x-api-key": api_key, "Content-Type": "application/json"}, json={"query": "teste", "numResults": 1}, timeout=timeout)
            return _status_message(r)
        if test_type == "kagi":
            r = requests.get("https://kagi.com/api/v0/search", headers={"Authorization": f"Bot {api_key}"}, params={"q": "teste", "limit": 1}, timeout=timeout)
            return _status_message(r)
        if test_type == "wolfram":
            r = requests.get("https://api.wolframalpha.com/v2/query", params={"appid": api_key, "input": "2+2", "output": "json"}, timeout=timeout)
            return _status_message(r)

        return {
            "ok": True,
            "manual": True,
            "message": "API key salva. Este provedor não tem teste automático padronizado no app; abra o link oficial para validar uso real.",
        }
    except requests.RequestException as exc:
        return {"ok": False, "message": f"Erro de conexão: {exc}"}
