# Histórico de mudanças

## 2.4.1 — Vídeos de menor tamanho
- Opções de resolução máxima até 360p, 240p e 144p na aba YouTube, além das existentes.
- Seleção de formato restringe a altura do vídeo; não amplia artificialmente vídeos abaixo do limite nem substitui o limite por uma resolução superior indisponível.
- Mesmo mecanismo de download, áudio, histórico e atualização; validação de API, seleção de formatos e testes da interface cobrindo as novas opções.
- Arquivos geralmente menores, sem promessa de tamanho fixo: a disponibilidade e bitrate dependem da origem e da duração.


## 2.4.0 — Navegação por abas
- Janela única do Clássica: YouTube e X em abas, sem lançar o Hub/Tkinter intermediário.
- Módulo X independente inicia na aba de forma local e autenticada, sem abrir outro navegador.
- Instalação ou atualização de compatibilidade do X automaticamente ao acessar a aba pela primeira vez, com verificação SHA-256; reaberturas reutilizam a versão já instalada. Falhas permitem tentar novamente sem afetar o YouTube.
- Aceite de uso responsável consistente entre as duas plataformas.
- Histórico e mecanismos de download mantidos em processos e pastas separadas.

## 2.3.0

- Biblioteca modular acessível em **Plataformas**, com instalação opt-in do Clássica X e da central de aplicativos (Hub).
- Os módulos usam Releases oficiais separados, validação SHA-256 e pastas versionadas por aplicativo; atualização e retorno à versão anterior independentes.
- Preservado integralmente o motor de download YouTube, o histórico e o atualizador guiado existente.
- O Clássica X usa a identidade visual marfim, filetes dourados e símbolo ☧ já aplicada à Clássica.
- O X ainda depende da disponibilidade das publicações públicas na plataforma; apenas conteúdos autorizados.


## 2.2.2

- A opção de atalhos permanece visível após a instalação e permite **Criar ou atualizar atalhos** sem reinstalar a aplicação.
- A criação dos atalhos valida a instalação gerenciada e mantém a sessão aberta depois de concluir.

## 2.2.1

- Clareza na instalação: a ação da Ajuda passou a se chamar **Instalar e criar atalhos**, explicando que ela prepara a cópia gerenciada e cria atalhos na Área de Trabalho e no menu Iniciar.

## 2.2.0

- Identidade visual própria: serifas clássicas, marfim, filetes e arabescos vetoriais discretos; marca ☧ preservada.
- Ícone na área de notificação com Abrir e Encerrar; uma única instância por pasta e perfil.
- Instalação opcional no perfil, com atalhos na Área de Trabalho e menu Iniciar, sem administrador ou inicialização automática.
- Atualização guiada pelo repositório oficial, ZIP verificado por tamanho e SHA256, extração protegida e preparação antes da troca; retorno à versão anterior após atualizar.
- Prévia explícita de título, duração e qualidades do link, respeitando pausas do YouTube.
- Diagnóstico com orientação de falhas e relatório copiável sem links, títulos, caminhos ou credenciais.
- Sem removedor e sem assinatura digital. Mantidas as limitações de disponibilidade do YouTube.

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
