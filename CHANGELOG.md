# Histórico de mudanças

## 2.1.2

- Pasta principal limpa: somente Clássica.exe, Leia-me.txt e Componentes. Scripts e arquivos técnicos ficam agrupados, com um único ponto de entrada visível.

- Pasta extraída identificada como `Classica-2.1.2`, sem instruções para mesclar arquivos de versões diferentes.
- Abrir novamente recupera a mesma sessão se a aba foi fechada. Depois de Sair, uma nova inicialização aguarda a liberação da sessão anterior.
- Instalação de outra versão ainda ativa recebe uma mensagem clara, sem abrir silenciosamente a versão antiga. Os registros de cada abertura têm arquivos próprios.

- O ZIP inclui Clássica.exe com nome, ícone ☧ e metadados do produto; compilação do código-fonte no Windows, sem empacotador de terceiros.
- Janela de preparação com progresso, detalhes e erros; abertura discreta da aplicação existente, sem instalação de atalhos ou privilégios administrativos.
- Compilação integrada aos testes e ao release. Validação em Windows do executável extraído do ZIP, caminhos com espaços e acentos e encerramento pelo botão Sair.

## 2.1.1 — 2026-10-17

- Refinamento visual discreto de painéis e hierarquia, preservando o símbolo canônico ☧, cores funcionais e acessibilidade; dourado suave apenas em detalhes simbólicos e divisórias, com superfícies claras e sem sombras.
- Botão “Limpar biblioteca” destacado; operação existente remove somente itens encerrados do histórico, sem apagar mídias ou downloads ativos.
- Aviso de uso responsável junto ao download, com explicação complementar na ajuda; não representa exoneração geral de responsabilidade.
- Inicialização discreta **opcional** em `Iniciar discreto.bat`: mantém o serviço local após fechar a janela de preparação; o modo clássico permanece disponível para diagnóstico. O ciclo de vida e a saída pelo botão Sair são testados num Windows limpo.

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
