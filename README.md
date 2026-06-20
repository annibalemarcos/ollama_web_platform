# Ollama Web Platform v56

Plataforma local em **Flask + Bootstrap** para usar o **Ollama local**, fazer pesquisa web quando necessário, integrar APIs externas de IA e organizar consultas em uma interface mais confortável do que ficar preso no terminal.

O foco do projeto é ser uma central local de IA para Windows: você escreve a pergunta no navegador, escolhe como quer rodar, e o app decide se usa apenas o modelo local, busca fontes na web, usa uma IA externa ou combina configurações salvas.

> **Atenção:** este projeto pode guardar API keys no arquivo `.env`. Nunca suba o `.env` para GitHub.

---

## Visão geral

O app roda localmente em:

```text
http://127.0.0.1:5388
```

Ele pode funcionar de várias formas:

| Fluxo | Usa Ollama local? | Usa web/API externa? | Quando usar |
|---|---:|---:|---|
| Padrão | Sim | Não por padrão | Perguntas comuns, explicações, escrita e testes rápidos |
| Somente local | Sim | Não | Privacidade, economia de API, scripts, tarefas técnicas locais |
| Pesquisa Web guiada | Sim | Sim, para buscar fontes | Preço, notícia, documentação atual, comparação com fontes |
| Web/Cloud sem local | Não necessariamente | Sim | Quando quiser usar ChatGPT, Gemini, Claude ou Perplexity sem depender do PC |
| Avançado | Configurável | Configurável | Quando quiser escolher motor, busca, grupo e fontes manualmente |
| Todos / Multi-IA | Configurável | Pode usar várias APIs | Comparação ampla, uso experimental e respostas mais robustas |

---

## Recursos principais

- Interface web local em Flask.
- Integração com Ollama local via `http://127.0.0.1:11434`.
- Pesquisa Web usando API configurada.
- Modos de execução: direto, detalhado, pesquisa web e técnico.
- Seletor visual de modelos Ollama.
- Download e exclusão de modelos pelo dropdown.
- Progresso de download/exclusão de modelos.
- Cancelar geração com segurança.
- Forçar parada do runner do modelo sem matar o Ollama inteiro.
- Histórico local em SQLite.
- Exportação de respostas em Markdown, TXT e JSON.
- Resposta limpa e resposta completa separadas.
- Botões separados para copiar resposta limpa e resposta completa.
- Painel de fontes em acordeão.
- Renderização melhorada de Markdown básico e blocos de código.
- Configurações pelo navegador editando o `.env` por trás.
- Importar/exportar configurações completas.
- Integração inicial com APIs externas de IA.
- Filtros e busca para provedores externos.
- Stats do PC em tempo real, com toggle para ativar/desativar.
- Ready made search para importar/exportar pesquisas prontas.

---

## Como instalar e rodar

### 1. Instale o Ollama

Baixe e instale o Ollama para Windows:

```text
https://ollama.com/
```

Depois abra o Ollama antes de iniciar a plataforma.

### 2. Extraia o projeto

Extraia o ZIP em uma pasta, por exemplo:

```text
C:\my_projects\ollama_web_platform
```

### 3. Rode uma vez

Use:

```bat
run_once.bat
```

Esse script instala dependências, aplica limites seguros e inicia o servidor local.

### 4. Acesse no navegador

```text
http://127.0.0.1:5388
```

---

## Arquivos `.bat`

Todos os arquivos `.bat` seguem o padrão:

```bat
@echo off
mode con: cols=68 lines=14
```

Arquivos principais:

| Arquivo | Função |
|---|---|
| `install.bat` | Instala dependências Python |
| `run.bat` | Roda o app normalmente |
| `run_economico.bat` | Roda com perfil econômico |
| `run_once.bat` | Instala, aplica limites seguros e roda |
| `apply_ollama_safe_limits.bat` | Configura limites para não travar o PC |

---

## Configuração `.env`

O arquivo `.env` guarda configurações locais, por exemplo:

```env
OLLAMA_API_KEY=
OLLAMA_LOCAL_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:4b
APP_HOST=127.0.0.1
APP_PORT=5388
FLASK_DEBUG=0
```

Também guarda limites, toggles e API keys externas.

> **Nunca envie `.env` para GitHub.** Use `.env.example` como modelo seguro.

---

## Configurações pelo navegador

O menu **Configurações** permite editar várias opções sem abrir o `.env` manualmente.

### API da Ollama

A seção da API da Ollama tem botões para:

- salvar API key;
- testar conexão;
- remover chave.

### APIs externas

A seção **Outras IAs / APIs externas** permite configurar:

- Copilot;
- You.com;
- Exa;
- Exa Websets;
- Kagi;
- Brave Search;
- Andi;
- Consensus;
- Elicit;
- NotebookLM;
- WolframAlpha;
- Ithy;
- Gemini;
- iAsk;
- Perplexity;
- Claude / Anthropic;
- ChatGPT / OpenAI.

Cada provedor pode ter:

- API key;
- toggle ativar/desativar;
- botão salvar API;
- botão testar conexão;
- botão apagar chave;
- botão de stats.

### Busca e filtros de provedores

A tela de provedores externos tem busca e filtros:

- exibir todas;
- somente ativas;
- somente desativadas;
- somente com API key;
- somente sem API key;
- somente teste real;
- somente teste básico.

---

## Como rodar uma pergunta

Na tela **Pesquisar**, o campo principal funciona como um composer de chat.

O botão azul envia a pergunta.

Durante a execução, aparecem botões para:

- cancelar com segurança;
- forçar parada do runner do modelo.

---

## Dropdown “Como rodar”

Esse dropdown controla o caminho principal da consulta.

### Padrão

Usa o modelo local selecionado e mantém os ajustes avançados escondidos.

Bom para:

- perguntas rápidas;
- reescrita;
- explicações;
- ideias;
- tarefas que não precisam de web.

### Somente local

Usa apenas o Ollama local.

Não chama busca web nem APIs externas de busca.

Agora também abre o acordeão de ajustes para permitir escolher:

- modo;
- grupo recomendado;
- motor de resposta;
- motor de busca;
- fontes.

Mesmo exibindo os controles, o backend continua forçando:

```text
Motor de resposta: Ollama local
Motor de busca: Somente local
```

Assim você pode escolher **Código / técnico**, por exemplo, sem acionar web.

### Pesquisa Web guiada

Busca fontes na web e depois manda essas fontes para o modelo local responder.

Fluxo:

```text
Pergunta
↓
Busca web/API
↓
Fontes organizadas
↓
Ollama local responde
```

### Web/Cloud sem local

Usa IA externa para gerar a resposta final.

Pode usar, se configurado:

- Perplexity;
- ChatGPT / OpenAI;
- Claude / Anthropic;
- Gemini.

Fluxo:

```text
Pergunta
↓
Busca web/API, se necessário
↓
IA externa gera a resposta
```

### Avançado

Exibe todos os controles para ajustar manualmente.

### Todos / Multi-IA

Perfil experimental para estratégias amplas e futuras combinações de motores.

---

## Modelo local / Ollama

O seletor de modelo mostra modelos com:

- nome;
- status instalado/não instalado;
- categoria;
- tamanho;
- indicação de uso;
- botão para baixar;
- botão para excluir.

Para código, recomenda-se:

```text
qwen2.5-coder:3b
```

Se o PC aguentar:

```text
qwen2.5-coder:7b
```

Evite `qwen2.5-coder:0.5b` para scripts completos, pois ele pode repetir texto e falhar em tarefas maiores.

---

## Modos de resposta

| Modo | Usa web? | Uso indicado |
|---|---:|---|
| Direto | Não | Resposta curta e simples |
| Detalhado | Não | Explicação mais completa |
| Pesquisa Web | Sim, se o motor de busca permitir | Preços, notícias, documentação atual |
| Técnico | Não por padrão | Código, scripts, Windows, Python, debug |

---

## Motores

### Motor de resposta

Define quem gera a resposta final.

Opções comuns:

- Auto;
- Todos;
- Ollama local;
- Web/Cloud sem local;
- provedores externos ativos com API key.

### Motor de busca

Define de onde vêm as fontes.

Opções comuns:

- Auto;
- Todos;
- Somente local;
- Ollama Web Search;
- buscadores externos ativos/configurados.

### Grupo recomendado

Ajuda o app a orientar o prompt.

Opções:

- Auto;
- Todos;
- Local leve;
- Web / preço / notícia;
- Código / técnico;
- Acadêmico;
- Matemática / cálculo.

---

## Respostas e cópia

A tela de resposta separa duas versões:

### Resposta limpa

É a versão principal, sem poluir a leitura com referências inline soltas.

Botão:

```text
Copiar resposta
```

### Resposta completa

Fica em acordeão e preserva a resposta original completa, incluindo referências inline.

Botão:

```text
Copiar resposta completa
```

---

## Fontes

Quando a consulta usa web, as fontes aparecem em um painel/acordeão.

A ideia é manter a resposta limpa e deixar as fontes organizadas abaixo ou ao lado, sem misturar tudo no texto principal.

---

## Histórico

O app salva consultas localmente em SQLite.

No histórico, você pode:

- rever pergunta;
- rever resposta;
- copiar resposta;
- copiar resposta completa;
- exportar em MD;
- exportar em TXT;
- exportar em JSON;
- apagar consultas;
- limpar histórico.

---

## Exportar e importar configurações

Em **Configurações**, existem botões para:

- exportar configurações;
- importar configurações.

O export gera um JSON completo com configurações locais, incluindo API keys salvas.

> Trate esse arquivo como senha. Não envie para GitHub.

O import aceita:

- JSON exportado pelo app;
- arquivo `.env` simples com `CHAVE=valor`.

---

## Ready made search

O recurso **Ready made search** pode ser ativado em **Configurações**.

Quando ativado, a tela **Pesquisar** mostra um painel para:

- importar pesquisa pronta em JSON;
- exportar a pesquisa/configuração atual em JSON.

### Para que serve

Serve para salvar setups bons de pergunta + configuração.

Exemplo:

```text
Prompt para gerar script Python
+ modelo qwen2.5-coder:3b
+ modo Técnico
+ motor local
+ temperatura 0.1
```

Depois você importa o JSON e o app preenche tudo para você só revisar e clicar em buscar.

### O que o export salva

- pergunta;
- como rodar;
- modelo;
- modo;
- motor de resposta;
- motor de busca;
- grupo recomendado;
- fontes;
- temperatura;
- resposta limpa, se existir;
- resposta completa, se existir.

### Formato básico

```json
{
  "format": "ollama-web-platform-ready-made-search-v1",
  "app": "Ollama Web Platform",
  "title": "Minha pesquisa pronta",
  "query": "Pergunta que será colocada no campo de busca",
  "config": {
    "execution_profile": "local_only",
    "model": "qwen2.5-coder:3b",
    "mode": "tecnico",
    "response_engine": "ollama",
    "search_engine": "local_only",
    "task_group": "code_tech",
    "max_results": "1",
    "temperature": "0.1"
  }
}
```

O import também tenta entender JSONs criados por outras IAs, aceitando campos como:

- `query`;
- `prompt`;
- `config`;
- `settings`;
- `modelo`;
- `modo`;
- `temperatura`.

---

## Stats do PC em tempo real

Pode ser ativado/desativado em **Configurações**.

Quando ativo, aparece:

- no menu **Status e uso**;
- no topo da tela **Pesquisar**, em botão de ícone.

Mostra:

- CPU;
- RAM;
- Disco;
- Download;
- Upload;
- RAM usada pelo Ollama;
- RAM usada pelo Python/Flask;
- horário da última atualização.

Os cards têm cores:

| Cor | Significado |
|---|---|
| Verde | uso normal |
| Amarelo | atenção |
| Laranja | alto |
| Vermelho | crítico |

A leitura só roda quando o painel/modal está visível e a opção está ativada.

---

## Cancelar e forçar parada

### Cancelar

Marca o job como cancelado e tenta descarregar o modelo com `ollama stop`.

Não fecha o Ollama inteiro.

### Forçar parada

Tenta encerrar apenas o runner do modelo, como:

```text
ollama_llama_server
llama-server
```

A intenção é evitar matar o app/daemon principal do Ollama.

---

## Gemini e modelos cloud

O cliente Gemini não depende mais apenas do modelo antigo `gemini-1.5-flash`.

Agora o app usa:

```env
AI_GEMINI_MODEL=gemini-3.1-flash-lite
```

Se o modelo configurado retornar `404`, o app tenta listar modelos disponíveis na API Gemini e escolher outro que suporte `generateContent`.

Variáveis opcionais para modelos cloud:

```env
AI_CHATGPT_MODEL=gpt-4o-mini
AI_PERPLEXITY_MODEL=sonar
AI_CLAUDE_MODEL=claude-3-5-haiku-latest
AI_GEMINI_MODEL=gemini-3.1-flash-lite
CLOUD_AI_TIMEOUT=120
```

---

## Uso recomendado para criar código

Para criar scripts Python no Windows, use:

```text
Como rodar: Somente local
Modelo: qwen2.5-coder:3b
Modo: Técnico
Motor de resposta: Ollama local
Motor de busca: Somente local
Grupo recomendado: Código / técnico
Temperatura: 0.1
```

Peça explicitamente para o modelo entregar o código em bloco:

````text
Entregue o código completo em um único bloco Markdown com ```python.
````

---

## Segurança

Não suba para GitHub:

```text
.env
*.db
__pycache__/
*.pyc
exports/
```

Arquivos seguros:

```text
.env.example
README.md
requirements.txt
app.py
services/
templates/
static/
*.bat
```

---

## Estrutura do projeto

```text
ollama_web_platform/
├─ app.py
├─ db.py
├─ model_catalog.py
├─ settings_manager.py
├─ ai_providers.py
├─ requirements.txt
├─ .env
├─ .env.example
├─ README.md
├─ install.bat
├─ run.bat
├─ run_once.bat
├─ run_economico.bat
├─ apply_ollama_safe_limits.bat
├─ services/
│  ├─ ollama_client.py
│  ├─ search_client.py
│  ├─ cloud_client.py
│  └─ pc_stats.py
├─ templates/
│  ├─ base.html
│  ├─ index.html
│  ├─ settings.html
│  ├─ status.html
│  ├─ history.html
│  └─ history_detail.html
├─ static/
│  ├─ css/
│  │  └─ style.css
│  └─ js/
│     └─ app.js
├─ scripts/
│  └─ positioned_server.ps1
├─ data/
└─ exports/
```

---

## Dependências

O app usa Python e bibliotecas listadas em `requirements.txt`.

Principais:

- Flask;
- requests;
- python-dotenv;
- psutil.

Instale com:

```powershell
pip install -r requirements.txt
```

Ou rode:

```bat
install.bat
```

---

## Changelog resumido

### v50

- Cancelar não fecha o Ollama inteiro.
- Forçar mira no runner do modelo, não no daemon principal.

### v51

- Correção do Gemini quando modelo antigo retorna `404`.
- Fallback automático para modelos compatíveis com `generateContent`.

### v52

- Versão de continuidade com README atualizado.

### v53

- Stats do PC com leitura melhorada de CPU.
- Sistema de cores conforme uso.

### v54

- Perfil **Somente local** passou a exibir também os ajustes de modo/grupo/motores.
- Grupo recomendado escolhido pelo usuário é preservado.

### v55

- Adicionado **Ready made search**.
- Importação/exportação de pesquisas prontas em JSON.

### v56

- README reestruturado e expandido com explicações completas sobre instalação, uso, modos, motores, APIs, stats, segurança e Ready made search.

---

## Observação final

Este projeto nasceu como uma interface local para Ollama, mas evoluiu para uma central modular de IA. A ideia é permitir trabalhar com:

- local puro;
- web + local;
- web/cloud sem local;
- provedores externos;
- pesquisas prontas importáveis;
- monitoramento do PC;
- histórico e exportação.

Tudo mantendo controle local e evitando depender de uma única ferramenta.
