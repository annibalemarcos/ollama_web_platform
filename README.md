# Ollama Web Platform v52

Plataforma local em Flask + Bootstrap para pesquisar na web, mandar as fontes para o Ollama local e gerar uma resposta em português.

## Como rodar

1. Extraia o ZIP.
2. Abra o Ollama no Windows.
3. Rode `run_once.bat`.
4. Acesse: `http://127.0.0.1:5388`

## Novidades da v18

- O seletor de modelos agora permite **baixar** modelos que ainda não estão instalados.
- Modelos instalados mostram botão **X** para excluir pelo próprio dropdown.
- O download chama `ollama pull <modelo>` em segundo plano.
- A exclusão chama `ollama rm <modelo>`.
- O app mostra uma caixinha de status com logs do download/exclusão e recarrega a página quando termina.

## Também incluído

- Barra de carregamento durante perguntas.
- Jobs com etapa atual no Status.
- Fontes em acordeão compacto.
- Cancelar e Forçar parada para jobs presos.

## Observação

Se usar **Forçar parada**, o app pode encerrar o Ollama. Abra o Ollama novamente antes de baixar/executar modelos.

## Ajuste v22

- A janela extra do servidor aberta por `run_once.bat` e `run_economico.bat` agora também executa `mode con: cols=68 lines=14`.
- Isso reduz o tamanho do terminal chamado **Ollama Web Platform ECO** em vez de abrir aquele telão preto gigante.

## Ajuste v23

- `run_once.bat` e `run_economico.bat` agora usam `scripts\positioned_server.ps1`.
- A janela do servidor **Ollama Web Platform ECO** salva a posição/tamanho em `data\console_window_position.json`.
- Na próxima execução, ela abre no mesmo lugar, inclusive em segundo monitor ou coordenadas negativas.
- Se quiser resetar, apague `data\console_window_position.json`.

## Ajuste v24

- O dropdown de modelos agora mostra uma mini barra de status dentro do próprio item durante download/instalação ou exclusão.
- A barra aparece abaixo do status do modelo, mantendo o card compacto e visualmente claro.

## Ajuste v27

- A posição da janela do servidor agora fica salva fora da pasta do projeto, para sobreviver a novas versões extraídas.
- Arquivo persistente usado:

```text
E:\my_projects\py_misc\ollama_web_platform_console_window_position.json
```

- Se o arquivo existir e tiver posição válida, o app lê e restaura a janela.
- Se não existir, o script aguarda alguns segundos depois de abrir a janela antes de criar/gravar a primeira posição real. Isso dá tempo de arrastar a janela para o monitor/canto desejado.
- Se a pasta `E:\my_projects\py_misc` não puder ser criada/acessada, o script usa fallback local em `data\console_window_position.json`.


## Ajuste v28

- `run_once.bat` agora chama `scripts\positioned_server.ps1` com `-InitialPositionDelaySeconds 12`.
- Quando ainda não existe posição salva válida, a janela **Ollama Web Platform ECO** abre e o script espera **12 segundos** antes de gravar o arquivo de posição.
- Esse tempo serve para você arrastar a janela para o segundo monitor, canto X/Y ou tamanho desejado antes do primeiro salvamento.
- Se já existir uma posição válida em `E:\my_projects\py_misc\ollama_web_platform_console_window_position.json`, o app restaura imediatamente e não fica esperando.
- Para escolher uma nova posição do zero, apague o arquivo persistente e rode `run_once.bat` novamente.


## Ajuste v29

- `run_once.bat` e `run_economico.bat` agora usam `-InitialPositionDelaySeconds 12`.
- Quando não existir posição salva, o script mostra uma mensagem avisando que a janela está pronta e que você já pode mover o terminal.
- Depois dos 12 segundos, ele cria/atualiza o JSON de posição e mostra outra mensagem confirmando que a posição foi gravada.
- Se já existir posição válida, ele restaura direto, sem espera.


## Ajuste v30

- O campo **Resposta** agora renderiza um subconjunto de Markdown, em vez de mostrar tudo como texto cru.
- Blocos com ```linguagem continuam virando cards de código com botão **Copiar**.
- Títulos em `**negrito:**`, listas numeradas, bullets, links crus e `código inline` agora ficam formatados de forma mais parecida com uma interface de chat moderna.
- Também vale para a página de detalhe do histórico.


## Ajuste v31

- Removida a automação de refresh/abertura automática do navegador.
- `run_once.bat` e `run_economico.bat` agora apenas sobem o servidor Flask e mostram a URL para abrir manualmente.
- O script `scripts
efresh_browser.ps1` foi removido do pacote.


## Ajuste v32

- O botão principal de iniciar agora fica logo abaixo da pergunta, antes dos controles avançados.
- A barra de ação ficou sticky/visível durante a configuração, reduzindo a necessidade de rolar a tela para enviar.
- O resumo do modelo selecionado agora fica recolhido por padrão em uma área clicável, para não empurrar o botão para baixo.
- A caixa da pergunta ficou mais compacta e o topo da página foi levemente reduzido para melhorar o fluxo.


## Ajuste v33

- O campo de pergunta virou um compositor no estilo chat: os botões de enviar, cancelar, forçar parada e limpar ficam dentro da própria área da pergunta.
- Quando já existe resposta, aparece no compositor o botão **Ir para resposta**.
- Abaixo da resposta, foi adicionado o botão **Voltar para pergunta**, para subir direto ao campo de entrada.
- A barra de ação externa foi removida do fluxo principal para reduzir rolagem e deixar o envio mais imediato.


## Ajuste v34

- O campo **Resposta** ficou mais limpo e menos parecido com uma caixa de formulário.
- Citações inline como `[1], [2], [3]` agora viram chips visuais discretos.
- Uma seção final `Fontes:` gerada pelo modelo é removida quando o app já está mostrando as fontes no painel lateral.
- Links crus continuam clicáveis e código/Markdown básico seguem formatados.


## Ajuste v36

- Corrigido o erro `name '_strip_inline_citations' is not defined`.
- A função que limpa citações inline agora existe no `app.py` antes de ser chamada pelo renderizador da resposta.


## Ajuste v37

- O modal de ajuda do campo **Modo** agora explica cada opção: Direto, Detalhado, Pesquisa Web e Técnico.
- A explicação mostra claramente quais modos usam apenas o Ollama local e qual modo usa web/API.
- O comportamento também foi ajustado: somente **Pesquisa Web** chama a busca online; Direto, Detalhado e Técnico rodam localmente sem busca web.
- O modal de **Fontes** agora deixa claro que esse campo só afeta o modo Pesquisa Web.


## Ajuste v38

- Adicionada seção **Outras IAs / APIs externas** em Configurações.
- Incluídos provedores: Copilot, You.com, Exa, Exa Websets, Kagi, Brave Search, Andi, Consensus, Elicit, NotebookLM, WolframAlpha, Ithy, Gemini, iAsk, Perplexity, Claude/Anthropic e ChatGPT/OpenAI.
- Cada provedor tem campo para API key, toggle individual de ativar/desativar, opção de apagar chave e botão **Testar conexão**.
- Adicionado toggle **Ativar todas que tiverem API key ao salvar**.
- Status agora mostra uma seção de IAs/APIs externas com botão **Stats** para cada provedor, abrindo modal com estado, chave mascarada, tipo de teste e observações.
- Observação: esta etapa cria a infraestrutura de configuração/teste/monitoramento. O roteamento de perguntas para esses provedores pode ser adicionado na próxima etapa.


## Ajuste v39

- Adicionados dropdowns no campo principal para **Motor de resposta**, **Motor de busca** e **Grupo recomendado**.
- Todo dropdown novo inclui sempre as opções **Auto** e **Todos**.
- Provedores externos só aparecem nos dropdowns quando estão ativados e com API key configurada em Configurações.
- Adicionadas explicações nos botões `?` para indicar melhores grupos: local leve, web/preço/notícia, código/técnico, acadêmico e matemática/cálculo.
- O grupo recomendado agora entra no prompt para orientar estilo/estratégia da resposta.
- Ajustada a contagem de buscas no Status para considerar fontes usadas, evitando confundir modo local com busca web.


## Ajuste v40

- Adicionada ao dropdown **Motor de busca** a opção **Somente local (sem web)**.
- Essa opção força o app a pular busca web/API externa mesmo se o modo selecionado for Pesquisa Web.
- O modal `?` do Motor de busca agora explica quando usar Somente local, Auto, Todos e buscadores web.


## Ajuste v41

- Na seção **Outras IAs / APIs externas**, o checkbox **Apagar chave deste serviço** foi substituído por um botão **Apagar chave**.
- Cada provedor agora tem botão individual **Salvar API** para salvar apenas aquela integração sem precisar salvar a tela inteira.
- Adicionados endpoints internos para salvar e apagar uma API específica via AJAX.
- Ao salvar/apagar, a chave mascarada e o status visual do card são atualizados na própria tela.


## Ajuste v42

- Na seção **API da Ollama**, removido o checkbox **Apagar a API key atual**.
- Adicionados botões individuais: **Salvar API**, **Testar conexão** e **Remover chave**.
- Criados endpoints internos AJAX para salvar, testar e remover a chave da API da Ollama sem depender do botão geral da página.
- A chave mascarada é atualizada na tela após salvar/remover.


## Ajuste v43

- `.env` atualizado com a nova API key da Ollama fornecida para testes.
- Não publique este ZIP em repositório público enquanto essa chave estiver no `.env`.


## Ajuste v44

- Adicionado sistema de busca/filtro na seção **Outras IAs / APIs externas** em Configurações.
- Agora é possível buscar por nome, categoria ou observação do provedor.
- Adicionados filtros: todas, somente ativas, somente desativadas, somente com API key, somente sem API key, teste real e teste básico.
- Incluído contador de cards exibidos e botão para limpar filtros.
- Ao salvar ou apagar uma chave individual, os filtros são atualizados automaticamente.

## Ajuste v45

- Adicionado dropdown **Como rodar** para escolher o fluxo principal: Padrão, Somente local, Pesquisa Web guiada, Avançado ou Todos/Multi-IA.
- O seletor **Modelo local (Ollama)** saiu da linha principal e agora fica dentro de um acordeão próprio.
- **Motores, busca, grupo recomendado e fontes** ficam em outro acordeão, exibido conforme o perfil escolhido.
- O perfil **Somente local** força `search_engine=local_only`, modo direto e grupo local leve.
- O perfil **Pesquisa Web guiada** abre os controles de web/busca e prepara modo web.

## Ajuste v46

- Adicionados botões em **Configurações** para **Exportar configurações** e **Importar configurações**.
- O export gera um JSON completo com todas as configurações locais, incluindo API keys salvas.
- O import aceita o JSON exportado pelo app e também arquivos `.env` simples com linhas `CHAVE=valor`.
- O arquivo exportado contém segredos; não deve ser enviado para GitHub nem compartilhado publicamente.

## Ajuste v47

- A área de resposta agora tem dois botões separados:
  - **Copiar resposta**: copia somente a versão limpa/visível da resposta.
  - **Copiar resposta completa**: copia o texto integral original, incluindo referências inline e conteúdo preservado no acordeão.
- O mesmo comportamento foi aplicado também no detalhe do Histórico.

## Ajuste v48

- Adicionado perfil **Web/Cloud (sem Ollama local)** no dropdown **Como rodar**.
- Adicionada opção **Web/Cloud (sem Ollama local)** no dropdown **Motor de resposta**.
- Quando esse motor é usado, o app pula a verificação do modelo local e gera a resposta final usando uma IA externa ativa/configurada.
- Implementado roteamento inicial para Perplexity, ChatGPT/OpenAI, Claude/Anthropic e Gemini.
- A busca web continua podendo alimentar fontes antes da resposta, mas a geração final não precisa mais passar pelo Ollama local.

## Ajuste v49

- Adicionada opção em **Configurações** para ativar/desativar **Stats do PC em tempo real**.
- Quando ativo, o app mostra CPU, RAM, disco, rede, processo Ollama e processo Python.
- O menu **Status e uso** passa a exibir o painel de stats do PC com atualização automática.
- A tela **Pesquisar** ganha um botão de ícone no topo, antes do botão de status, que abre os stats do PC em um modal.
- O monitoramento só consulta o PC quando está ativado e visível, evitando deixar o app mais pesado à toa.
- Adicionado `psutil` às dependências.

## Ajuste v50

- Corrigido o comportamento de cancelamento/parada.
- **Cancelar** marca o job para interrupção e tenta descarregar o modelo com `ollama stop`, sem fechar o app/daemon do Ollama.
- **Forçar** não mata mais todos os processos `ollama*`; agora tenta encerrar apenas o runner do modelo (`ollama_llama_server` / `llama-server`).
- As mensagens da interface foram ajustadas para deixar claro que a parada forçada mira o runner do modelo, não o Ollama inteiro.

## Ajuste v51

- Corrigido erro do Gemini quando a API retorna `404` para `models/gemini-1.5-flash`.
- O modelo padrão do Gemini foi atualizado para `gemini-3.1-flash-lite`.
- O cliente Gemini agora tenta descobrir automaticamente, via endpoint de modelos da própria Gemini API, quais modelos suportam `generateContent`.
- Se o modelo configurado em `AI_GEMINI_MODEL` não existir ou retornar `404`, o app tenta outro modelo compatível antes de desistir.
- Adicionadas variáveis opcionais ao `.env.example` para modelos cloud:
  - `AI_CHATGPT_MODEL`
  - `AI_PERPLEXITY_MODEL`
  - `AI_CLAUDE_MODEL`
  - `AI_GEMINI_MODEL`
  - `CLOUD_AI_TIMEOUT`

### Observação sobre Gemini

A API do Gemini muda nomes e disponibilidade de modelos com alguma frequência. Por isso, em vez de depender apenas de um ID fixo, o app agora usa fallback automático e prefere modelos que suportem `generateContent`.

## Ajuste v52

- Versão de continuidade gerada a partir da linha normal do projeto, mantendo a correção do Gemini feita na v51.
- README atualizado para acompanhar a nova versão.
- Sem alteração funcional adicional nesta versão: o objetivo foi deixar o pacote numerado e documentado para seguir a linha principal de desenvolvimento.

