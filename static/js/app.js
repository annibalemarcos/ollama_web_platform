const form = document.getElementById('askForm');
const submitBtn = document.getElementById('submitBtn');
const stopBtn = document.getElementById('stopBtn');
const forceStopBtn = document.getElementById('forceStopBtn');
const cancelStatus = document.getElementById('cancelStatus');
const modelInput = document.getElementById('modelInput');
const modelPickerButton = document.getElementById('modelPickerButton');
const modelChoices = Array.from(document.querySelectorAll('.model-choice'));
const modelPickerSearch = document.getElementById('modelPickerSearch');
const modelInfo = document.getElementById('modelInfo');
const modelTaskBox = document.getElementById('modelTaskBox');
const progressPanel = document.getElementById('progressPanel');
const progressBar = document.getElementById('progressBar');
const progressStage = document.getElementById('progressStage');
let progressTimer = null;
let progressPollTimer = null;

function escapeHtml(value) {
    return String(value || '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function datasetFromChoice(choice) {
    if (!choice) return null;
    return {
        value: choice.dataset.name || '',
        installed: choice.dataset.installed === '1',
        status: choice.dataset.status || '',
        size: choice.dataset.size || '',
        level: choice.dataset.level || '',
        category: choice.dataset.category || '',
        goodFor: choice.dataset.goodFor || '',
        warning: choice.dataset.warning || '',
        hint: choice.dataset.hint || '',
        tags: choice.dataset.tags || '',
        command: choice.dataset.command || ''
    };
}

function findChoiceByName(name) {
    const wanted = String(name || '').toLowerCase();
    return modelChoices.find(choice => String(choice.dataset.name || '').toLowerCase() === wanted) || modelChoices[0];
}

function renderModelButton(data) {
    if (!modelPickerButton || !data) return;
    const iconClass = data.installed ? 'bi-check2-circle' : 'bi-cloud-arrow-down';
    const statusClass = data.installed ? 'installed' : 'missing';
    const statusText = data.installed ? 'Instalado' : 'Baixar';
    modelPickerButton.innerHTML = `
        <span class="picker-status ${statusClass}"><i class="bi ${iconClass}"></i></span>
        <span class="picker-main">
            <span class="picker-name">${escapeHtml(data.value)}</span>
            <span class="picker-meta">${escapeHtml(data.level)} · ${escapeHtml(data.size)} · ${escapeHtml(statusText)}</span>
        </span>
        <span class="picker-caret"><i class="bi bi-chevron-down"></i></span>
    `;
}

function updateModelInfo(data) {
    if (!modelInfo || !data) return;
    const statusClass = data.installed ? 'model-ok' : 'model-missing';
    const statusText = data.installed ? 'Instalado e pronto' : 'Ainda não instalado';
    const statusIcon = data.installed ? 'bi-check2-circle' : 'bi-cloud-arrow-down';
    const command = data.command || `ollama pull ${data.value}`;
    const tags = String(data.tags || '').split(',').filter(Boolean)
        .map(tag => `<span>${escapeHtml(tag.trim())}</span>`).join('');

    modelInfo.innerHTML = `
        <div class="model-info-layout">
            <div class="model-info-hero">
                <div class="model-info-head">
                    <span class="model-status ${statusClass}"><i class="bi ${statusIcon}"></i> ${statusText}</span>
                    <span class="model-chip">${escapeHtml(data.level || 'Modelo')}</span>
                    <span class="model-chip">${escapeHtml(data.size || '')}</span>
                    <span class="model-chip">${escapeHtml(data.category || 'Uso geral')}</span>
                </div>
                <div class="model-info-title">${escapeHtml(data.value)}</div>
                <div class="model-tags">${tags}</div>
            </div>
            <div class="model-info-sections">
                <div class="model-info-section">
                    <div class="model-info-label">Bom para</div>
                    <p>${escapeHtml(data.goodFor || 'Uso geral.')}</p>
                </div>
                <div class="model-info-section">
                    <div class="model-info-label">Hint</div>
                    <p>${escapeHtml(data.hint || 'Use para tarefas gerais e teste com perguntas curtas primeiro.')}</p>
                </div>
                <div class="model-info-section">
                    <div class="model-info-label">Aviso</div>
                    <p>${escapeHtml(data.warning || 'Teste com perguntas curtas primeiro.')}</p>
                </div>
            </div>
            ${data.installed ? '' : `<div class="install-command"><span>Para baixar agora:</span> <code>${escapeHtml(command)}</code></div>`}
        </div>
    `;
}

function selectModel(choice) {
    const data = datasetFromChoice(choice);
    if (!data) return;
    if (modelInput) modelInput.value = data.value;
    modelChoices.forEach(item => item.classList.toggle('active', item === choice));
    renderModelButton(data);
    updateModelInfo(data);
}

function renderModelTask(task) {
    if (!modelTaskBox || !task) return;
    modelTaskBox.classList.remove('d-none');
    const status = task.status || 'idle';
    const icon = task.running ? 'bi-arrow-repeat' : (task.ok ? 'bi-check2-circle' : 'bi-info-circle');
    const title = task.model ? `${task.action === 'delete' ? 'Exclusão' : 'Download'}: ${task.model}` : 'Tarefa de modelo';
    const lines = Array.isArray(task.lines) && task.lines.length
        ? `<div class="model-task-lines">${task.lines.map(escapeHtml).join('\n')}</div>`
        : '';
    modelTaskBox.innerHTML = `
        <div><strong><i class="bi ${icon}"></i> ${escapeHtml(title)}</strong></div>
        <div>${escapeHtml(task.message || status)}</div>
        ${lines}
    `;
    updateModelRowFromTask(task);
}
function setModelRowProgress(modelName, state = {}) {
    if (!modelName) return;
    const progress = document.querySelector(`.model-choice-progress[data-progress-for="${CSS.escape(modelName)}"]`);
    if (!progress) return;

    const bar = progress.querySelector('.model-choice-progress-bar');
    const text = progress.querySelector('.model-choice-progress-text');

    progress.classList.remove('d-none', 'is-done', 'is-error');
    if (state.status === 'done') progress.classList.add('is-done');
    if (state.status === 'error') progress.classList.add('is-error');

    if (bar && typeof state.percent === 'number') {
        bar.style.width = `${Math.max(3, Math.min(100, state.percent))}%`;
    }

    if (text) {
        text.textContent = state.message || 'Trabalhando...';
    }
}

function updateModelRowFromTask(task) {
    if (!task || !task.model) return;
    const actionLabel = task.action === 'delete' ? 'Excluindo' : 'Baixando';
    const doneLabel = task.action === 'delete' ? 'Excluído' : 'Instalado';
    const errorLabel = task.action === 'delete' ? 'Erro ao excluir' : 'Erro ao baixar';

    if (task.running) {
        setModelRowProgress(task.model, {
            status: 'running',
            message: task.message || `${actionLabel}...`,
            percent: 45
        });
        return;
    }

    if (task.status === 'done' || task.ok === true) {
        setModelRowProgress(task.model, { status: 'done', message: doneLabel, percent: 100 });
        return;
    }

    if (task.status === 'error' || task.ok === false) {
        setModelRowProgress(task.model, { status: 'error', message: errorLabel, percent: 100 });
    }
}


async function pollModelTask() {
    if (!modelTaskBox) return;
    try {
        const response = await fetch('/api/models/task');
        const data = await response.json();
        if (!data.ok || !data.task) return;
        renderModelTask(data.task);
        if (data.task.running) {
            setTimeout(pollModelTask, 1400);
        } else if (data.task.status === 'done') {
            setTimeout(() => window.location.reload(), 1800);
        }
    } catch (err) {
        modelTaskBox.classList.remove('d-none');
        modelTaskBox.innerHTML = 'Não consegui consultar o status da tarefa de modelo.';
    }
}

async function pullModel(modelName, button) {
    if (!modelName) return;
    const ok = window.confirm(`Baixar o modelo ${modelName}? Pode demorar e consumir alguns GB dependendo do modelo.`);
    if (!ok) return;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    setModelRowProgress(modelName, { status: 'running', message: 'Baixando...', percent: 35 });
    if (modelTaskBox) {
        modelTaskBox.classList.remove('d-none');
        modelTaskBox.innerHTML = `<strong><i class="bi bi-download"></i> Baixando ${escapeHtml(modelName)}</strong><div>Iniciando download pelo Ollama...</div>`;
    }
    try {
        const response = await fetch('/api/models/pull', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: modelName })
        });
        const data = await response.json();
        if (!data.ok) {
            if (modelTaskBox) modelTaskBox.innerHTML = escapeHtml(data.message || 'Falha ao iniciar download.');
            setModelRowProgress(modelName, { status: 'error', message: 'Falha ao iniciar', percent: 100 });
            button.disabled = false;
            button.innerHTML = '<i class="bi bi-download"></i>';
            return;
        }
        renderModelTask(data.task);
        pollModelTask();
    } catch (err) {
        if (modelTaskBox) modelTaskBox.innerHTML = 'Erro ao pedir download do modelo.';
        setModelRowProgress(modelName, { status: 'error', message: 'Erro no pedido', percent: 100 });
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-download"></i>';
    }
}

async function deleteModel(modelName, button) {
    if (!modelName) return;
    const ok = window.confirm(`Excluir o modelo ${modelName} do Ollama local? Se precisar depois, terá que baixar novamente.`);
    if (!ok) return;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    setModelRowProgress(modelName, { status: 'running', message: 'Excluindo...', percent: 50 });
    if (modelTaskBox) {
        modelTaskBox.classList.remove('d-none');
        modelTaskBox.innerHTML = `<strong><i class="bi bi-x-lg"></i> Excluindo ${escapeHtml(modelName)}</strong><div>Chamando ollama rm...</div>`;
    }
    try {
        const response = await fetch('/api/models/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: modelName })
        });
        const data = await response.json();
        if (modelTaskBox) renderModelTask(data.task || { message: data.message, ok: data.ok, status: data.ok ? 'done' : 'error' });
        if (data.ok) {
            updateModelRowFromTask(data.task || { model: modelName, action: 'delete', status: 'done', ok: true });
            setTimeout(() => window.location.reload(), 1400);
        } else {
            setModelRowProgress(modelName, { status: 'error', message: 'Erro ao excluir', percent: 100 });
            button.disabled = false;
            button.innerHTML = '<i class="bi bi-x-lg"></i>';
        }
    } catch (err) {
        if (modelTaskBox) modelTaskBox.innerHTML = 'Erro ao excluir modelo.';
        setModelRowProgress(modelName, { status: 'error', message: 'Erro ao excluir', percent: 100 });
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-x-lg"></i>';
    }
}

function initModelPicker() {
    if (!modelInput || !modelChoices.length) return;
    const initialChoice = findChoiceByName(modelInput.value);
    selectModel(initialChoice);

    modelChoices.forEach(choice => {
        choice.addEventListener('click', (event) => {
            if (event.target.closest('.model-action')) return;
            selectModel(choice);
        });
        choice.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                selectModel(choice);
            }
        });
    });

    document.querySelectorAll('.model-action').forEach((button) => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            const modelName = button.dataset.model;
            const action = button.dataset.modelAction;
            if (action === 'pull') pullModel(modelName, button);
            if (action === 'delete') deleteModel(modelName, button);
        });
    });

    if (modelPickerSearch) {
        modelPickerSearch.addEventListener('click', (event) => event.stopPropagation());
        modelPickerSearch.addEventListener('input', () => {
            const query = modelPickerSearch.value.trim().toLowerCase();
            modelChoices.forEach(choice => {
                const haystack = [
                    choice.dataset.name,
                    choice.dataset.level,
                    choice.dataset.category,
                    choice.dataset.goodFor,
                    choice.dataset.hint,
                    choice.dataset.tags,
                    choice.dataset.status
                ].join(' ').toLowerCase();
                choice.classList.toggle('d-none', query && !haystack.includes(query));
            });
        });
    }
}

initModelPicker();

function setSelectValueByName(name, value) {
    const select = document.querySelector(`[name="${name}"]`);
    if (!select) return;
    const optionExists = Array.from(select.options || []).some((option) => option.value === value);
    if (optionExists) select.value = value;
}

function applyExecutionProfile() {
    const profileEl = document.getElementById('executionProfile');
    const profile = profileEl ? profileEl.value : 'standard';
    const localPanel = document.querySelector('[data-execution-panel="local"]');
    const advancedPanel = document.querySelector('[data-execution-panel="advanced"]');
    const localDetails = document.getElementById('localModelPanel');
    const advancedDetails = document.getElementById('advancedEnginesPanel');

    const showLocal = ['standard', 'local_only', 'web', 'advanced', 'all'].includes(profile);
    const showAdvanced = ['local_only', 'web', 'cloud_web', 'advanced', 'all'].includes(profile);

    if (localPanel) localPanel.classList.toggle('d-none', !showLocal);
    if (advancedPanel) advancedPanel.classList.toggle('d-none', !showAdvanced);

    if (localDetails) {
        localDetails.open = ['local_only', 'web', 'advanced', 'all'].includes(profile);
    }
    if (advancedDetails) {
        advancedDetails.open = ['local_only', 'web', 'cloud_web', 'advanced', 'all'].includes(profile);
    }

    if (profile === 'local_only') {
        setSelectValueByName('response_engine', 'ollama');
        setSelectValueByName('search_engine', 'local_only');
        const modeSelect = document.querySelector('[name="mode"]');
        if (modeSelect && modeSelect.value === 'web') setSelectValueByName('mode', 'direto');
        const groupSelect = document.querySelector('[name="task_group"]');
        if (groupSelect && groupSelect.value === 'auto') setSelectValueByName('task_group', 'local_fast');
    } else if (profile === 'web') {
        setSelectValueByName('mode', 'web');
        setSelectValueByName('response_engine', 'ollama');
        const searchSelect = document.querySelector('[name="search_engine"]');
        if (searchSelect && searchSelect.value === 'local_only') setSelectValueByName('search_engine', 'auto');
        const groupSelect = document.querySelector('[name="task_group"]');
        if (groupSelect && groupSelect.value === 'auto') setSelectValueByName('task_group', 'web_price');
    } else if (profile === 'cloud_web') {
        setSelectValueByName('mode', 'web');
        setSelectValueByName('response_engine', 'web_cloud');
        const searchSelect = document.querySelector('[name="search_engine"]');
        if (searchSelect && searchSelect.value === 'local_only') setSelectValueByName('search_engine', 'auto');
        const groupSelect = document.querySelector('[name="task_group"]');
        if (groupSelect && groupSelect.value === 'auto') setSelectValueByName('task_group', 'web_price');
    } else if (profile === 'all') {
        setSelectValueByName('mode', 'web');
        setSelectValueByName('response_engine', 'all');
        setSelectValueByName('search_engine', 'all');
        setSelectValueByName('task_group', 'all');
    }
}


const PROGRESS_FLOW = [
    { pct: 10, label: 'Preparando pergunta e configurações...', delay: 0 },
    { pct: 25, label: 'Buscando fontes na web...', delay: 900 },
    { pct: 42, label: 'Organizando fontes e cortando excesso de texto...', delay: 2600 },
    { pct: 62, label: 'Chamando o motor de resposta...', delay: 5200 },
    { pct: 82, label: 'Gerando resposta. Aqui o PC pode respirar pesado...', delay: 9500 },
    { pct: 92, label: 'Finalizando e salvando histórico...', delay: 18000 }
];

function setProgressStep(index) {
    if (!progressPanel || !progressBar || !progressStage) return;
    const step = PROGRESS_FLOW[Math.min(index, PROGRESS_FLOW.length - 1)];
    progressPanel.classList.remove('d-none');
    progressBar.style.width = `${step.pct}%`;
    progressStage.textContent = step.label;

    document.querySelectorAll('.progress-steps span').forEach((item) => {
        const itemStep = Number(item.dataset.step || '0');
        item.classList.toggle('is-done', itemStep < Math.min(index, 4));
        item.classList.toggle('is-active', itemStep === Math.min(index, 4));
    });
}

function startProgressUI() {
    if (!progressPanel) return;
    if (progressTimer) clearInterval(progressTimer);
    setProgressStep(0);
    let current = 0;

    PROGRESS_FLOW.slice(1).forEach((step, idx) => {
        window.setTimeout(() => {
            if (!progressPanel.classList.contains('d-none')) {
                current = idx + 1;
                setProgressStep(current);
            }
        }, step.delay);
    });

    progressTimer = window.setInterval(() => {
        if (!progressBar || progressPanel.classList.contains('d-none')) return;
        const currentWidth = parseFloat(progressBar.style.width || '0');
        if (currentWidth < 96) {
            progressBar.style.width = `${Math.min(96, currentWidth + 1.5)}%`;
        }
    }, 2200);

    if (progressPollTimer) clearInterval(progressPollTimer);
    progressPollTimer = window.setInterval(async () => {
        try {
            const response = await fetch('/api/jobs');
            const data = await response.json();
            const job = data.jobs && data.jobs[0];
            if (job && job.stage) updateProgressMessage(job.stage);
        } catch (err) {
            // Se a navegação estiver ocupada, mantém o progresso aproximado.
        }
    }, 2500);
}

function updateProgressMessage(message) {
    if (!progressPanel || !progressStage) return;
    progressPanel.classList.remove('d-none');
    progressStage.textContent = message;
}

if (form && submitBtn) {
    form.addEventListener('submit', () => {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        if (stopBtn) stopBtn.classList.remove('d-none');
        if (forceStopBtn) forceStopBtn.classList.remove('d-none');
        startProgressUI();
        if (cancelStatus) cancelStatus.textContent = 'Rodando... use cancelar; se travar, use forçar o runner do modelo.';
    });
}

if (stopBtn) {
    stopBtn.addEventListener('click', async () => {
        stopBtn.disabled = true;
        stopBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        updateProgressMessage('Cancelamento seguro solicitado...');
        if (cancelStatus) cancelStatus.textContent = 'Enviando pedido de cancelamento seguro...';

        try {
            const response = await fetch('/api/cancel', { method: 'POST' });
            const data = await response.json();
            if (cancelStatus) {
                cancelStatus.textContent = data.model
                    ? `Cancelamento pedido para ${data.model}. Se não parar em alguns segundos, force só o runner do modelo.`
                    : 'Pedido enviado. Nenhuma tarefa ativa encontrada.';
            }
            await refreshJobs();
        } catch (err) {
            if (cancelStatus) cancelStatus.textContent = 'Não consegui enviar o pedido de parada.';
        } finally {
            stopBtn.innerHTML = '<i class="bi bi-stop-fill"></i>';
            setTimeout(() => { stopBtn.disabled = false; }, 1500);
        }
    });
}

if (forceStopBtn) {
    forceStopBtn.addEventListener('click', async () => {
        const ok = window.confirm('Forçar parada vai tentar encerrar só o runner do modelo, sem fechar o Ollama. Continuar?');
        if (!ok) return;
        forceStopBtn.disabled = true;
        forceStopBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        updateProgressMessage('Forçando runner do modelo...');
        if (cancelStatus) cancelStatus.textContent = 'Forçando runner do modelo...';

        try {
            const response = await fetch('/api/force_cancel', { method: 'POST' });
            const data = await response.json();
            if (cancelStatus) {
                cancelStatus.textContent = data.ok
                    ? 'Parada forçada enviada ao runner. O Ollama deve continuar aberto.'
                    : (data.message || 'Não consegui forçar a parada.');
            }
            await refreshJobs();
        } catch (err) {
            if (cancelStatus) cancelStatus.textContent = 'Falha ao forçar parada.';
        } finally {
            forceStopBtn.innerHTML = '<i class="bi bi-exclamation-octagon"></i>';
            setTimeout(() => { forceStopBtn.disabled = false; }, 1500);
        }
    });
}

function copyToClipboardWithButton(textToCopy, buttonEl) {
    if (!textToCopy) return;
    navigator.clipboard.writeText(String(textToCopy).trim()).then(() => {
        const btn = buttonEl || event?.target?.closest('button');
        if (!btn) return;
        const old = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check2"></i> Copiado';
        setTimeout(() => btn.innerHTML = old, 1200);
    });
}

function copyCleanAnswer(buttonEl) {
    const box = document.getElementById('answerBox');
    copyToClipboardWithButton(box ? box.innerText : '', buttonEl);
}

function copyFullAnswer(buttonEl) {
    const raw = document.getElementById('answerCopyText');
    const fallback = document.getElementById('answerBox')?.innerText || '';
    copyToClipboardWithButton(raw ? raw.value : fallback, buttonEl);
}

function copyAnswer(buttonEl) {
    copyFullAnswer(buttonEl);
}

function copyCodeBlock(blockId, buttonEl) {
    const codeEl = document.getElementById(blockId);
    if (!codeEl) return;
    navigator.clipboard.writeText(codeEl.innerText).then(() => {
        const btn = buttonEl;
        const old = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check2"></i><span>Copiado</span>';
        setTimeout(() => { btn.innerHTML = old; }, 1200);
    });
}

const HELP_CONTENT = {
    perfil_execucao: {
        title: 'Como rodar',
        icon: 'bi-signpost-split',
        body: `
            <p><strong>Esse menu escolhe o caminho principal da pergunta.</strong> Ele serve para não deixar modelo, busca, motores e fontes todos jogados na tela ao mesmo tempo.</p>
            <div class="help-grid help-grid-wide">
                <div><strong>Padrão</strong><br><span class="help-pill-local">Ollama local</span><br>Roda como antes: usa o modelo local selecionado e mantém os ajustes avançados escondidos.</div>
                <div><strong>Somente local</strong><br><span class="help-pill-local">Sem web/API de busca</span><br>Força motor de busca local-only e resposta no Ollama local, mas agora também abre os ajustes de modo/grupo para você escolher Técnico, Local leve, Código etc.</div>
                <div><strong>Pesquisa Web guiada</strong><br><span class="help-pill-web">Busca web + resposta local</span><br>Busca fontes na web, mas a resposta final continua no Ollama local selecionado.</div>
                <div><strong>Web/Cloud sem local</strong><br><span class="help-pill-web">Sem Ollama local</span><br>Busca web e gera a resposta em uma IA externa ativa/configurada, como Perplexity, ChatGPT, Claude ou Gemini.</div>
                <div><strong>Avançado</strong><br>Mostra os dois acordeões para você escolher modelo local, motor de resposta, motor de busca, grupo e fontes manualmente.</div>
                <div><strong>Todos / Multi-IA</strong><br>Prepara a estratégia ampla: Todos nos motores e grupo. Mais pesado, útil para comparar respostas/fontes quando o roteamento completo estiver ativado.</div>
            </div>
            <div class="help-example"><span>Regra prática:</span> dia a dia: <code>Padrão</code>. Quer zero web: <code>Somente local</code>. Quer fontes atuais mas resposta local: <code>Pesquisa Web guiada</code>. Quer não usar Ollama local: <code>Web/Cloud</code>. Quer mexer em tudo: <code>Avançado</code>.</div>
        `
    },
    pergunta: {
        title: 'Pergunta',
        icon: 'bi-chat-left-text',
        body: `
            <p><strong>Esse campo é o volante do carro.</strong> É aqui que você diz o que quer que a IA faça: pesquisar, analisar, comparar, resumir, explicar, criar anúncio, gerar código, revisar texto ou montar um passo a passo.</p>
            <div class="help-grid">
                <div><strong>Como afeta a resposta</strong><br>Pedido claro gera resposta clara. Pedido solto gera resposta genérica, porque o modelo tenta adivinhar sua intenção.</div>
                <div><strong>O que colocar</strong><br>Objetivo, contexto, cidade/país se for pesquisa local, formato desejado e restrições. Ex: “não invente”, “cite fontes”, “responda em tabela”.</div>
                <div><strong>Para pesquisa web</strong><br>Inclua termos específicos, local e recorte. “Preço de berço usado em Campinas-SP” é melhor que “preço de berço”.</div>
                <div><strong>Para código</strong><br>Diga linguagem, sistema operacional, versão, pastas, dependências e o que deve acontecer em caso de erro.</div>
            </div>
            <div class="help-example"><span>Exemplo forte:</span> “Pesquise na web anúncios de berço infantil usado em Campinas-SP, cite fontes, compare preços e diga uma faixa realista.”</div>
            <div class="help-example"><span>Exemplo técnico:</span> “Crie um script Python 3.11 para Windows 10 que leia um JSON, filtre por navegador e exporte CSV. Entregue código completo.”</div>
        `
    },
    modelo: {
        title: 'Modelo',
        icon: 'bi-cpu',
        body: `
            <p><strong>Modelo é o cérebro que vai responder.</strong> O app mostra um catálogo do mais leve ao mais pesado e verifica o que já existe no seu Ollama local.</p>
            <div class="help-grid">
                <div><strong>Instalado</strong><br>Badge verde com check. Dá para usar agora, sem baixar nada.</div>
                <div><strong>Não instalado</strong><br>Badge de download. O app mostra o comando <code>ollama pull modelo</code> para baixar.</div>
                <div><strong>Modelos leves</strong><br>1B, 1.7B, 3B e 4B. Rodam melhor em PC com 16 GB. Menos inteligência, mais velocidade.</div>
                <div><strong>Modelos pesados</strong><br>7B, 8B, 12B e 14B+. Respostas melhores, mas usam muito mais RAM/CPU e podem travar.</div>
            </div>
            <div class="help-example"><span>Minha regra para seu PC:</span> uso geral: <code>llama3.2:1b</code>, <code>llama3.2</code> ou <code>gemma3:4b</code>. Código: <code>qwen2.5-coder:3b</code>; só depois teste <code>qwen2.5-coder:7b</code>.</div>
        `
    },
    modo: {
        title: 'Modo',
        icon: 'bi-sliders2',
        body: `
            <p><strong>Modo define se o app vai usar só o Ollama local ou se também vai buscar fontes na web.</strong> O modelo continua sendo o cérebro; o modo muda o caminho da pergunta.</p>
            <div class="help-grid help-grid-wide">
                <div><strong>Direto</strong><br><span class="help-pill-local">Só local</span><br>Não faz busca web. Manda sua pergunta direto para o modelo local. Bom para perguntas simples, explicações rápidas, reescrita, ideias e coisas que não dependem de informação atual.</div>
                <div><strong>Detalhado</strong><br><span class="help-pill-local">Só local</span><br>Também não faz busca web. Usa o modelo local para responder com mais contexto, exemplos, prós/contras e próximos passos. Bom quando você quer entender melhor um assunto estável.</div>
                <div><strong>Pesquisa Web</strong><br><span class="help-pill-web">Usa web/API</span><br>Faz busca na internet, injeta as fontes no prompt e pede ao modelo para comparar, citar e concluir. Use para notícias, preços, anúncios, documentação atual, leis/regras e qualquer coisa que pode ter mudado.</div>
                <div><strong>Técnico</strong><br><span class="help-pill-local">Só local</span><br>Não faz busca web por padrão. Foca em comandos, código, Windows, Python, Flask, erros e diagnóstico. Use quando você quer script, debugging ou passo a passo técnico.</div>
            </div>
            <div class="help-example"><span>Regra prática:</span> se precisa de informação atual ou fonte, use <code>Pesquisa Web</code>. Se é tarefa geral/código/explicação e você quer economizar cloud usage, use <code>Direto</code>, <code>Detalhado</code> ou <code>Técnico</code>.</div>
            <div class="help-example"><span>Impacto no Cloud usage:</span> <code>Pesquisa Web</code> pode usar API/web para buscar fontes. Se o motor de resposta for <code>Ollama local</code>, a geração fica no PC. Se for <code>Web/Cloud</code>, a geração vai para a IA externa configurada.</div>
        `
    },
    motor_resposta: {
        title: 'Motor de resposta',
        icon: 'bi-cpu',
        body: `
            <p><strong>Escolhe quem gera a resposta final.</strong> Este dropdown sempre tem <code>Auto</code> e <code>Todos</code>. Os provedores externos só aparecem quando estão ativos e com API key salva em Configurações.</p>
            <div class="help-grid help-grid-wide">
                <div><strong>Auto</strong><br>Melhor padrão. Usa Ollama local quando a tarefa é simples/local; futuramente pode escolher cloud quando fizer sentido.</div>
                <div><strong>Todos</strong><br>Para comparação/multi-IA. A ideia é chamar mais de um motor e depois sintetizar. Use com cuidado porque pode gastar mais API.</div>
                <div><strong>Ollama local</strong><br>Melhor para privacidade, custo zero de cloud e tarefas gerais. Depende da força do seu PC/modelo.</div>
                <div><strong>Web/Cloud sem Ollama local</strong><br>Usa uma IA externa ativa/configurada para gerar a resposta final. Bom quando você não quer carregar modelo local.</div>
                <div><strong>ChatGPT / Claude / Gemini / Perplexity</strong><br>Melhores para respostas fortes, raciocínio, escrita, análise longa e tarefas em que vale gastar API.</div>
            </div>
            <div class="help-example"><span>Regra prática:</span> tarefa comum: <code>Auto</code> ou <code>Ollama local</code>. Texto/código difícil: cloud forte. Comparação séria: <code>Todos</code>.</div>
        `
    },
    motor_busca: {
        title: 'Motor de busca',
        icon: 'bi-search',
        body: `
            <p><strong>Escolhe quem busca informação externa.</strong> Ele só importa de verdade quando o modo/tarefa envolve web, preço, notícia, documentação atual ou comparação.</p>
            <div class="help-grid help-grid-wide">
                <div><strong>Auto</strong><br>Escolha segura. O app usa o melhor buscador disponível/ativado.</div>
                <div><strong>Todos</strong><br>Bom para pesquisa pesada: compara vários buscadores. Mais lento e pode gastar mais quota/API.</div>
                <div><strong>Somente local (sem web)</strong><br>Força o app a não chamar busca web nem API externa de busca. É o modo “meu PC e acabou”.</div>
                <div><strong>Ollama Web Search</strong><br>Bom caminho padrão quando você já usa a API da Ollama.</div>
                <div><strong>Brave / Kagi / Exa</strong><br>Brave/Kagi são bons para web geral. Exa é bom para busca semântica, pesquisa e páginas parecidas.</div>
            </div>
            <div class="help-example"><span>Regra prática:</span> OLX/preço/notícia: busca web. Pesquisa semântica: Exa. Busca geral limpa: Brave/Kagi. Sem dado atual ou se quiser economizar cloud: <code>Somente local</code>.</div>
        `
    },
    grupo_ia: {
        title: 'Grupo recomendado',
        icon: 'bi-diagram-3',
        body: `
            <p><strong>Ajuda o app a entender o tipo da tarefa.</strong> Também tem sempre <code>Auto</code> e <code>Todos</code>.</p>
            <div class="help-grid help-grid-wide">
                <div><strong>Auto</strong><br>Use quando não quiser pensar. O app tenta inferir pelo texto da pergunta.</div>
                <div><strong>Todos</strong><br>Para análise ampla/multi-etapa. Melhor quando a pergunta é importante e você quer comparação.</div>
                <div><strong>Local leve</strong><br>Resumo, explicação, reescrita, ideia, resposta rápida. Melhor para economizar cloud.</div>
                <div><strong>Web / preço / notícia</strong><br>Produtos, anúncios, mercado, documentação recente, leis/regras, fatos que mudam.</div>
                <div><strong>Código / técnico</strong><br>Scripts, Windows, Python, Flask, debug, logs, comandos e diagnóstico.</div>
                <div><strong>Acadêmico</strong><br>Artigos, evidência científica, papers, revisão, consenso e incerteza.</div>
                <div><strong>Matemática / cálculo</strong><br>Conta, fórmula, resultado exato, checagem matemática e WolframAlpha.</div>
            </div>
            <div class="help-example"><span>Atalho mental:</span> atualidade = web. Privacidade/custo = local. Ciência = acadêmico. Conta exata = matemática. Erro/script = técnico.</div>
        `
    },
    fontes: {
        title: 'Fontes',
        icon: 'bi-link-45deg',
        body: `
            <p><strong>Fontes só entram em ação no modo Pesquisa Web.</strong> Elas definem quantos resultados da internet entram na pergunta enviada ao modelo local.</p>
            <div class="help-grid">
                <div><strong>1 a 3 fontes</strong><br>Mais rápido, mais leve, ideal para PC com 16 GB. Bom para consultas simples.</div>
                <div><strong>4 a 5 fontes</strong><br>Mais contexto e comparação, mas aumenta o prompt e pode deixar o modelo mais lento.</div>
                <div><strong>Impacto em RAM</strong><br>Cada fonte vira texto dentro do prompt. Quanto mais texto, mais contexto o Ollama precisa processar.</div>
                <div><strong>Qualidade</strong><br>Mais fontes não significa resposta melhor se as fontes forem ruins. O segredo é pergunta específica + fontes suficientes.</div>
            </div>
            <div class="help-example"><span>Minha sugestão:</span> deixe em <code>3</code>. Aumente para <code>5</code> só quando estiver pesquisando preço, comparação ou algo que precise de várias referências.</div>
        `
    },
    temperatura: {
        title: 'Temperatura',
        icon: 'bi-thermometer-half',
        body: `
            <p><strong>Temperatura controla criatividade versus previsibilidade.</strong> Baixa temperatura deixa a IA mais conservadora; alta deixa mais inventiva.</p>
            <div class="help-grid">
                <div><strong>0.0 a 0.3</strong><br>Mais estável e objetiva. Melhor para pesquisa web, fatos, código, diagnóstico e respostas com fontes.</div>
                <div><strong>0.4 a 0.8</strong><br>Equilíbrio. Bom para explicações, anúncios, ideias, textos naturais e reescrita.</div>
                <div><strong>0.9 a 1.5</strong><br>Mais criativa, mas aumenta chance de viajar na maionese. Use para brainstorming, não para fato.</div>
                <div><strong>Impacto prático</strong><br>Não muda muito a velocidade, mas muda o estilo e a chance de respostas diferentes para a mesma pergunta.</div>
            </div>
            <div class="help-example"><span>Receita pronta:</span> pesquisa/preço/código: <code>0.2</code>. Anúncio de venda/texto criativo: <code>0.6</code> ou <code>0.7</code>. Ideias malucas: <code>1.0</code>.</div>
        `
    }
};

function initHelpModal() {
    const modalEl = document.getElementById('helpModal');
    const titleEl = document.getElementById('helpModalTitle');
    const bodyEl = document.getElementById('helpModalBody');
    if (!modalEl || !titleEl || !bodyEl || typeof bootstrap === 'undefined') return;

    const modal = new bootstrap.Modal(modalEl);
    document.querySelectorAll('[data-help-topic]').forEach((button) => {
        button.addEventListener('click', () => {
            const topic = button.dataset.helpTopic;
            const item = HELP_CONTENT[topic];
            if (!item) return;
            titleEl.innerHTML = `<i class="bi ${item.icon}"></i> ${item.title}`;
            bodyEl.innerHTML = item.body;
            modal.show();
        });
    });
}

initHelpModal();

async function cancelCurrentJob(jobId) {
    const payload = jobId ? { job_id: jobId } : {};
    try {
        const response = await fetch('/api/cancel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (cancelStatus) {
            cancelStatus.textContent = data.ok
                ? 'Pedido de cancelamento enviado. Se continuar preso, force o runner do modelo.'
                : (data.message || 'Não consegui cancelar.');
        }
        await refreshJobs();
        return data;
    } catch (err) {
        if (cancelStatus) cancelStatus.textContent = 'Falha ao pedir cancelamento.';
        return { ok: false };
    }
}

async function forceCancelCurrentJob(jobId) {
    const payload = jobId ? { job_id: jobId } : {};
    const ok = window.confirm('Forçar parada vai encerrar só o runner do modelo, sem fechar o Ollama. Continuar?');
    if (!ok) return { ok: false };
    try {
        const response = await fetch('/api/force_cancel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (cancelStatus) {
            cancelStatus.textContent = data.ok
                ? 'Parada forçada enviada ao runner. O Ollama deve continuar aberto.'
                : (data.message || 'Não consegui forçar a parada.');
        }
        await refreshJobs();
        return data;
    } catch (err) {
        if (cancelStatus) cancelStatus.textContent = 'Falha ao forçar parada.';
        return { ok: false };
    }
}

async function cancelAndRetry(jobId) {
    const data = await cancelCurrentJob(jobId);
    if (!data.ok) return;
    if (cancelStatus) cancelStatus.textContent = 'Cancelamento enviado. Tentando de novo em instantes...';
    setTimeout(() => {
        if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
    }, 1800);
}

async function forceCancelAndRetry(jobId) {
    const data = await forceCancelCurrentJob(jobId);
    if (!data.ok) return;
    if (cancelStatus) cancelStatus.textContent = 'Runner do modelo forçado. Tentando de novo em alguns segundos...';
    setTimeout(() => {
        if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
    }, 3500);
}

function renderJobs(jobs) {
    const box = document.getElementById('activeJobsBox');
    if (!box) return;
    if (!jobs || !jobs.length) {
        box.innerHTML = '<div class="empty-mini">Nenhum job rodando agora. Silêncio raro, aproveite.</div>';
        return;
    }
    box.innerHTML = jobs.map(job => `
        <div class="active-job-card" data-job-id="${escapeHtml(job.id)}">
            <div class="active-job-icon"><i class="bi bi-activity"></i></div>
            <div class="active-job-main">
                <div class="active-job-title">${escapeHtml(job.model || 'Modelo')}</div>
                <div class="active-job-query">${escapeHtml(job.query_short || '')}</div>
                <div class="active-job-stage"><i class="bi bi-arrow-right-circle"></i> ${escapeHtml(job.stage || 'Rodando')}</div>
                <div class="active-job-meta">Rodando há ${escapeHtml(job.age_seconds)}s${job.cancel_requested ? ' · cancelamento solicitado' : ''}</div>
            </div>
            <div class="active-job-actions">
                <button class="btn btn-sm btn-outline-danger" type="button" onclick="cancelJob('${escapeHtml(job.id)}')">
                    <i class="bi bi-stop-fill"></i> Cancelar
                </button>
                <button class="btn btn-sm btn-danger" type="button" onclick="forceCancelJob('${escapeHtml(job.id)}')">
                    <i class="bi bi-exclamation-octagon"></i> Forçar
                </button>
            </div>
        </div>
    `).join('');
}

async function refreshJobs() {
    try {
        const response = await fetch('/api/jobs');
        const data = await response.json();
        if (data.ok) renderJobs(data.jobs || []);
    } catch (err) {
        // Mantém o painel como está. Drama zero.
    }
}

async function cancelJob(jobId) {
    const data = await cancelCurrentJob(jobId);
    if (data.ok) setTimeout(refreshJobs, 1000);
}

async function forceCancelJob(jobId) {
    const data = await forceCancelCurrentJob(jobId);
    if (data.ok) setTimeout(refreshJobs, 1000);
}

if (document.getElementById('activeJobsBox')) {
    refreshJobs();
    setInterval(refreshJobs, 3000);
}

async function testProvider(providerId, buttonEl) {
    const resultEl = document.getElementById(`provider_test_${providerId}`);
    const old = buttonEl ? buttonEl.innerHTML : '';
    if (buttonEl) {
        buttonEl.disabled = true;
        buttonEl.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Testando...';
    }
    if (resultEl) {
        resultEl.className = 'provider-test-result small text-muted';
        resultEl.textContent = 'Chamando API...';
    }
    try {
        const response = await fetch('/api/providers/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider: providerId })
        });
        const data = await response.json();
        if (resultEl) {
            resultEl.className = `provider-test-result small ${data.ok ? 'text-success' : 'text-danger'}`;
            resultEl.textContent = data.message || (data.ok ? 'OK' : 'Falha');
        }
    } catch (err) {
        if (resultEl) {
            resultEl.className = 'provider-test-result small text-danger';
            resultEl.textContent = 'Erro ao testar conexão.';
        }
    } finally {
        if (buttonEl) {
            buttonEl.disabled = false;
            buttonEl.innerHTML = old;
        }
    }
}

function setProviderResult(providerId, ok, message) {
    const resultEl = document.getElementById(`provider_test_${providerId}`);
    if (!resultEl) return;
    resultEl.className = `provider-test-result small ${ok ? 'text-success' : 'text-danger'}`;
    resultEl.textContent = message || (ok ? 'OK' : 'Falha');
}

async function saveProvider(providerId, buttonEl) {
    const keyInput = document.getElementById(`provider_key_${providerId}`);
    const enabledInput = document.getElementById(`provider_enabled_${providerId}`);
    const old = buttonEl ? buttonEl.innerHTML : '';
    if (buttonEl) {
        buttonEl.disabled = true;
        buttonEl.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Salvando...';
    }
    try {
        const response = await fetch('/api/providers/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                provider: providerId,
                api_key: keyInput ? keyInput.value : '',
                enabled: enabledInput ? enabledInput.checked : false
            })
        });
        const data = await response.json();
        if (data.ok) {
            const masked = document.getElementById(`provider_masked_${providerId}`);
            const card = document.querySelector(`[data-provider-card="${providerId}"]`);
            if (masked) masked.textContent = data.masked_key || 'não definida';
            if (card) card.dataset.providerConfigured = data.configured ? '1' : '0';
            if (keyInput) keyInput.value = '';
            filterExternalProviders();
        }
        setProviderResult(providerId, !!data.ok, data.message || 'Salvo.');
    } catch (err) {
        setProviderResult(providerId, false, 'Erro ao salvar API.');
    } finally {
        if (buttonEl) {
            buttonEl.disabled = false;
            buttonEl.innerHTML = old;
        }
    }
}

async function clearProvider(providerId, buttonEl) {
    if (!confirm('Apagar a API key deste serviço e desativar o toggle?')) return;
    const old = buttonEl ? buttonEl.innerHTML : '';
    if (buttonEl) {
        buttonEl.disabled = true;
        buttonEl.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Apagando...';
    }
    try {
        const response = await fetch('/api/providers/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider: providerId })
        });
        const data = await response.json();
        if (data.ok) {
            const masked = document.getElementById(`provider_masked_${providerId}`);
            const keyInput = document.getElementById(`provider_key_${providerId}`);
            const enabledInput = document.getElementById(`provider_enabled_${providerId}`);
            const card = document.querySelector(`[data-provider-card="${providerId}"]`);
            if (masked) masked.textContent = data.masked_key || 'não definida';
            if (keyInput) keyInput.value = '';
            if (enabledInput) enabledInput.checked = false;
            if (card) card.dataset.providerConfigured = '0';
            filterExternalProviders();
        }
        setProviderResult(providerId, !!data.ok, data.message || 'Chave apagada.');
    } catch (err) {
        setProviderResult(providerId, false, 'Erro ao apagar chave.');
    } finally {
        if (buttonEl) {
            buttonEl.disabled = false;
            buttonEl.innerHTML = old;
        }
    }
}

function setOllamaApiResult(ok, message) {
    const resultEl = document.getElementById('ollama_api_result');
    if (!resultEl) return;
    resultEl.className = `provider-test-result small ${ok ? 'text-success' : 'text-danger'}`;
    resultEl.textContent = message || (ok ? 'OK' : 'Falha');
}

async function saveOllamaApi(buttonEl) {
    const keyInput = document.getElementById('ollama_new_api_key');
    const old = buttonEl ? buttonEl.innerHTML : '';
    if (buttonEl) {
        buttonEl.disabled = true;
        buttonEl.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Salvando...';
    }
    try {
        const response = await fetch('/api/ollama-api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: keyInput ? keyInput.value : '' })
        });
        const data = await response.json();
        if (data.ok) {
            const masked = document.getElementById('ollama_key_masked');
            if (masked) masked.value = data.masked_key || 'não definida';
            if (keyInput) keyInput.value = '';
        }
        setOllamaApiResult(!!data.ok, data.message || 'Salvo.');
    } catch (err) {
        setOllamaApiResult(false, 'Erro ao salvar API da Ollama.');
    } finally {
        if (buttonEl) {
            buttonEl.disabled = false;
            buttonEl.innerHTML = old;
        }
    }
}

async function clearOllamaApi(buttonEl) {
    if (!confirm('Remover a API key atual da Ollama?')) return;
    const old = buttonEl ? buttonEl.innerHTML : '';
    if (buttonEl) {
        buttonEl.disabled = true;
        buttonEl.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Removendo...';
    }
    try {
        const response = await fetch('/api/ollama-api/clear', { method: 'POST' });
        const data = await response.json();
        if (data.ok) {
            const masked = document.getElementById('ollama_key_masked');
            const keyInput = document.getElementById('ollama_new_api_key');
            if (masked) masked.value = data.masked_key || 'não definida';
            if (keyInput) keyInput.value = '';
        }
        setOllamaApiResult(!!data.ok, data.message || 'Removida.');
    } catch (err) {
        setOllamaApiResult(false, 'Erro ao remover API da Ollama.');
    } finally {
        if (buttonEl) {
            buttonEl.disabled = false;
            buttonEl.innerHTML = old;
        }
    }
}

async function testOllamaApi(buttonEl) {
    const old = buttonEl ? buttonEl.innerHTML : '';
    if (buttonEl) {
        buttonEl.disabled = true;
        buttonEl.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Testando...';
    }
    setOllamaApiResult(true, 'Testando conexão...');
    try {
        const response = await fetch('/api/ollama-api/test', { method: 'POST' });
        const data = await response.json();
        setOllamaApiResult(!!data.ok, data.message || (data.ok ? 'OK' : 'Falha'));
    } catch (err) {
        setOllamaApiResult(false, 'Erro ao testar API da Ollama.');
    } finally {
        if (buttonEl) {
            buttonEl.disabled = false;
            buttonEl.innerHTML = old;
        }
    }
}

function filterExternalProviders() {
    const searchEl = document.getElementById('externalAiSearch');
    const filterEl = document.getElementById('externalAiStatusFilter');
    const countEl = document.getElementById('externalAiFilterCount');
    const query = (searchEl?.value || '').trim().toLowerCase();
    const filter = filterEl?.value || 'all';
    const cards = Array.from(document.querySelectorAll('[data-provider-card]'));
    let visible = 0;

    cards.forEach((card) => {
        const providerId = card.dataset.providerCard;
        const enabled = document.getElementById(`provider_enabled_${providerId}`)?.checked || false;
        const configured = card.dataset.providerConfigured === '1';
        const testType = card.dataset.providerTest || 'manual';
        const haystack = `${card.dataset.providerName || ''} ${card.dataset.providerCategory || ''} ${card.dataset.providerNote || ''}`;

        const matchesSearch = !query || haystack.includes(query);
        let matchesFilter = true;
        if (filter === 'active') matchesFilter = enabled;
        if (filter === 'inactive') matchesFilter = !enabled;
        if (filter === 'configured') matchesFilter = configured;
        if (filter === 'missing_key') matchesFilter = !configured;
        if (filter === 'real_test') matchesFilter = testType !== 'manual';
        if (filter === 'basic_test') matchesFilter = testType === 'manual';

        const show = matchesSearch && matchesFilter;
        card.classList.toggle('d-none', !show);
        if (show) visible += 1;
    });

    if (countEl) countEl.textContent = `${visible} de ${cards.length} exibidas`;
}

function clearExternalProviderFilters() {
    const searchEl = document.getElementById('externalAiSearch');
    const filterEl = document.getElementById('externalAiStatusFilter');
    if (searchEl) searchEl.value = '';
    if (filterEl) filterEl.value = 'all';
    filterExternalProviders();
}

document.addEventListener('DOMContentLoaded', () => {
    applyExecutionProfile();
    document.querySelectorAll('[id^="provider_enabled_"]').forEach((el) => {
        el.addEventListener('change', filterExternalProviders);
    });
    filterExternalProviders();
});

function readyMadeSetStatus(message, isError = false) {
    const el = document.getElementById('readyMadeStatus');
    if (!el) return;
    el.textContent = message;
    el.classList.toggle('is-error', Boolean(isError));
}

function currentReadyMadeSearchPayload() {
    const getValue = (name) => {
        const el = form?.querySelector(`[name="${name}"]`);
        return el ? el.value : '';
    };
    const cleanAnswer = document.getElementById('answerBox')?.innerText || '';
    const fullAnswer = document.getElementById('answerCopyText')?.value || cleanAnswer;
    return {
        format: 'ollama-web-platform-ready-made-search-v1',
        app: 'Ollama Web Platform',
        exported_at: new Date().toISOString(),
        title: (getValue('query') || 'Pesquisa pronta').split('\n')[0].slice(0, 90),
        query: getValue('query'),
        config: {
            execution_profile: getValue('execution_profile'),
            model: getValue('model'),
            mode: getValue('mode'),
            response_engine: getValue('response_engine'),
            search_engine: getValue('search_engine'),
            task_group: getValue('task_group'),
            max_results: getValue('max_results'),
            temperature: getValue('temperature')
        },
        answer: {
            clean: cleanAnswer,
            full: fullAnswer
        },
        notes: 'Importe este JSON no menu Pesquisar para restaurar pergunta + configurações e clicar em Buscar.'
    };
}

function exportReadyMadeSearch() {
    const payload = currentReadyMadeSearchPayload();
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' });
    const link = document.createElement('a');
    const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    link.href = URL.createObjectURL(blob);
    link.download = `ready_made_search_${stamp}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
    readyMadeSetStatus('Pesquisa atual exportada em JSON.');
}

function getReadyMadeConfig(data) {
    if (!data || typeof data !== 'object') return {};
    return data.config || data.settings || data.ready_made_search?.config || data.search?.config || data;
}

function getReadyMadeQuery(data) {
    if (!data || typeof data !== 'object') return '';
    return data.query || data.prompt || data.search?.query || data.ready_made_search?.query || '';
}

function setNamedField(name, value) {
    if (value === undefined || value === null || value === '') return;
    const el = form?.querySelector(`[name="${name}"]`);
    if (!el) return;
    if (el.tagName === 'SELECT') {
        const hasOption = Array.from(el.options || []).some((option) => option.value === String(value));
        if (hasOption) el.value = String(value);
        return;
    }
    el.value = String(value);
}

function applyReadyMadeSearch(data) {
    const config = getReadyMadeConfig(data);
    const query = getReadyMadeQuery(data);
    if (query) {
        const questionInput = document.getElementById('questionInput');
        if (questionInput) questionInput.value = query;
    }

    // Perfil primeiro, porque ele abre/fecha acordeões e ajusta defaults.
    setNamedField('execution_profile', config.execution_profile || config.profile || config.como_rodar);
    applyExecutionProfile();

    const map = {
        mode: config.mode || config.modo,
        response_engine: config.response_engine || config.motor_resposta,
        search_engine: config.search_engine || config.motor_busca,
        task_group: config.task_group || config.grupo_recomendado || config.group,
        max_results: config.max_results || config.fontes,
        temperature: config.temperature || config.temperatura
    };
    Object.entries(map).forEach(([name, value]) => setNamedField(name, value));

    const importedModel = config.model || config.modelo;
    let modelWarning = '';
    if (importedModel) {
        const wanted = String(importedModel).toLowerCase();
        const exactChoice = modelChoices.find((choice) => String(choice.dataset.name || '').toLowerCase() === wanted);
        if (exactChoice) {
            selectModel(exactChoice);
        } else {
            if (modelInput) modelInput.value = importedModel;
            modelWarning = ' Modelo importado não apareceu no catálogo; confira antes de buscar.';
        }
    }

    readyMadeSetStatus(`Pesquisa importada. Revise os campos e clique no botão azul para buscar.${modelWarning}`);
}

async function importReadyMadeSearchFromFile(input) {
    const file = input?.files?.[0];
    if (!file) return;
    try {
        const raw = await file.text();
        const data = JSON.parse(raw);
        applyReadyMadeSearch(data);
    } catch (err) {
        readyMadeSetStatus('Não consegui importar. Verifique se o arquivo é um JSON válido.', true);
    } finally {
        if (input) input.value = '';
    }
}

let pcStatsTimer = null;

function getNestedValue(obj, path) {
    return String(path || '').split('.').reduce((current, key) => (current && current[key] !== undefined ? current[key] : undefined), obj);
}

function formatPcStat(path, value) {
    if (value === undefined || value === null || value === '') return '--';
    if (['cpu.percent', 'memory.percent', 'disk.percent'].includes(path)) return `${value}%`;
    if (['processes.ollama.memory_mb', 'processes.python.memory_mb'].includes(path)) return `${value} MB`;
    if (path === 'updated_at') return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    return value;
}

function pcStatPercentForPath(path, value, data) {
    const numericValue = Number(value || 0);
    if (['cpu.percent', 'memory.percent', 'disk.percent'].includes(path)) {
        return Math.max(0, Math.min(100, numericValue));
    }
    if (['processes.ollama.memory_mb', 'processes.python.memory_mb'].includes(path)) {
        const totalMb = Number(data?.memory?.total_gb || 0) * 1024;
        if (!totalMb) return 0;
        return Math.max(0, Math.min(100, (numericValue / totalMb) * 100));
    }
    return null;
}

function pcStatLevel(percent) {
    if (percent === null || percent === undefined) return 'info';
    if (percent >= 93) return 'critical';
    if (percent >= 80) return 'hot';
    if (percent >= 60) return 'warn';
    return 'ok';
}

function applyPcStatColor(el, path, value, data) {
    const card = el.closest('.pc-stat-card');
    if (!card) return;
    card.classList.remove('pc-stat-ok', 'pc-stat-warn', 'pc-stat-hot', 'pc-stat-critical', 'pc-stat-info');
    const percent = pcStatPercentForPath(path, value, data);
    const level = pcStatLevel(percent);
    card.classList.add(`pc-stat-${level}`);
    card.style.setProperty('--usage-pct', percent === null || percent === undefined ? '0%' : `${Math.round(percent)}%`);
}

function renderPcStats(data) {
    const message = document.getElementById('pcStatsMessage');
    if (!data || !data.ok) {
        if (message) message.textContent = data?.message || 'Stats do PC indisponíveis.';
        return;
    }

    document.querySelectorAll('[data-pc-stat]').forEach((el) => {
        const path = el.dataset.pcStat;
        const value = path === 'updated_at' ? 'now' : getNestedValue(data, path);
        el.textContent = formatPcStat(path, value);
        applyPcStatColor(el, path, value, data);
    });

    if (message) {
        const ram = data.memory ? `${data.memory.used_gb} GB / ${data.memory.total_gb} GB` : '--';
        const cpu = data.cpu ? `${data.cpu.count} threads · leitura por amostra curta` : '--';
        message.textContent = `CPU: ${cpu} · RAM: ${ram} · cores: verde ok, amarelo atenção, laranja alto, vermelho crítico.`;
    }
}

async function refreshPcStats() {
    if (!document.querySelector('[data-pc-stats-root]')) return;
    try {
        const response = await fetch('/api/pc-stats');
        const data = await response.json();
        renderPcStats(data);
    } catch (err) {
        renderPcStats({ ok: false, message: 'Erro ao ler stats do PC.' });
    }
}

function startPcStatsPolling() {
    if (pcStatsTimer) return;
    refreshPcStats();
    pcStatsTimer = setInterval(refreshPcStats, 2000);
}

function stopPcStatsPolling() {
    if (!pcStatsTimer) return;
    clearInterval(pcStatsTimer);
    pcStatsTimer = null;
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('[data-pc-stats-panel]')) {
        startPcStatsPolling();
    }

    const pcModal = document.getElementById('pcStatsModal');
    if (pcModal) {
        pcModal.addEventListener('shown.bs.modal', startPcStatsPolling);
        pcModal.addEventListener('hidden.bs.modal', () => {
            if (!document.querySelector('[data-pc-stats-panel]')) stopPcStatsPolling();
        });
    }
});
