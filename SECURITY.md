# Segurança e privacidade

## Escopo

A interface e o servidor executam no computador do usuário. O servidor escuta
apenas em `127.0.0.1`, com porta aleatória por sessão. Operações da API exigem
um token de sessão; o servidor verifica Host e Origin. Não há configuração de
CORS para sites externos. Os arquivos da interface são servidos com CSP,
proteção contra enquadramento e sem cache de sessão.

O extrator recebe argumentos como lista, sem interpretação por shell, e ignora
configurações externas do yt-dlp. Só são aceitos links de vídeos do YouTube.
Os nomes de arquivo são sanitizados pelo extrator. A entrega de arquivos limita
o caminho à pasta de saída registrada no trabalho.

Estas medidas não criam uma sandbox para os componentes externos. Python,
FFmpeg, uv e Deno são programas executados com as permissões do usuário. Uma
revisão estática e testes funcionais não são certificação antimalware.

## Distribuição inicial

- `requirements.lock` fixa versões Python e hashes das distribuições.
- `tools.lock.json` fixa URLs versionadas e SHA256 dos pacotes Windows.
- O instalador valida SHA256 antes de extrair os componentes externos.
- Python é provisionado pelo uv; sua distribuição é gerenciada por esse
  fornecedor. Isso é uma dependência transitiva adicional, não uma assinatura
  criptográfica emitida pela ☧ SYSTEMS.
- O pacote não contém senhas, tokens, cookies, executáveis externos ou mídias.
- Código-fonte, histórico de mudanças e hash do ZIP acompanham a publicação.
- A preparação modifica componentes somente dentro da pasta da aplicação.
  Não existe ferramenta para limpar a raiz da unidade.

## Atualização explícita do extrator

`Atualizar.bat` permite atualizar yt-dlp e dependências via PyPI. Essa escolha
do usuário sai da baseline fixada: seus resultados não herdam automaticamente
os testes da versão 2.0.0. A ocorrência fica registrada localmente em
`.tools/perfil-atualizado.txt`. Mudanças no código da Clássica vêm de novas
versões do projeto, não dessa atualização.

## Dados e conexão

O histórico contém URLs, títulos, caminhos e detalhes recentes de erro. Esses
dados ficam no perfil local do usuário; não devem ser incluídos em issues ou
commits sem revisão. O navegador guarda somente a preferência de tamanho de
texto. Não existe telemetria própria, sincronização remota ou coleta de senhas.
YouTube recebe as solicitações necessárias ao download. Fornecedores de
componentes recebem conexões durante preparação e atualização.

## Interface sem autenticação por navegador

A interface, a API local e o mecanismo de download não oferecem leitura de cookies de navegadores. Uma opção `use_edge_session` em pedidos à API é rejeitada; históricos antigos têm o campo removido ao carregar. O comando do extrator nunca recebe `--cookies-from-browser`. O aplicativo não garante acesso a conteúdos sujeitos a restrições do YouTube.

## Relatar um problema

Use o canal privado de avisos de segurança do repositório quando estiver
habilitado. Não publique credenciais, arquivos pessoais, histórico completo ou
URLs assinadas. Informe versão, sistema operacional, comportamento observado
e passos mínimos com dados de teste. Alertas de antivírus devem ser analisados
com o nome da detecção e o caminho, antes de liberar o arquivo.

## Limites conhecidos

Não houve auditoria independente, assinatura de código Windows ou varredura
antivírus dos componentes baixados no computador do usuário. A aplicação não
oferece autenticação multiusuário, servidor público ou isolamento de sistema
operacional. Não exponha a porta local à internet.
