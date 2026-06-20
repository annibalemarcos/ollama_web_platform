from __future__ import annotations

from typing import Dict, List
import re


MODEL_CATALOG: List[Dict[str, str]] = [
    {
        "name": "gemma3:270m",
        "size": "~292 MB",
        "level": "Ultra leve",
        "category": "Uso geral leve",
        "good_for": "Testes rápidos, perguntas simples, resumo curto e PC sofrendo.",
        "warning": "Bem limitado para raciocínio longo e código complexo.",
    },
    {
        "name": "qwen3:0.6b",
        "size": "~523 MB",
        "level": "Ultra leve",
        "category": "Raciocínio leve",
        "good_for": "Perguntas simples, respostas rápidas, pequenas análises e uso econômico.",
        "warning": "Pode errar mais em tarefas longas ou muito técnicas.",
    },
    {
        "name": "qwen2.5-coder:0.5b",
        "size": "Muito leve",
        "level": "Ultra leve",
        "category": "Código leve",
        "good_for": "Scripts pequenos, exemplos simples em Python, comandos básicos e ajustes rápidos.",
        "warning": "Não espere arquitetura de app grande ou debug pesado.",
    },
    {
        "name": "llama3.2:1b",
        "size": "~1.3 GB",
        "level": "Leve",
        "category": "Uso geral",
        "good_for": "Resumo, reescrita, conversa básica, perguntas gerais e PC com 16 GB.",
        "warning": "É o modelo seguro quando o PC começa a travar.",
    },
    {
        "name": "qwen2.5:1.5b",
        "size": "Leve",
        "level": "Leve",
        "category": "Uso geral técnico",
        "good_for": "Raciocínio leve, perguntas técnicas, listas, resumo e tarefas gerais.",
        "warning": "Mais esperto que sub-1B, ainda econômico.",
    },
    {
        "name": "qwen2.5-coder:1.5b",
        "size": "Leve",
        "level": "Leve",
        "category": "Código leve/médio",
        "good_for": "Python, scripts, pequenos apps, correção simples e explicação de erros.",
        "warning": "Bom meio-termo para programar sem fritar CPU.",
    },
    {
        "name": "qwen3:1.7b",
        "size": "~1.4 GB",
        "level": "Leve",
        "category": "Raciocínio leve/médio",
        "good_for": "Respostas estruturadas, análise leve, perguntas técnicas e uso geral rápido.",
        "warning": "Ainda é econômico, mas melhor que os modelos tiny.",
    },
    {
        "name": "smollm2:1.7b",
        "size": "~1.8 GB",
        "level": "Leve",
        "category": "Compacto geral",
        "good_for": "Uso on-device, respostas rápidas, resumo e tarefas simples.",
        "warning": "Boa opção para velocidade, não para super inteligência.",
    },
    {
        "name": "llama3.2:3b",
        "size": "~2.0 GB",
        "level": "Leve/médio",
        "category": "Uso geral equilibrado",
        "good_for": "Conversa, resumo, análise, reescrita, uso diário e português razoável.",
        "warning": "Ótimo primeiro modelo principal para seu PC.",
    },
    {
        "name": "llama3.2",
        "size": "~2.0 GB",
        "level": "Leve/médio",
        "category": "Uso geral equilibrado",
        "good_for": "Atalho para o Llama 3.2 padrão, geralmente 3B. Bom para tarefas gerais.",
        "warning": "Se quiser garantir leveza máxima, use llama3.2:1b.",
    },
    {
        "name": "qwen2.5:3b",
        "size": "Médio leve",
        "level": "Médio leve",
        "category": "Uso geral técnico",
        "good_for": "Raciocínio melhor, respostas técnicas, comparações e explicações mais completas.",
        "warning": "Bom equilíbrio antes de partir para 7B.",
    },
    {
        "name": "qwen2.5-coder:3b",
        "size": "Médio leve",
        "level": "Médio leve",
        "category": "Código recomendado",
        "good_for": "Python, Flask, scripts Windows, debug, refatoração e projetos pequenos/médios.",
        "warning": "Minha escolha inicial para código no seu PC.",
    },
    {
        "name": "gemma3:4b",
        "size": "~3.3 GB",
        "level": "Médio",
        "category": "Uso geral forte",
        "good_for": "Português, resumo, análise, explicação, perguntas gerais e tarefas com contexto.",
        "warning": "Boa qualidade sem ir direto para a pancadaria dos 7B+.",
    },
    {
        "name": "qwen3:4b",
        "size": "Médio",
        "level": "Médio",
        "category": "Raciocínio médio",
        "good_for": "Respostas técnicas, análise, raciocínio e tarefas gerais mais elaboradas.",
        "warning": "Pode ser um pouco mais pesado; use modo econômico.",
    },
    {
        "name": "mistral:7b",
        "size": "Pesado",
        "level": "Pesado",
        "category": "Texto geral forte",
        "good_for": "Texto, síntese, análise, respostas diretas e tarefas gerais robustas.",
        "warning": "7B já pode pesar em 16 GB sem GPU boa.",
    },
    {
        "name": "qwen2.5:7b",
        "size": "Pesado",
        "level": "Pesado",
        "category": "Uso geral forte",
        "good_for": "Raciocínio, tarefas técnicas, textos longos, análise e respostas melhores.",
        "warning": "Teste só com limites ativos. Pode deixar o PC lerdo.",
    },
    {
        "name": "qwen2.5-coder:7b",
        "size": "~4.7 GB",
        "level": "Pesado",
        "category": "Código forte",
        "good_for": "Apps Flask, Python maior, debug, refatoração, arquitetura e explicação de erros.",
        "warning": "É bom, mas pode fazer seu PC respirar pela boca.",
    },
    {
        "name": "qwen3:8b",
        "size": "Pesado",
        "level": "Pesado",
        "category": "Raciocínio forte",
        "good_for": "Respostas melhores, análise mais profunda e tarefas técnicas.",
        "warning": "No seu PC, só se 4B/7B estiverem rodando liso.",
    },
    {
        "name": "gemma3:12b",
        "size": "Bem pesado",
        "level": "Bem pesado",
        "category": "Uso geral avançado",
        "good_for": "Mais qualidade em análise, resumo e raciocínio.",
        "warning": "Não recomendo como padrão em 16 GB.",
    },
    {
        "name": "qwen2.5:14b",
        "size": "Bem pesado",
        "level": "Bem pesado",
        "category": "Técnico avançado",
        "good_for": "Respostas técnicas melhores e raciocínio mais forte.",
        "warning": "Grande chance de lentidão/travamento em PC comum.",
    },
    {
        "name": "qwen3:14b",
        "size": "Bem pesado",
        "level": "Bem pesado",
        "category": "Raciocínio avançado",
        "good_for": "Análise complexa, raciocínio e respostas mais completas.",
        "warning": "Use só se você aceitar esperar e ouvir o cooler cantando sertanejo.",
    },
    {
        "name": "qwen2.5-coder:14b",
        "size": "Bem pesado",
        "level": "Bem pesado",
        "category": "Código avançado",
        "good_for": "Projetos maiores, debug complexo e raciocínio de programação mais forte.",
        "warning": "Não é boa ideia como padrão no seu PC.",
    },
    {
        "name": "gemma3:27b",
        "size": "Muito pesado",
        "level": "Muito pesado",
        "category": "Uso geral avançado",
        "good_for": "Qualidade maior em tarefas difíceis e análises longas.",
        "warning": "Para workstation/servidor. No seu PC, é passeio no inferno térmico.",
    },
    {
        "name": "qwen2.5-coder:32b",
        "size": "Brutal",
        "level": "Brutal",
        "category": "Código muito avançado",
        "good_for": "Código complexo, arquitetura, raciocínio pesado e projetos grandes.",
        "warning": "Não recomendo para 16 GB. É bigorna digital.",
    },
    {
        "name": "qwen3:30b",
        "size": "Brutal",
        "level": "Brutal",
        "category": "Raciocínio pesado",
        "good_for": "Tarefas muito exigentes em hardware forte.",
        "warning": "Máquina comum sofre. Use nuvem ou hardware forte.",
    },
    {
        "name": "qwen3:32b",
        "size": "Brutal",
        "level": "Brutal",
        "category": "Raciocínio pesado",
        "good_for": "Análise pesada e tarefas avançadas em máquina forte.",
        "warning": "Não é para PC de 16 GB em uso confortável.",
    },
    {
        "name": "llama3.1:70b",
        "size": "Absurdo",
        "level": "Absurdo",
        "category": "Modelo grande",
        "good_for": "Alta qualidade em hardware parrudo/servidor.",
        "warning": "No seu PC, melhor fingir que nem viu.",
    },
    {
        "name": "qwen3:235b",
        "size": "NASA caseira",
        "level": "NASA caseira",
        "category": "MoE gigante",
        "good_for": "Infraestrutura de verdade, servidores e uso cloud.",
        "warning": "Não rode localmente no seu PC. Sério. Sem heroísmo.",
    },
    {
        "name": "llama3.1:405b",
        "size": "Evento astronômico",
        "level": "Evento astronômico",
        "category": "Modelo gigante",
        "good_for": "Data center, servidor monstruoso ou cloud.",
        "warning": "No Windows 10 com 16 GB, isso é fanfic tecnológica.",
    },
]


def normalize_model_name(name: str) -> str:
    return (name or "").strip().lower()


def _has_size(text: str, size: str) -> bool:
    pattern = r"(^|[:\s\-])" + re.escape(size) + r"($|[\s\-])"
    return re.search(pattern, text) is not None


def _has_any_size(text: str, sizes: List[str]) -> bool:
    return any(_has_size(text, size) for size in sizes)


def _is_tiny(text: str) -> bool:
    return _has_any_size(text, ["270m", "0.6b", "0.5b", "135m", "360m"])


def _is_light(text: str) -> bool:
    return _has_any_size(text, ["1b", "1.5b", "1.7b"])


def _is_heavy(text: str) -> bool:
    return _has_any_size(text, ["7b", "8b", "12b", "14b", "27b", "30b", "32b", "70b", "235b", "405b"])


def _is_web_recommended(text: str) -> bool:
    if "coder" in text or _is_tiny(text):
        return False
    if "llama3.2:1b" in text:
        return False
    if "smollm" in text:
        return False
    if "llama3.2" in text:
        return True
    if "gemma3:4b" in text or "gemma3 4b" in text:
        return True
    if "gemma" in text and _has_any_size(text, ["12b", "27b"]):
        return True
    if ("qwen3" in text or "qwen2.5" in text) and _has_any_size(text, ["3b", "4b", "7b", "8b", "14b"]):
        return True
    if "mistral" in text:
        return True
    return False


def model_hint_for(name: str, category: str, level: str) -> str:
    text = f"{name} {category} {level}".lower()

    if "coder" in text:
        if _has_any_size(text, ["0.5b", "1.5b"]):
            return "💻 Código leve: bom para scripts pequenos, exemplos em Python, comandos Windows e ajustes rápidos. Não é bom para pesquisa web geral nem para perguntas nonsense; use só para dúvida técnica simples."
        if _has_any_size(text, ["3b", "7b"]):
            return "💻 Código/sistemas: bom para Python, Flask, debug, refatoração, apps pequenos/médios e explicar erros. Serve para ler documentação técnica que veio da web, mas não é o melhor para comparar anúncios, preços ou notícias."
        return "💻 Código avançado: forte para arquitetura, debug complexo e projetos grandes. Pesado e especializado; não use para pesquisa casual na web ou pergunta criativa."

    if _is_tiny(text):
        return "🪶 Ultra leve: bom para teste rápido, pergunta simples e resumo curtinho. Não recomendo para pesquisa web com várias fontes, comparação de preços ou análise séria; falta fôlego."

    if _is_light(text):
        if "llama3.2:1b" in text:
            return "⚡ Leve emergencial: bom para perguntas rápidas, resumo curto e PC sofrendo. Para web, só consulta simples com 1–2 fontes; para preço/busca web, prefira llama3.2 ou gemma3:4b."
        return "⚡ Leve e econômico: bom para perguntas rápidas, resumo, reescrita e curiosidades simples. Não é minha escolha para pesquisa web com várias fontes nem para código complexo."

    if "llama3.2" in text:
        return "🧭 Geral equilibrado: bom para conversa, resumo, reescrita, perguntas nonsense leves e pesquisa web simples/média com fontes. Código básico/médio ok, mas não é especialista."

    if "gemma3:4b" in text or "gemma3 4b" in text:
        return "🌐 Melhor equilíbrio para web no seu PC: bom em português, pesquisa com fontes, comparação de anúncios/preços, resumo e análise. Também vai bem em perguntas criativas/nonsense. Código pequeno ok, mas app grande pede Qwen Coder."

    if "gemma" in text and _has_any_size(text, ["12b", "27b"]):
        return "🌐 Texto/análise de alta qualidade: bom para pesquisa web, resumo longo e interpretação, mas é pesado para seu PC. Use só se aceitar lentidão."

    if "qwen3" in text or "qwen2.5" in text:
        if _has_any_size(text, ["3b", "4b"]):
            return "🧠 Raciocínio técnico leve/médio: bom para perguntas técnicas, comparação estruturada, listas, análise e pesquisa web objetiva. Menos criativo/nonsense que Gemma/Llama."
        if _has_any_size(text, ["7b", "8b"]):
            return "🧠 Raciocínio forte: bom para pesquisa web exigente, análise técnica, comparação e respostas melhores. Pode pesar; mantenha modo econômico ligado."
        return "🧠 Raciocínio avançado: bom para análise complexa, mas pesado demais para uso confortável no seu PC. Não é escolha de rotina."

    if "mistral" in text:
        return "✍️ Texto direto e robusto: bom para síntese, explicações, respostas objetivas e pesquisa web geral. Não é o mais leve; teste com cuidado."

    if _has_any_size(text, ["70b", "235b", "405b", "30b", "32b"]):
        return "🚧 Modelo gigante: ótimo em teoria para raciocínio e qualidade, mas não é indicado para seu PC local. Melhor usar via cloud ou máquina parruda."

    return "🧩 Uso geral: bom para testar respostas, resumo e perguntas comuns. Não marquei como web porque não é uma escolha especialmente boa para sintetizar várias fontes."


def model_tags_for(name: str, category: str, level: str) -> List[str]:
    text = f"{name} {category} {level}".lower()
    tags: List[str] = []

    if _is_tiny(text) or _is_light(text):
        tags.append("PC fraco")

    if "coder" in text:
        tags.extend(["Código", "Debug", "Scripts"])
        if _has_any_size(text, ["3b", "7b", "14b", "32b"]):
            tags.append("Docs técnicas")
    else:
        if _is_tiny(text):
            tags.extend(["Teste rápido", "Perguntas simples"])
        else:
            tags.extend(["Perguntas", "Resumo"])

    if _is_web_recommended(text):
        tags.append("Web")

    if any(x in text for x in ["llama", "gemma", "mistral"]) and not _is_tiny(text):
        tags.append("Nonsense")

    if ("qwen3" in text or "qwen2.5" in text) and "coder" not in text:
        tags.append("Raciocínio")

    if _is_heavy(text):
        tags.append("Pesado")

    return list(dict.fromkeys(tags))


def model_catalog_with_status(installed_names: List[str], default_model: str = "") -> List[Dict[str, object]]:
    installed_set = {normalize_model_name(name) for name in installed_names}
    installed_base = {name.split(":", 1)[0] for name in installed_set}
    seen = set()
    output: List[Dict[str, object]] = []

    for item in MODEL_CATALOG:
        name = item["name"]
        norm = normalize_model_name(name)
        base = norm.split(":", 1)[0]
        installed = norm in installed_set or (":" not in norm and base in installed_base)
        row = item.copy()
        row["installed"] = installed
        row["status_icon"] = "✓" if installed else "↓"
        row["status_label"] = "Instalado" if installed else "Não instalado"
        row["hint"] = model_hint_for(name, row.get("category", ""), row.get("level", ""))
        row["tags"] = model_tags_for(name, row.get("category", ""), row.get("level", ""))
        row["install_command"] = f"ollama pull {name}"
        row["option_label"] = f"{row['status_icon']} {name} — {row['level']}"
        row["is_default"] = normalize_model_name(default_model) == norm
        output.append(row)
        seen.add(norm)

    for name in installed_names:
        norm = normalize_model_name(name)
        if norm and norm not in seen:
            output.insert(
                0,
                {
                    "name": name,
                    "size": "Detectado localmente",
                    "level": "Local",
                    "category": "Modelo instalado",
                    "good_for": "Modelo encontrado no seu Ollama local. Use se você já sabe para que ele serve ou teste com uma pergunta curta.",
                    "warning": "Não está no catálogo padrão do app, mas está instalado.",
                    "hint": "📦 Modelo local detectado: ele está instalado, mas não faz parte do catálogo guiado. Teste com uma pergunta curta para descobrir se combina com web, código, resumo ou criatividade.",
                    "tags": ["Local", "Teste"],
                    "installed": True,
                    "status_icon": "✓",
                    "status_label": "Instalado",
                    "install_command": f"ollama pull {name}",
                    "option_label": f"✓ {name} — Local",
                    "is_default": normalize_model_name(default_model) == norm,
                },
            )

    return output
