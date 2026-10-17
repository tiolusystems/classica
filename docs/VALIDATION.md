# Registro de verificação

## 2.1.0 — 17/10/2026

- Linux: 33 testes passaram, incluindo consentimento Edge ausente/presente,
  rejeição de valores inválidos, novas tentativas e não persistência.
- Nenhum cookie real foi lido nos testes. O fluxo HTTP usa um gerenciador sem
  worker; comandos são inspecionados sem executar a leitura do Edge.
- Sintaxe JavaScript e contrato de distribuição passaram. A suíte de interface
  foi ampliada para aceitar/recusar o consentimento, envio na API e reset ao
  recarregar, mas não executou: o Chromium não está instalado e o download
  retornou um ZIP vazio/truncado. Não se afirma aprovação visual desta versão.
- Não foi validada a descriptografia de cookies no Windows/Edge do usuário.
  A proteção do navegador pode impedir o recurso; não há promessa de eliminar
  HTTP 429, exigências de login ou PO Token.
- Recuperação HTTP 429: testes de uma tentativa automática, pausa global,
  recusa de retomada antecipada e persistência da pausa.
- Respostas HTML não passam pela validação de mídia nem são marcadas como
  concluídas mesmo quando o extrator encerra com código zero.
- Teste remoto do vídeo r30D3SW4OVw: consulta retornou título; a tentativa de
  mídia recebeu HTML de 195 bytes com “Site Unavailable”, rejeitado pelo FFprobe.
  Isso é uma limitação desta conexão remota, não o diagnóstico do Windows do
  usuário. Não houve download de mídia válido confirmado para esse vídeo.
- O pacote local 2.1.0 não implica publicação no GitHub nem aprovação na CI.

## Registro histórico — 2.0.0

Data: 17/10/2026. Ambiente de trabalho: Linux.

## Executado

- A suíte original de 21 testes passou após a nova interface e a identificação
  da versão. Inclui yt-dlp e FFmpeg reais com conteúdo sintético local.
- Os oito formatos de áudio e os três contêineres de vídeo foram exercitados.
  FFprobe confirmou imagem e áudio nos vídeos de teste.
- Referências HTML/JavaScript, assinatura by ☧ SYSTEMS, integridade dos locks
  e contraste dos principais tokens fazem parte do contrato de distribuição.
- A suíte consolidada de **23 testes passou** em Python 3.12 e novamente em
  Python 3.13.16 com dependências instaladas a partir do lock e hashes:
  21 testes funcionais e dois de distribuição (contrato e ZIP determinístico).
- Os três locks de ferramentas Windows foram obtidos dos repositórios oficiais,
  com tags e SHA256 explícitos; FFmpeg usa um tag de autobuild datado.

## Pendências expressas

- A instalação do Chromium de testes neste ambiente recebeu um arquivo de
  download vazio/inválido. Portanto, a suíte de navegador foi criada, mas **não
  foi executada com sucesso aqui**. Não se afirma validação visual completa,
  ausência de overflow em todas as janelas ou conformidade WCAG integral.
- O inicializador PowerShell da versão 2.0.0 não foi executado no Windows aqui.
  A matriz de CI inclui preparação e testes Windows; o workflow ainda precisa
  rodar no repositório publicado.
- Não há auditoria independente de segurança, varredura antimalware dos
  binários do usuário, assinatura de código ou certificação ISO.
- O download real do YouTube continua dependente de rede, disponibilidade e
  bloqueios do serviço. Nos testes remotos anteriores, foi possível consultar
  metadados; a obtenção de mídia encontrou falha e verificação de usuário.
  Nenhum desses bloqueios foi contornado. Esta versão não reivindica uma nova
  validação remota completa.

## Como concluir a aceitação

Executar a CI Linux/Windows e a suíte de interface; realizar instalação limpa
no Windows e teste de uma gravação autorizada; revisar 320/768/1366/1920 pixels,
leitura a 200%, teclado, leitor de tela, diálogos e reprodução dos arquivos.
Atualizar este registro com links de runs e evidências reais. Não converter
uma pendência em aprovação apenas porque existe um teste preparado.
