import os
from typing import Any, Dict, List, Tuple

import requests


class SearchError(RuntimeError):
    pass


RATE_HEADER_PREFIXES = ("x-ratelimit", "ratelimit", "retry-after")


def _extract_rate_headers(headers: requests.structures.CaseInsensitiveDict) -> Dict[str, str]:
    found: Dict[str, str] = {}
    for key, value in headers.items():
        lower = key.lower()
        if lower.startswith(RATE_HEADER_PREFIXES):
            found[key] = value
    return found


def web_search(query: str, max_results: int = 5) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    api_key = os.getenv("OLLAMA_API_KEY", "").strip()
    if not api_key:
        raise SearchError("OLLAMA_API_KEY não foi definida. Vá em Configurações e informe sua chave.")

    max_results = max(1, min(int(max_results), 10))

    try:
        response = requests.post(
            "https://ollama.com/api/web_search",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"query": query, "max_results": max_results},
            timeout=45,
        )
        rate_headers = _extract_rate_headers(response.headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        message = response.text[:500] if "response" in locals() else str(exc)
        if response.status_code == 429:
            raise SearchError("Limite/rate limit da API atingido ou temporariamente bloqueado: HTTP 429.") from exc
        raise SearchError(f"Erro na busca web: {response.status_code} - {message}") from exc
    except requests.exceptions.RequestException as exc:
        raise SearchError(f"Falha ao chamar a busca web: {exc}") from exc

    payload = response.json()
    results = payload.get("results", [])

    cleaned: List[Dict[str, Any]] = []
    for item in results:
        cleaned.append(
            {
                "title": item.get("title") or "Sem título",
                "url": item.get("url") or "",
                "content": item.get("content") or "",
            }
        )

    return cleaned, rate_headers
