import json
import os
import subprocess
from typing import Any, Callable, Dict, List, Optional

import requests

from settings_manager import as_int


class OllamaError(RuntimeError):
    pass


def _base_url() -> str:
    return os.getenv("OLLAMA_LOCAL_URL", "http://127.0.0.1:11434").rstrip("/")


def _request_timeout() -> int:
    # PC com CPU/RAM modestos pode levar mais de 150s em modelos 4B/7B.
    # Mantemos um piso de 600s para evitar falso timeout enquanto o Ollama ainda está trabalhando.
    configured = as_int(os.getenv("OLLAMA_REQUEST_TIMEOUT", "600"), 600) or 600
    return max(configured, 600)


def _runtime_options(temperature: float) -> Dict[str, Any]:
    """Runtime options sent to Ollama. These are the main anti-PC-frying knobs."""
    options: Dict[str, Any] = {"temperature": temperature}

    num_ctx = as_int(os.getenv("OLLAMA_NUM_CTX", "2048"), 2048)
    num_predict = as_int(os.getenv("OLLAMA_NUM_PREDICT", "512"), 512)
    num_thread = as_int(os.getenv("OLLAMA_NUM_THREAD", "2"), 2)

    if num_ctx:
        options["num_ctx"] = num_ctx
    if num_predict:
        options["num_predict"] = num_predict
    if num_thread:
        options["num_thread"] = num_thread

    return options


def check_ollama() -> Dict[str, Any]:
    try:
        response = requests.get(f"{_base_url()}/api/tags", timeout=5)
        response.raise_for_status()
        return {"ok": True, "models": response.json().get("models", [])}
    except requests.exceptions.RequestException as exc:
        return {"ok": False, "error": str(exc), "models": []}


def list_models() -> List[str]:
    status = check_ollama()
    if not status.get("ok"):
        return []
    names = [m.get("name", "") for m in status.get("models", []) if m.get("name")]
    return sorted(set(names), key=str.lower)


def stop_model(model: str) -> Dict[str, Any]:
    """Best-effort model interruption/unload.

    The streaming client usually cancels by closing the HTTP response. This function is an extra kick:
    it tries the Ollama CLI and then asks the local API to unload the model.
    """
    result: Dict[str, Any] = {"cli_called": False, "cli_ok": False, "cli_error": None, "http_called": False, "http_ok": False, "http_error": None}

    if not model:
        return result

    try:
        result["cli_called"] = True
        proc = subprocess.run(
            ["ollama", "stop", str(model)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        result["cli_ok"] = proc.returncode == 0
        if proc.returncode != 0:
            result["cli_error"] = (proc.stderr or proc.stdout or "ollama stop retornou erro").strip()[:500]
    except Exception as exc:  # noqa: BLE001
        result["cli_error"] = str(exc)

    # Fallback: ask Ollama API to unload the model.
    try:
        result["http_called"] = True
        response = requests.post(
            f"{_base_url()}/api/generate",
            json={"model": model, "prompt": "", "keep_alive": 0, "stream": False},
            timeout=10,
        )
        result["http_ok"] = response.status_code < 400
        if response.status_code >= 400:
            result["http_error"] = response.text[:500]
    except Exception as exc:  # noqa: BLE001
        result["http_error"] = str(exc)

    return result


def chat(
    prompt: str,
    model: str,
    temperature: float = 0.2,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "0").strip() or "0"

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Você é um assistente de pesquisa em português do Brasil. "
                    "Seja claro, prático, honesto e cite as fontes no formato [1], [2] quando usar a web. "
                    "Não invente dados. Se as fontes forem insuficientes, diga isso. "
                    "Prefira respostas compactas quando o usuário não pedir detalhes."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "options": _runtime_options(temperature),
        "stream": True,
        "keep_alive": keep_alive,
    }

    content_parts: List[str] = []
    last_data: Dict[str, Any] = {}
    response = None

    try:
        response = requests.post(
            f"{_base_url()}/api/chat",
            json=payload,
            timeout=(10, _request_timeout()),
            stream=True,
        )
        response.raise_for_status()

        for raw_line in response.iter_lines(decode_unicode=True):
            if should_cancel and should_cancel():
                response.close()
                stop_model(model)
                raise OllamaError("Execução cancelada pelo usuário.")

            if not raw_line:
                continue

            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            last_data = data
            chunk = data.get("message", {}).get("content", "")
            if chunk:
                content_parts.append(chunk)

            if data.get("done"):
                break

        if should_cancel and should_cancel():
            if response is not None:
                response.close()
            stop_model(model)
            raise OllamaError("Execução cancelada pelo usuário.")

    except requests.exceptions.ReadTimeout as exc:
        raise OllamaError(
            "O Ollama demorou demais para responder. Aumentei o timeout padrão para 600s, mas se isso ainda aparecer, use um modelo mais leve, reduza Fontes para 2-3 ou clique em Parar/Cancelar no Status."
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise OllamaError(
            "Não consegui conectar ao Ollama local. Abra o Ollama e confirme se ele está rodando em http://127.0.0.1:11434."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        detail = response.text[:800] if response is not None else str(exc)
        raise OllamaError(f"Erro HTTP do Ollama local: {detail}") from exc
    except requests.exceptions.RequestException as exc:
        raise OllamaError(f"Falha ao chamar o Ollama local: {exc}") from exc
    finally:
        if response is not None:
            response.close()

    content = "".join(content_parts).strip()
    metrics = {
        "total_duration": last_data.get("total_duration", 0),
        "load_duration": last_data.get("load_duration", 0),
        "prompt_eval_count": last_data.get("prompt_eval_count", 0),
        "prompt_eval_duration": last_data.get("prompt_eval_duration", 0),
        "eval_count": last_data.get("eval_count", 0),
        "eval_duration": last_data.get("eval_duration", 0),
        "num_ctx": payload["options"].get("num_ctx"),
        "num_predict": payload["options"].get("num_predict"),
        "num_thread": payload["options"].get("num_thread"),
        "keep_alive": keep_alive,
    }
    return {"content": content, "metrics": metrics, "raw": last_data}
