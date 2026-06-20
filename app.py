import html
import json
import os
import re
import subprocess
import threading
import time
import uuid
from io import BytesIO
from typing import Any, Dict, List

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, redirect, render_template, request, send_file, url_for
from markupsafe import Markup

from db import (
    add_history,
    add_usage_log,
    clear_history,
    delete_history,
    get_history,
    init_db,
    list_history,
    recent_usage_logs,
    usage_stats,
)
from model_catalog import model_catalog_with_status, normalize_model_name
from services.cloud_client import CloudAIError, cloud_chat, is_cloud_response_engine
from services.ollama_client import OllamaError, chat, check_ollama, list_models, stop_model
from services.pc_stats import collect_pc_stats
from services.search_client import SearchError, web_search
from settings_manager import DEFAULTS, apply_env_to_process, as_int, mask_secret, read_env_file, write_env_file
from ai_providers import AI_PROVIDERS, provider_by_id, providers_for_ui, test_provider_connection

load_dotenv(override=True)
apply_env_to_process()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "local-dev-only-change-me")

JOB_LOCK = threading.Lock()
ACTIVE_LOCK = threading.RLock()
ACTIVE_JOB = {"id": None, "cancel_requested": False, "model": None, "query": None, "started_at": None, "stage": None}
MODEL_TASK_LOCK = threading.RLock()
MODEL_TASK: Dict[str, Any] = {"id": None, "running": False, "action": None, "model": None, "status": "idle", "message": "", "lines": [], "started_at": None, "finished_at": None, "ok": None}

CODE_BLOCK_RE = re.compile(r"```([\w.+#-]*)\n?(.*?)```", re.DOTALL)


def _render_citation_group(match: re.Match[str]) -> str:
    numbers = re.findall(r"\[(\d{1,3})\]", match.group(0))
    if not numbers:
        return match.group(0)
    chips = "".join(f'<span class="answer-citation">[{html.escape(number)}]</span>' for number in numbers)
    return f' <span class="answer-citation-group" title="Referências nas fontes ao lado">{chips}</span>'


def _strip_trailing_sources_section(value: str) -> str:
    """Remove uma seção final de fontes quando o app já mostra as fontes no painel lateral."""
    pattern = r"\n\s*(?:\*\*)?Fontes?:?(?:\*\*)?\s*\n(?:\s*(?:[-*]\s*)?\[\d+\].*(?:\n|$))+\s*$"
    return re.sub(pattern, "", value, flags=re.IGNORECASE)


def _strip_inline_citations(value: str) -> str:
    """Remove referências inline [1], [2], [3] da versão limpa do campo Resposta."""
    return re.sub(r"\s*(?:\[\d{1,3}\]\s*,?\s*)+", " ", value).strip()

def _render_inline_markdown(value: str, include_citations: bool = True) -> str:
    """Renderiza um subconjunto seguro de Markdown para deixar a resposta mais parecida com chat moderno."""
    escaped = html.escape(value)

    # Grupos de citações tipo [1], [2], [3] só aparecem na versão completa da resposta.
    if include_citations:
        escaped = re.sub(r"(?:\s*\[\d{1,3}\]\s*,?)+", _render_citation_group, escaped)

    # Links crus primeiro, para URLs em fontes/listas não ficarem parecendo tijolo de texto.
    escaped = re.sub(
        r"(https?://[^\s<]+)",
        r'<a class="answer-link" href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
        escaped,
    )

    # Inline code e negrito simples. Não é um parser Markdown completo; é propositalmente leve.
    escaped = re.sub(r"`([^`]+)`", r'<code class="answer-inline-code">\1</code>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def _flush_paragraph(buffer: List[str], parts: List[str], include_citations: bool = True) -> None:
    if not buffer:
        return
    paragraph = " ".join(item.strip() for item in buffer if item.strip())
    if paragraph:
        parts.append(f"<p>{_render_inline_markdown(paragraph, include_citations=include_citations)}</p>")
    buffer.clear()


def _render_prose_html(text: str, include_citations: bool = True) -> str:
    parts: List[str] = []
    paragraph_buffer: List[str] = []
    current_list: str | None = None

    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return ""

    def close_list() -> None:
        nonlocal current_list
        if current_list:
            parts.append(f"</{current_list}>")
            current_list = None

    for raw_line in normalized.split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            _flush_paragraph(paragraph_buffer, parts, include_citations=include_citations)
            close_list()
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        bold_heading = re.match(r"^\*\*([^*]+?)\*\*:?\s*$", stripped)
        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        numbered = re.match(r"^\d+[.)]\s+(.+)$", stripped)

        if heading:
            _flush_paragraph(paragraph_buffer, parts, include_citations=include_citations)
            close_list()
            level = min(4, len(heading.group(1)) + 1)
            parts.append(f'<h{level} class="answer-heading">{_render_inline_markdown(heading.group(2).strip(), include_citations=include_citations)}</h{level}>')
            continue

        if bold_heading and len(stripped) <= 90:
            _flush_paragraph(paragraph_buffer, parts, include_citations=include_citations)
            close_list()
            parts.append(f'<h3 class="answer-heading">{_render_inline_markdown(bold_heading.group(1).strip(), include_citations=include_citations)}</h3>')
            continue

        if bullet:
            _flush_paragraph(paragraph_buffer, parts, include_citations=include_citations)
            if current_list != "ul":
                close_list()
                parts.append('<ul class="answer-list">')
                current_list = "ul"
            parts.append(f"<li>{_render_inline_markdown(bullet.group(1).strip(), include_citations=include_citations)}</li>")
            continue

        if numbered:
            _flush_paragraph(paragraph_buffer, parts, include_citations=include_citations)
            if current_list != "ol":
                close_list()
                parts.append('<ol class="answer-list answer-list-numbered">')
                current_list = "ol"
            parts.append(f"<li>{_render_inline_markdown(numbered.group(1).strip(), include_citations=include_citations)}</li>")
            continue

        close_list()
        paragraph_buffer.append(stripped)

    _flush_paragraph(paragraph_buffer, parts, include_citations=include_citations)
    close_list()
    return "".join(parts)


def render_answer_html(text: str, include_citations: bool = True, strip_sources_section: bool = True) -> Markup:
    if not text:
        return Markup("")

    if strip_sources_section:
        text = _strip_trailing_sources_section(text)
    if not include_citations:
        text = _strip_inline_citations(text)
    segments: List[str] = []
    last_end = 0

    for match_index, match in enumerate(CODE_BLOCK_RE.finditer(text), start=1):
        before = text[last_end:match.start()]
        if before.strip():
            segments.append(f'<div class="answer-prose">{_render_prose_html(before, include_citations=include_citations)}</div>')

        language = (match.group(1) or "").strip()
        code_body = match.group(2).rstrip("\n")
        lang_label = language if language else "Código"
        escaped_code = html.escape(code_body)
        escaped_lang_label = html.escape(lang_label)
        lang_class = html.escape(language.lower() or "plain")
        block_id = f"code-block-{match_index}-{uuid.uuid4().hex[:8]}"
        segments.append(
            "<div class=\"answer-code-card\">"
            "<div class=\"answer-code-toolbar\">"
            "<div class=\"answer-code-meta\"><span class=\"answer-code-icon\"><i class=\"bi bi-code-slash\"></i></span>"
            f"<span class=\"answer-code-lang\">{escaped_lang_label}</span></div>"
            f"<button type=\"button\" class=\"answer-code-copy\" onclick=\"copyCodeBlock('{block_id}', this)\"><i class=\"bi bi-copy\"></i><span>Copiar</span></button>"
            "</div>"
            f"<pre class=\"answer-code-pre\"><code id=\"{block_id}\" class=\"language-{lang_class}\" data-language=\"{escaped_lang_label}\">{escaped_code}</code></pre>"
            "</div>"
        )
        last_end = match.end()

    tail = text[last_end:]
    if tail.strip():
        segments.append(f'<div class="answer-prose">{_render_prose_html(tail, include_citations=include_citations)}</div>')

    if not segments:
        segments.append(f'<div class="answer-prose">{_render_prose_html(text, include_citations=include_citations)}</div>')

    return Markup("".join(segments))





def start_active_job(model: str, query: str) -> str:
    job_id = uuid.uuid4().hex
    with ACTIVE_LOCK:
        ACTIVE_JOB["id"] = job_id
        ACTIVE_JOB["cancel_requested"] = False
        ACTIVE_JOB["model"] = model
        ACTIVE_JOB["query"] = query
        ACTIVE_JOB["started_at"] = time.time()
        ACTIVE_JOB["stage"] = "Preparando pergunta"
    return job_id


def finish_active_job(job_id: str) -> None:
    with ACTIVE_LOCK:
        if ACTIVE_JOB.get("id") == job_id:
            ACTIVE_JOB["id"] = None
            ACTIVE_JOB["cancel_requested"] = False
            ACTIVE_JOB["model"] = None
            ACTIVE_JOB["query"] = None
            ACTIVE_JOB["started_at"] = None
            ACTIVE_JOB["stage"] = None


def update_active_job_stage(job_id: str, stage: str) -> None:
    with ACTIVE_LOCK:
        if ACTIVE_JOB.get("id") == job_id:
            ACTIVE_JOB["stage"] = stage


def active_job_cancelled(job_id: str) -> bool:
    with ACTIVE_LOCK:
        return ACTIVE_JOB.get("id") == job_id and bool(ACTIVE_JOB.get("cancel_requested"))


def active_jobs_snapshot() -> List[Dict[str, Any]]:
    with ACTIVE_LOCK:
        if not ACTIVE_JOB.get("id"):
            return []
        started = ACTIVE_JOB.get("started_at") or time.time()
        age = max(0, int(time.time() - float(started)))
        query = str(ACTIVE_JOB.get("query") or "")
        return [
            {
                "id": ACTIVE_JOB.get("id"),
                "model": ACTIVE_JOB.get("model"),
                "query": query,
                "query_short": query[:140] + ("..." if len(query) > 140 else ""),
                "started_at_ts": started,
                "age_seconds": age,
                "stage": ACTIVE_JOB.get("stage") or "Rodando",
                "cancel_requested": bool(ACTIVE_JOB.get("cancel_requested")),
            }
        ]

def resource_limits() -> Dict[str, int | str]:
    return {
        "default_max_results": as_int(os.getenv("DEFAULT_MAX_RESULTS", "3"), 3) or 3,
        "max_results_cap": as_int(os.getenv("MAX_RESULTS_CAP", "5"), 5) or 5,
        "max_source_chars": as_int(os.getenv("MAX_SOURCE_CHARS", "1200"), 1200) or 1200,
        "max_total_source_chars": as_int(os.getenv("MAX_TOTAL_SOURCE_CHARS", "4500"), 4500) or 4500,
        "num_ctx": as_int(os.getenv("OLLAMA_NUM_CTX", "2048"), 2048) or 2048,
        "num_predict": as_int(os.getenv("OLLAMA_NUM_PREDICT", "512"), 512) or 512,
        "num_thread": as_int(os.getenv("OLLAMA_NUM_THREAD", "2"), 2) or 2,
        "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "0"),
        "request_timeout": as_int(os.getenv("OLLAMA_REQUEST_TIMEOUT", "600"), 600) or 600,
        "busy_reject": os.getenv("APP_BUSY_REJECT", "1") == "1",
    }

def default_model() -> str:
    return os.getenv("OLLAMA_MODEL", "gemma3:4b")


def app_port() -> int:
    return int(os.getenv("APP_PORT", "5388"))


def app_host() -> str:
    return os.getenv("APP_HOST", "127.0.0.1")


def build_prompt(query: str, sources: List[Dict[str, Any]], mode: str, task_group: str = "auto") -> str:
    limits = resource_limits()
    max_source_chars = int(limits["max_source_chars"])
    max_total_source_chars = int(limits["max_total_source_chars"])

    sources_text = []
    total_chars = 0
    for index, source in enumerate(sources, start=1):
        raw_content = str(source.get("content", ""))
        content = raw_content[:max_source_chars]
        if len(raw_content) > max_source_chars:
            content = content.rstrip() + "... [trecho cortado para economizar RAM]"

        block = f"""
[{index}]
Título: {source.get('title', 'Sem título')}
URL: {source.get('url', '')}
Trecho: {content}
""".strip()

        if sources_text and total_chars + len(block) > max_total_source_chars:
            sources_text.append("[fontes adicionais cortadas para reduzir uso de memória]")
            break

        sources_text.append(block)
        total_chars += len(block)

    style_map = {
        "direto": "Responda de forma direta, prática e objetiva.",
        "detalhado": "Responda com detalhes, contexto, prós, contras e próximos passos.",
        "web": "Responda como um pesquisador web: use as fontes, compare informações, destaque dados úteis, explique incertezas, cite referências no formato [1], [2] e entregue uma conclusão prática. Se a pergunta envolver preço, produto ou anúncio, estime faixa realista com base nas fontes.",
        "mercado": "Responda como um pesquisador web: use as fontes, compare informações, destaque dados úteis, explique incertezas, cite referências no formato [1], [2] e entregue uma conclusão prática. Se a pergunta envolver preço, produto ou anúncio, estime faixa realista com base nas fontes.",
        "vendedor": "Responda como um pesquisador web: use as fontes, compare informações, destaque dados úteis, explique incertezas, cite referências no formato [1], [2] e entregue uma conclusão prática. Se a pergunta envolver preço, produto ou anúncio, estime faixa realista com base nas fontes.",
        "tecnico": "Responda como um técnico/programador: inclua passos, comandos e alertas objetivos quando fizer sentido.",
    }
    instruction = style_map.get(mode, style_map["direto"])
    task_map = {
        "auto": "Escolha a melhor estratégia pelo conteúdo da pergunta.",
        "all": "Use uma estratégia ampla e deixe claro quando algo dependeria de mais validação.",
        "local_fast": "Priorize resposta local leve, curta e prática.",
        "web_price": "Priorize comparação, preços, atualidade, fontes e incertezas.",
        "code_tech": "Priorize diagnóstico técnico, comandos, passos e cuidados.",
        "academic": "Priorize evidência, cautela, metodologia e limitações.",
        "math": "Priorize cálculo exato, fórmula e conferência do resultado.",
    }
    task_instruction = task_map.get(task_group, f"Perfil solicitado: {task_group}.")

    if not sources_text:
        return f"""
Você recebeu uma pergunta do usuário.

Sua missão:
- Responder em português do Brasil.
- Usar apenas seu conhecimento local/contexto do modelo.
- Não diga que pesquisou na web.
- Não cite fontes no formato [1], [2], [3], porque nenhuma fonte web foi usada nesta execução.
- Se não tiver certeza ou a pergunta depender de informação atual, diga claramente que o modo Pesquisa Web seria mais adequado.
- {instruction}
- Grupo/tarefa: {task_instruction}

Pergunta do usuário:
{query}

Resposta final:
""".strip()

    return f"""
Você recebeu uma pergunta do usuário e resultados de busca na web.

Sua missão:
- Responder em português do Brasil.
- Usar as fontes abaixo quando a resposta depender de informação atual.
- Citar fontes no formato [1], [2], [3].
- Não inventar dados.
- Se as fontes forem insuficientes, diga claramente.
- Não cite uma fonte se ela não sustentar a afirmação.
- {instruction}
- Grupo/tarefa: {task_instruction}

Pergunta do usuário:
{query}

Fontes:
{chr(10).join(sources_text)}

Resposta final:
""".strip()


def get_models_for_ui() -> List[Dict[str, Any]]:
    return model_catalog_with_status(list_models(), default_model())


def engine_dropdowns_for_ui(env: Dict[str, str]) -> Dict[str, List[Dict[str, str]]]:
    active = [p for p in providers_for_ui(env, mask_secret) if p.get("enabled") and p.get("configured")]

    response = [
        {"id": "auto", "label": "Auto", "hint": "Escolhe o melhor motor disponível"},
        {"id": "all", "label": "Todos", "hint": "Usar/combinar todos os motores disponíveis"},
        {"id": "ollama", "label": "Ollama local", "hint": "Seu PC, sem cloud para gerar resposta"},
        {"id": "web_cloud", "label": "Web/Cloud (sem Ollama local)", "hint": "Gera a resposta em uma IA externa ativa/configurada"},
    ]
    search = [
        {"id": "auto", "label": "Auto", "hint": "Escolhe a melhor busca disponível"},
        {"id": "all", "label": "Todos", "hint": "Usar/combinar buscadores ativos"},
        {"id": "local_only", "label": "Somente local (sem web)", "hint": "Não usa web/API de busca; manda direto para o modelo local/selecionado"},
    ]
    if env.get("OLLAMA_API_KEY"):
        search.append({"id": "ollama_web", "label": "Ollama Web Search", "hint": "Busca web oficial da Ollama"})

    task_groups = [
        {"id": "auto", "label": "Auto", "hint": "O app decide pelo tipo da pergunta"},
        {"id": "all", "label": "Todos", "hint": "Usa estratégia ampla/multi-etapa"},
        {"id": "local_fast", "label": "Local leve", "hint": "Explicação, resumo, reescrita, tarefas sem dado atual"},
        {"id": "web_price", "label": "Web / preço / notícia", "hint": "Coisas atuais, produtos, anúncios, documentação recente"},
        {"id": "code_tech", "label": "Código / técnico", "hint": "Windows, Python, debug, scripts e comandos"},
        {"id": "academic", "label": "Acadêmico", "hint": "Artigos, evidência científica, papers, revisão"},
        {"id": "math", "label": "Matemática / cálculo", "hint": "Conta, fórmula, Wolfram, resultado exato"},
    ]

    response_categories = {"LLM", "Busca + LLM", "Assistente"}
    search_categories = {"Busca", "Busca neural", "Busca + IA", "Busca + LLM", "Websets"}
    academic_categories = {"Pesquisa acadêmica"}
    math_categories = {"Cálculo/conhecimento"}

    for p in active:
        item = {"id": p["id"], "label": p["name"], "hint": p.get("category", "")}
        category = p.get("category")
        if category in response_categories:
            response.append(item)
        if category in search_categories:
            search.append(item)
        if category in academic_categories:
            task_groups.append({"id": p["id"], "label": p["name"], "hint": "Pesquisa acadêmica configurada"})
        if category in math_categories:
            task_groups.append({"id": p["id"], "label": p["name"], "hint": "Cálculo/conhecimento configurado"})

    return {"response": response, "search": search, "task_groups": task_groups}


def installed_model_names() -> List[str]:
    return list_models()


def is_model_installed(model_name: str) -> bool:
    wanted = normalize_model_name(model_name)
    if not wanted:
        return False
    installed = {normalize_model_name(name) for name in installed_model_names()}
    if wanted in installed:
        return True
    # If user selected an alias without tag, accept matching base model.
    wanted_base = wanted.split(":", 1)[0]
    return ":" not in wanted and any(name.split(":", 1)[0] == wanted_base for name in installed)


def is_safe_model_name(model_name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}", str(model_name or "")))


def model_task_snapshot() -> Dict[str, Any]:
    with MODEL_TASK_LOCK:
        return dict(MODEL_TASK)


def update_model_task(**updates: Any) -> None:
    with MODEL_TASK_LOCK:
        MODEL_TASK.update(updates)


def _append_model_task_line(line: str) -> None:
    cleaned = str(line or "").replace("\r", "").strip()
    if not cleaned:
        return
    with MODEL_TASK_LOCK:
        lines = list(MODEL_TASK.get("lines") or [])
        lines.append(cleaned)
        MODEL_TASK["lines"] = lines[-16:]
        MODEL_TASK["message"] = cleaned[-500:]


def _run_pull_model_task(task_id: str, model_name: str) -> None:
    update_model_task(status="running", message=f"Baixando {model_name}...", ok=None)
    try:
        proc = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        if proc.stdout:
            for line in proc.stdout:
                with MODEL_TASK_LOCK:
                    if MODEL_TASK.get("id") != task_id:
                        break
                _append_model_task_line(line)
        return_code = proc.wait()
        if return_code == 0:
            update_model_task(running=False, status="done", message=f"Modelo {model_name} baixado com sucesso.", finished_at=time.time(), ok=True)
        else:
            update_model_task(running=False, status="error", message=f"Falha ao baixar {model_name}. Código {return_code}.", finished_at=time.time(), ok=False)
    except Exception as exc:  # noqa: BLE001
        update_model_task(running=False, status="error", message=f"Erro ao baixar {model_name}: {exc}", finished_at=time.time(), ok=False)


@app.before_request
def ensure_db() -> None:
    init_db()


@app.route("/", methods=["GET", "POST"])
def index():
    models = get_models_for_ui()
    selected_model = request.form.get("model", default_model()) if request.method == "POST" else default_model()
    env = read_env_file()
    engine_dropdowns = engine_dropdowns_for_ui(env)

    limits = resource_limits()

    context = {
        "models": models,
        "selected_model": selected_model,
        "default_model": default_model(),
        "query": "",
        "answer": None,
        "answer_html": None,
        "answer_full_html": None,
        "sources": [],
        "error": None,
        "saved_id": None,
        "max_results": limits["default_max_results"],
        "max_results_cap": limits["max_results_cap"],
        "resource_limits": limits,
        "temperature": 0.2,
        "mode": "direto",
        "execution_profile": "standard",
        "response_engine": "auto",
        "search_engine": "auto",
        "task_group": "auto",
        "engine_dropdowns": engine_dropdowns,
        "ollama_status": check_ollama(),
        "busy_job": None,
        "pc_stats_enabled": env.get("PC_STATS_ENABLED", "0") == "1",
    }

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        model = request.form.get("model", default_model()).strip() or default_model()
        mode = request.form.get("mode", "direto").strip() or "direto"
        execution_profile = request.form.get("execution_profile", "standard").strip() or "standard"
        response_engine = request.form.get("response_engine", "auto").strip() or "auto"
        search_engine = request.form.get("search_engine", "auto").strip() or "auto"
        task_group = request.form.get("task_group", "auto").strip() or "auto"

        # Perfil de execução: controla os menus visíveis e também garante o comportamento no backend.
        if execution_profile == "local_only":
            mode = "direto"
            response_engine = "ollama"
            search_engine = "local_only"
            task_group = "local_fast"
        elif execution_profile == "web":
            mode = "web"
            if search_engine == "local_only":
                search_engine = "auto"
            if task_group == "auto":
                task_group = "web_price"
        elif execution_profile == "cloud_web":
            mode = "web"
            response_engine = "web_cloud"
            if search_engine == "local_only":
                search_engine = "auto"
            if task_group == "auto":
                task_group = "web_price"
        elif execution_profile == "all":
            mode = "web"
            response_engine = "all"
            search_engine = "all"
            task_group = "all"
        elif execution_profile not in {"standard", "advanced", "cloud_web"}:
            execution_profile = "standard"

        try:
            max_results = max(1, min(int(request.form.get("max_results", str(limits["default_max_results"]))), int(limits["max_results_cap"])))
        except ValueError:
            max_results = int(limits["default_max_results"])

        try:
            temperature = float(request.form.get("temperature", "0.2"))
            temperature = max(0.0, min(temperature, 1.5))
        except ValueError:
            temperature = 0.2

        context.update(
            {
                "query": query,
                "selected_model": model,
                "max_results": max_results,
                "temperature": temperature,
                "mode": mode,
                "execution_profile": execution_profile,
                "response_engine": response_engine,
                "search_engine": search_engine,
                "task_group": task_group,
            }
        )

        use_cloud_response = is_cloud_response_engine(response_engine)

        if not query:
            context["error"] = "Digite uma pergunta antes de pesquisar."
            return render_template("index.html", **context)

        if not use_cloud_response and not is_model_installed(model):
            context["error"] = f"O modelo {model} ainda não está instalado. Rode: ollama pull {model}"
            return render_template("index.html", **context)

        sources: List[Dict[str, Any]] = []
        prompt = ""
        rate_headers: Dict[str, str] = {}
        acquired = False

        if limits["busy_reject"]:
            acquired = JOB_LOCK.acquire(blocking=False)
            if not acquired:
                jobs = active_jobs_snapshot()
                context["busy_job"] = jobs[0] if jobs else None
                context["error"] = (
                    "Já tem uma pesquisa/resposta rodando. Você pode esperar, cancelar o trabalho anterior ou cancelar e tentar esta nova pergunta."
                )
                return render_template("index.html", **context)
        else:
            JOB_LOCK.acquire()
            acquired = True

        job_id = start_active_job("Web/Cloud" if use_cloud_response else model, query)

        try:
            uses_web = mode in {"web", "mercado", "vendedor"} and search_engine != "local_only"
            if uses_web:
                update_active_job_stage(job_id, f"Buscando fontes na web ({search_engine})")
                sources, rate_headers = web_search(query, max_results=max_results)
                if active_job_cancelled(job_id):
                    raise OllamaError("Execução interrompida pelo usuário antes de chamar o modelo.")
            else:
                stage_label = "Busca local: sem web/API externa" if search_engine == "local_only" else "Modo local: pulando busca web"
                update_active_job_stage(job_id, stage_label)
                sources = []
                rate_headers = {}

            update_active_job_stage(job_id, "Organizando prompt")
            prompt = build_prompt(query=query, sources=sources, mode=mode, task_group=task_group)
            if active_job_cancelled(job_id):
                raise OllamaError("Execução interrompida pelo usuário antes da resposta.")

            if use_cloud_response:
                update_active_job_stage(job_id, f"Chamando motor Web/Cloud ({response_engine})")
                ai_result = cloud_chat(
                    prompt=prompt,
                    env=env,
                    response_engine=response_engine,
                    temperature=temperature,
                    should_cancel=lambda: active_job_cancelled(job_id),
                )
                model_label = ai_result.get("model_label", "Web/Cloud")
            else:
                update_active_job_stage(job_id, "Chamando Ollama local e gerando resposta")
                ai_result = chat(prompt=prompt, model=model, temperature=temperature, should_cancel=lambda: active_job_cancelled(job_id))
                model_label = model

            if active_job_cancelled(job_id):
                raise OllamaError("Execução interrompida pelo usuário.")

            update_active_job_stage(job_id, "Salvando histórico e preparando tela")
            answer = ai_result["content"]
            metrics = ai_result.get("metrics", {})
            saved_id = add_history(query, answer, model_label, max_results, sources)

            add_usage_log(
                query=query,
                model=model_label,
                web_ok=True,
                chat_ok=True,
                source_count=len(sources),
                prompt_chars=len(prompt),
                answer_chars=len(answer),
                metrics=metrics,
                rate_headers=rate_headers,
            )

            context.update({"answer": answer, "answer_html": render_answer_html(answer, include_citations=False, strip_sources_section=True), "answer_full_html": render_answer_html(answer, include_citations=True, strip_sources_section=False), "sources": sources, "saved_id": saved_id})
        except (SearchError, OllamaError, CloudAIError) as exc:
            add_usage_log(
                query=query,
                model=model,
                web_ok=bool(sources),
                chat_ok=False,
                source_count=len(sources),
                prompt_chars=len(prompt),
                error_message=str(exc),
                rate_headers=rate_headers,
            )
            context["error"] = str(exc)
        except Exception as exc:  # noqa: BLE001
            add_usage_log(
                query=query,
                model=model,
                web_ok=bool(sources),
                chat_ok=False,
                source_count=len(sources),
                prompt_chars=len(prompt),
                error_message=f"Erro inesperado: {exc}",
                rate_headers=rate_headers,
            )
            context["error"] = f"Erro inesperado: {exc}"
        finally:
            finish_active_job(job_id)
            if acquired:
                JOB_LOCK.release()

    return render_template("index.html", **context)


@app.route("/history")
def history():
    return render_template("history.html", items=list_history(limit=200))


@app.route("/history/<int:item_id>")
def history_detail(item_id: int):
    item = get_history(item_id)
    if not item:
        return redirect(url_for("history"))
    return render_template("history_detail.html", item=item, answer_html=render_answer_html(item.get("answer", ""), include_citations=False, strip_sources_section=True), answer_full_html=render_answer_html(item.get("answer", ""), include_citations=True, strip_sources_section=False))


@app.route("/history/<int:item_id>/delete", methods=["POST"])
def history_delete(item_id: int):
    delete_history(item_id)
    return redirect(url_for("history"))


@app.route("/history/clear", methods=["POST"])
def history_clear():
    clear_history()
    return redirect(url_for("history"))


@app.route("/api/pc-stats")
def api_pc_stats():
    env = read_env_file()
    if env.get("PC_STATS_ENABLED", "0") != "1":
        return jsonify({"ok": False, "enabled": False, "message": "Stats do PC desativados em Configurações."})
    data = collect_pc_stats()
    data["enabled"] = True
    return jsonify(data)


@app.route("/status")
def status():
    env = read_env_file()
    stats = usage_stats()
    limits = {
        "hour": as_int(env.get("API_HOURLY_LIMIT", "0")),
        "day": as_int(env.get("API_DAILY_LIMIT", "0")),
        "week": as_int(env.get("API_WEEKLY_LIMIT", "0")),
        "month": as_int(env.get("API_MONTHLY_LIMIT", "0")),
    }
    return render_template(
        "status.html",
        stats=stats,
        limits=limits,
        recent_logs=recent_usage_logs(limit=15),
        api_key_masked=mask_secret(env.get("OLLAMA_API_KEY", "")),
        local_url=os.getenv("OLLAMA_LOCAL_URL", "http://127.0.0.1:11434"),
        default_model=default_model(),
        app_host=app_host(),
        app_port=app_port(),
        ollama_status=check_ollama(),
        models=list_models(),
        model_catalog=get_models_for_ui(),
        resource_limits=resource_limits(),
        active_jobs=active_jobs_snapshot(),
        ai_providers=providers_for_ui(env, mask_secret),
        pc_stats_enabled=env.get("PC_STATS_ENABLED", "0") == "1",
    )


def _parse_settings_import(raw_text: str) -> Dict[str, str]:
    cleaned = raw_text.strip()
    if not cleaned:
        return {}

    parsed: Dict[str, str] = {}
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            settings_payload = payload.get("settings", payload)
            if isinstance(settings_payload, dict):
                parsed = {str(k): str(v) for k, v in settings_payload.items()}
    except json.JSONDecodeError:
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()

    return {key: value for key, value in parsed.items() if key in DEFAULTS}


@app.route("/settings/export")
def settings_export():
    env = read_env_file()
    payload = {
        "app": "Ollama Web Platform",
        "format": "settings-export-v1",
        "warning": "Este arquivo inclui API keys e segredos salvos. Não envie para GitHub nem compartilhe publicamente.",
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "settings": env,
    }
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return send_file(
        BytesIO(data),
        mimetype="application/json",
        as_attachment=True,
        download_name=f"ollama_web_platform_settings_{time.strftime('%Y%m%d_%H%M%S')}.json",
    )


@app.route("/settings/import", methods=["POST"])
def settings_import():
    uploaded = request.files.get("config_file")
    if not uploaded or not uploaded.filename:
        return redirect(url_for("settings", import_error="1"))
    try:
        raw = uploaded.read().decode("utf-8-sig", errors="replace")
        updates = _parse_settings_import(raw)
        if not updates:
            return redirect(url_for("settings", import_error="1"))
        write_env_file(updates)
        load_dotenv(override=True)
        return redirect(url_for("settings", imported="1"))
    except Exception:  # noqa: BLE001
        return redirect(url_for("settings", import_error="1"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    message = None
    error = None
    if request.args.get("exported") == "1":
        message = "Configurações exportadas. Guarde esse arquivo com cuidado: ele inclui API keys."
    if request.args.get("imported") == "1":
        message = "Configurações importadas com sucesso. Reinicie o app se alterou host, porta, modelo padrão ou chaves em uso."
    if request.args.get("import_error") == "1":
        error = "Não consegui importar as configurações. Verifique se o arquivo é um JSON exportado pelo app ou um .env válido."
    env = read_env_file()

    if request.method == "POST":
        try:
            clear_key = request.form.get("clear_api_key") == "on"
            new_key = request.form.get("new_api_key", "").strip()

            updates = {
                "OLLAMA_LOCAL_URL": request.form.get("ollama_local_url", env.get("OLLAMA_LOCAL_URL", "")).strip(),
                "OLLAMA_MODEL": request.form.get("ollama_model", env.get("OLLAMA_MODEL", "")).strip(),
                "APP_HOST": request.form.get("app_host", env.get("APP_HOST", "127.0.0.1")).strip(),
                "APP_PORT": request.form.get("app_port", env.get("APP_PORT", "5388")).strip(),
                "FLASK_DEBUG": "1" if request.form.get("flask_debug") == "on" else "0",
                "API_HOURLY_LIMIT": request.form.get("api_hourly_limit", "0").strip() or "0",
                "API_DAILY_LIMIT": request.form.get("api_daily_limit", "0").strip() or "0",
                "API_WEEKLY_LIMIT": request.form.get("api_weekly_limit", "0").strip() or "0",
                "API_MONTHLY_LIMIT": request.form.get("api_monthly_limit", "0").strip() or "0",
                "DEFAULT_MAX_RESULTS": request.form.get("default_max_results", "3").strip() or "3",
                "MAX_RESULTS_CAP": request.form.get("max_results_cap", "5").strip() or "5",
                "MAX_SOURCE_CHARS": request.form.get("max_source_chars", "1200").strip() or "1200",
                "MAX_TOTAL_SOURCE_CHARS": request.form.get("max_total_source_chars", "4500").strip() or "4500",
                "OLLAMA_NUM_CTX": request.form.get("ollama_num_ctx", "2048").strip() or "2048",
                "OLLAMA_NUM_PREDICT": request.form.get("ollama_num_predict", "512").strip() or "512",
                "OLLAMA_NUM_THREAD": request.form.get("ollama_num_thread", "2").strip() or "2",
                "OLLAMA_KEEP_ALIVE": request.form.get("ollama_keep_alive", "0").strip() or "0",
                "OLLAMA_REQUEST_TIMEOUT": request.form.get("ollama_request_timeout", "600").strip() or "600",
                "APP_BUSY_REJECT": "1" if request.form.get("app_busy_reject") == "on" else "0",
                "PC_STATS_ENABLED": "1" if request.form.get("pc_stats_enabled") == "on" else "0",
            }

            if clear_key:
                updates["OLLAMA_API_KEY"] = ""
            elif new_key:
                updates["OLLAMA_API_KEY"] = new_key
            else:
                updates["OLLAMA_API_KEY"] = env.get("OLLAMA_API_KEY", "")

            activate_all_with_keys = request.form.get("activate_all_with_keys") == "on"
            for provider in AI_PROVIDERS:
                key_env = provider["key_env"]
                enabled_env = provider["enabled_env"]
                new_provider_key = request.form.get(f"provider_key_{provider['id']}", "").strip()
                clear_provider_key = request.form.get(f"provider_clear_{provider['id']}") == "on"
                if clear_provider_key:
                    final_key = ""
                elif new_provider_key:
                    final_key = new_provider_key
                else:
                    final_key = env.get(key_env, "")
                enabled = request.form.get(f"provider_enabled_{provider['id']}") == "on"
                if activate_all_with_keys:
                    enabled = bool(final_key)
                updates[key_env] = final_key
                updates[enabled_env] = "1" if enabled else "0"

            env = write_env_file(updates)
            load_dotenv(override=True)
            message = "Configurações salvas. Se você mudou host/porta, reinicie o run.bat."
        except Exception as exc:  # noqa: BLE001
            error = f"Não consegui salvar: {exc}"

    return render_template(
        "settings.html",
        env=env,
        message=message,
        error=error,
        api_key_masked=mask_secret(env.get("OLLAMA_API_KEY", "")),
        models=get_models_for_ui(),
        ai_providers=providers_for_ui(env, mask_secret),
    )


@app.route("/api/ollama-api/save", methods=["POST"])
def api_ollama_api_save():
    payload = request.get_json(silent=True) or {}
    new_key = str(payload.get("api_key", "")).strip()
    env = read_env_file()
    final_key = new_key if new_key else env.get("OLLAMA_API_KEY", "")
    env = write_env_file({"OLLAMA_API_KEY": final_key})
    load_dotenv(override=True)
    return jsonify({"ok": True, "message": "API da Ollama salva.", "masked_key": mask_secret(env.get("OLLAMA_API_KEY", ""))})


@app.route("/api/ollama-api/clear", methods=["POST"])
def api_ollama_api_clear():
    env = write_env_file({"OLLAMA_API_KEY": ""})
    load_dotenv(override=True)
    return jsonify({"ok": True, "message": "API da Ollama removida.", "masked_key": mask_secret(env.get("OLLAMA_API_KEY", ""))})


@app.route("/api/ollama-api/test", methods=["POST"])
def api_ollama_api_test():
    env = read_env_file()
    api_key = env.get("OLLAMA_API_KEY", "")
    if not api_key:
        return jsonify({"ok": False, "message": "API key da Ollama não definida."})
    os.environ["OLLAMA_API_KEY"] = api_key
    try:
        sources, _headers = web_search("teste de conexão", max_results=1)
        return jsonify({"ok": True, "message": f"Conexão OK. Fontes retornadas: {len(sources)}."})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "message": f"Falha ao testar: {exc}"})


@app.route("/api/providers/save", methods=["POST"])
def api_provider_save():
    payload = request.get_json(silent=True) or {}
    provider_id = str(payload.get("provider", "")).strip()
    provider = provider_by_id(provider_id)
    if not provider:
        return jsonify({"ok": False, "message": "Provedor não encontrado."}), 404

    env = read_env_file()
    new_key = str(payload.get("api_key", "")).strip()
    enabled = bool(payload.get("enabled", False))
    final_key = new_key if new_key else env.get(provider["key_env"], "")

    updates = {
        provider["key_env"]: final_key,
        provider["enabled_env"]: "1" if enabled else "0",
    }
    env = write_env_file(updates)
    load_dotenv(override=True)
    return jsonify({
        "ok": True,
        "message": "API salva para este serviço.",
        "provider": provider_id,
        "masked_key": mask_secret(env.get(provider["key_env"], "")),
        "configured": bool(env.get(provider["key_env"], "")),
        "enabled": env.get(provider["enabled_env"], "0") == "1",
    })


@app.route("/api/providers/clear", methods=["POST"])
def api_provider_clear():
    payload = request.get_json(silent=True) or {}
    provider_id = str(payload.get("provider", "")).strip()
    provider = provider_by_id(provider_id)
    if not provider:
        return jsonify({"ok": False, "message": "Provedor não encontrado."}), 404

    env = write_env_file({provider["key_env"]: "", provider["enabled_env"]: "0"})
    load_dotenv(override=True)
    return jsonify({
        "ok": True,
        "message": "Chave apagada e serviço desativado.",
        "provider": provider_id,
        "masked_key": mask_secret(env.get(provider["key_env"], "")),
        "configured": False,
        "enabled": False,
    })


@app.route("/api/providers/test", methods=["POST"])
def api_provider_test():
    payload = request.get_json(silent=True) or {}
    provider_id = str(payload.get("provider", "")).strip()
    provider = provider_by_id(provider_id)
    if not provider:
        return jsonify({"ok": False, "message": "Provedor não encontrado."}), 404
    env = read_env_file()
    api_key = env.get(provider["key_env"], "")
    result = test_provider_connection(provider, api_key)
    result["provider"] = provider_id
    result["name"] = provider.get("name")
    return jsonify(result)


@app.route("/export/<int:item_id>/<fmt>")
def export_item(item_id: int, fmt: str):
    item = get_history(item_id)
    if not item:
        return Response("Item não encontrado", status=404)

    fmt = fmt.lower()
    base_name = f"ollama_web_resposta_{item_id}"

    if fmt == "json":
        payload = json.dumps(item, ensure_ascii=False, indent=2)
        return _download_text(payload, f"{base_name}.json", "application/json")

    if fmt == "md":
        content = _to_markdown(item)
        return _download_text(content, f"{base_name}.md", "text/markdown")

    if fmt == "txt":
        content = _to_text(item)
        return _download_text(content, f"{base_name}.txt", "text/plain")

    return Response("Formato inválido", status=400)


def force_kill_ollama_processes() -> Dict[str, Any]:
    """Força só o runner do modelo, sem encerrar o app/daemon do Ollama.

    Antes a parada forçada matava `ollama*`, o que fechava o Ollama inteiro.
    Agora tentamos encerrar apenas processos de execução do modelo, como
    `ollama_llama_server.exe`, deixando o Ollama aberto para a próxima pergunta.
    """
    result: Dict[str, Any] = {"called": False, "ok": False, "error": None, "stdout": ""}
    try:
        result["called"] = True
        command = (
            "$targets = Get-Process -ErrorAction SilentlyContinue | "
            "Where-Object { $_.ProcessName -like 'ollama_llama_server*' -or $_.ProcessName -like 'llama-server*' }; "
            "$count = @($targets).Count; "
            "if ($count -gt 0) { $targets | Stop-Process -Force }; "
            "Write-Output ('runners_interrompidos=' + $count)"
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        result["ok"] = proc.returncode == 0
        result["stdout"] = (proc.stdout or "").strip()[:500]
        if proc.returncode != 0:
            result["error"] = (proc.stderr or proc.stdout or "PowerShell retornou erro").strip()[:500]
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
    return result


@app.route("/api/cancel", methods=["POST"])
def api_cancel():
    payload = request.get_json(silent=True) or {}
    wanted_job_id = payload.get("job_id") or request.form.get("job_id")

    with ACTIVE_LOCK:
        has_job = bool(ACTIVE_JOB.get("id"))
        current_job_id = ACTIVE_JOB.get("id")
        if wanted_job_id and wanted_job_id != current_job_id:
            return jsonify({"ok": False, "message": "Esse job não está mais ativo.", "active_jobs": active_jobs_snapshot()})
        ACTIVE_JOB["cancel_requested"] = True
        ACTIVE_JOB["stage"] = "Cancelamento solicitado"
        model = ACTIVE_JOB.get("model")

    if model and is_safe_model_name(str(model)):
        stop_result = stop_model(str(model))
    else:
        stop_result = {"skipped": True, "reason": "Motor web/cloud ou modelo inválido para ollama stop."}

    return jsonify(
        {
            "ok": True,
            "had_active_job": has_job,
            "job_id": current_job_id,
            "model": model,
            "stop_result": stop_result,
            "active_jobs": active_jobs_snapshot(),
            "message": "Cancelamento seguro enviado. O app também tentou descarregar o modelo sem fechar o Ollama.",
        }
    )


@app.route("/api/force_cancel", methods=["POST"])
def api_force_cancel():
    payload = request.get_json(silent=True) or {}
    wanted_job_id = payload.get("job_id") or request.form.get("job_id")

    with ACTIVE_LOCK:
        has_job = bool(ACTIVE_JOB.get("id"))
        current_job_id = ACTIVE_JOB.get("id")
        if wanted_job_id and current_job_id and wanted_job_id != current_job_id:
            return jsonify({"ok": False, "message": "Esse job não está mais ativo.", "active_jobs": active_jobs_snapshot()})
        ACTIVE_JOB["cancel_requested"] = True
        ACTIVE_JOB["stage"] = "Forçando parada do runner do modelo"
        model = ACTIVE_JOB.get("model")

    if model and is_safe_model_name(str(model)):
        stop_result = stop_model(str(model))
    else:
        stop_result = {"skipped": True, "reason": "Motor web/cloud ou modelo inválido para ollama stop."}

    # Forçar agora tenta encerrar só o runner do modelo, não o daemon/app do Ollama.
    kill_result = force_kill_ollama_processes()

    return jsonify(
        {
            "ok": True,
            "had_active_job": has_job,
            "job_id": current_job_id,
            "model": model,
            "stop_result": stop_result,
            "kill_result": kill_result,
            "active_jobs": active_jobs_snapshot(),
            "message": "Parada forçada enviada ao runner do modelo. O Ollama deve continuar aberto.",
        }
    )


@app.route("/api/jobs")
def api_jobs():
    return jsonify({"ok": True, "jobs": active_jobs_snapshot()})


@app.route("/api/status")
def api_status():
    return jsonify(
        {
            "ollama": check_ollama(),
            "default_model": default_model(),
            "api_key_defined": bool(os.getenv("OLLAMA_API_KEY", "")),
            "usage": usage_stats(),
            "models": list_models(),
            "model_catalog": get_models_for_ui(),
            "resource_limits": resource_limits(),
            "active_jobs": active_jobs_snapshot(),
            "model_task": model_task_snapshot(),
        }
    )


@app.route("/api/models/task")
def api_model_task():
    return jsonify({"ok": True, "task": model_task_snapshot()})


@app.route("/api/models/pull", methods=["POST"])
def api_model_pull():
    payload = request.get_json(silent=True) or {}
    model_name = str(payload.get("model") or request.form.get("model") or "").strip()

    if not is_safe_model_name(model_name):
        return jsonify({"ok": False, "message": "Nome de modelo inválido."}), 400

    with MODEL_TASK_LOCK:
        if MODEL_TASK.get("running"):
            return jsonify({"ok": False, "message": "Já existe um download/exclusão de modelo em andamento.", "task": model_task_snapshot()}), 409
        task_id = uuid.uuid4().hex
        MODEL_TASK.update({
            "id": task_id,
            "running": True,
            "action": "pull",
            "model": model_name,
            "status": "queued",
            "message": f"Download de {model_name} iniciado...",
            "lines": [],
            "started_at": time.time(),
            "finished_at": None,
            "ok": None,
        })

    thread = threading.Thread(target=_run_pull_model_task, args=(task_id, model_name), daemon=True)
    thread.start()
    return jsonify({"ok": True, "task": model_task_snapshot(), "message": f"Baixando {model_name}."})


@app.route("/api/models/delete", methods=["POST"])
def api_model_delete():
    payload = request.get_json(silent=True) or {}
    model_name = str(payload.get("model") or request.form.get("model") or "").strip()

    if not is_safe_model_name(model_name):
        return jsonify({"ok": False, "message": "Nome de modelo inválido."}), 400

    with MODEL_TASK_LOCK:
        if MODEL_TASK.get("running"):
            return jsonify({"ok": False, "message": "Existe uma tarefa de modelo em andamento. Aguarde terminar.", "task": model_task_snapshot()}), 409
        task_id = uuid.uuid4().hex
        MODEL_TASK.update({
            "id": task_id,
            "running": True,
            "action": "delete",
            "model": model_name,
            "status": "running",
            "message": f"Excluindo {model_name}...",
            "lines": [],
            "started_at": time.time(),
            "finished_at": None,
            "ok": None,
        })

    try:
        proc = subprocess.run(
            ["ollama", "rm", model_name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
        output = (proc.stdout or proc.stderr or "").strip()
        ok = proc.returncode == 0
        update_model_task(
            running=False,
            status="done" if ok else "error",
            message=(f"Modelo {model_name} excluído." if ok else (output or f"Falha ao excluir {model_name}.")),
            lines=[output] if output else [],
            finished_at=time.time(),
            ok=ok,
        )
        return jsonify({"ok": ok, "task": model_task_snapshot(), "message": MODEL_TASK.get("message")})
    except Exception as exc:  # noqa: BLE001
        update_model_task(running=False, status="error", message=f"Erro ao excluir {model_name}: {exc}", finished_at=time.time(), ok=False)
        return jsonify({"ok": False, "task": model_task_snapshot(), "message": str(exc)}), 500


def _download_text(text: str, filename: str, mimetype: str):
    buffer = BytesIO(text.encode("utf-8"))
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype=mimetype)


def _to_markdown(item: Dict[str, Any]) -> str:
    sources = "\n".join(
        f"- [{i}] [{s.get('title', 'Sem título')}]({s.get('url', '')}) — {s.get('content', '')}"
        for i, s in enumerate(item.get("sources", []), start=1)
    )
    return f"""# Resposta Ollama Web Platform

**Data:** {item.get('created_at')}

**Modelo:** `{item.get('model')}`

## Pergunta

{item.get('query')}

## Resposta

{item.get('answer')}

## Fontes

{sources}
""".strip()


def _to_text(item: Dict[str, Any]) -> str:
    sources = "\n".join(
        f"[{i}] {s.get('title', 'Sem título')}\n{s.get('url', '')}\n{s.get('content', '')}\n"
        for i, s in enumerate(item.get("sources", []), start=1)
    )
    return f"""Resposta Ollama Web Platform

Data: {item.get('created_at')}
Modelo: {item.get('model')}

Pergunta:
{item.get('query')}

Resposta:
{item.get('answer')}

Fontes:
{sources}
""".strip()


if __name__ == "__main__":
    init_db()
    app.run(host=app_host(), port=app_port(), debug=os.getenv("FLASK_DEBUG", "1") == "1", threaded=True)
