# Histórico de mudanças

## 2.1.1 — candidata, ainda não publicada

- Refinamento visual sóbrio: linhas técnicas discretas e detalhe metálico suave, com o monograma cristológico ☧ preservado.
- Aviso de responsabilidade pelo uso e acesso às condições sem aceitar licenças fictícias ou interromper o fluxo de download.
- Botão **Limpar concluídos** remove apenas downloads finalizados do histórico, preservando erros, tarefas pendentes e todos os arquivos; a limpeza total anterior continua disponível.
- Regressões Python/API e Playwright para limpeza, privacidade, responsividade e uso responsável.
- Nenhuma mudança no mecanismo de download, yt-dlp, FFmpeg ou formatos disponíveis.


## 2.1.0 — 2026-10-17

- Pausa global de 60 segundos ao receber HTTP 429, uma única tentativa automática e pausa manual se o limite persistir.
- Espaçamento entre requisições e downloads; eliminação de novas tentativas internas de extração sobrepostas à política da fila.
- FFprobe valida áudio/vídeo antes de declarar sucesso, incluindo o caso em que a rede devolve HTML no lugar da mídia.
- Correção da classificação de formato indisponível, que podia ser confundido com vídeo removido.
- Verificação da presença do pacote EJS necessário ao extrator.

- Revisão para publicação: removida integralmente a opção experimental do Edge da interface e do extrator. A API rejeita pedidos com cookies do navegador; histórico antigo é normalizado. O fluxo de download permanece com os mesmos parâmetros de áudio, vídeo e recuperação de rede.
- Mensagens para HTTP 429, pedidos de verificação e PO Token sem recomendar autenticação pelo navegador ou desativar proteções.
- Ajuda distingue atualização do extrator de limites HTTP 429 e exigências de login/PO Token, sem prometer correção automática.

## 2.0.0 — 2026-10-17

- Nova interface operacional, clara, responsiva e assinada **by ☧ SYSTEMS**.
- Tipografia fluida e controle de leitura entre 100% e 200%.
- Opções de áudio e vídeo com estados, dicas e progresso explícitos.
- Navegação por teclado, link para conteúdo, foco visível e diálogos rotulados.
- Remoção da ferramenta de organização de extrações antigas do pacote.
- Dependências Python com versões e hashes; componentes Windows com URLs
  versionadas e SHA256 obrigatório na preparação inicial.
- Script de empacotamento com lista explícita, uma pasta superior e SHA256.
- Testes e workflows para Linux, Windows, interface e publicação por tag.
- Documentação de arquitetura, segurança, identidade e requisitos de qualidade.

## 1.1.0 — 2026-10-17

- Vídeo com som em MP4, MKV e WebM, com limite de resolução.
- Histórico distingue resoluções; nomes de arquivo evitam colisões.

## 1.0.0 — 2026-10-17

- Primeira versão local, com formatos de áudio, fila e histórico.
