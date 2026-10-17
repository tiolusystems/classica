# Registro de verificação — 2.0.0

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
