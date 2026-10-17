# Registro de verificação

## 2.1.0 — 17/10/2026 (candidata, ainda não publicada)

### Evidências confirmadas em ordem cronológica

- Prévia 2.1.0: CI [39049563209](https://github.com/tiolusystems/classica/actions/runs/39049563209), Linux, Windows e navegador aprovados **na revisão que ainda oferecia a opção experimental do Edge**.
- Teste funcional de uso: o usuário confirmou no seu Windows downloads de MP3, áudio Original e vídeo, inclusive repetição do MP3 e reprodução completa. Esses testes ocorreram antes da remoção integral do Edge.
- Revisão da interface, sem caixa de cookies: CI [39063052434](https://github.com/tiolusystems/classica/actions/runs/39063052434), Linux, Windows e Playwright aprovados.
- Revisão de segurança que removeu o mecanismo de leitura de cookies da API e do extrator: CI [39064398541](https://github.com/tiolusystems/classica/actions/runs/39064398541), Linux, Windows e Playwright aprovados.
- Nova validação do ZIP após as alterações de segurança: CI [39066425692](https://github.com/tiolusystems/classica/actions/runs/39066425692), Linux, Windows, Playwright e instalação limpa no Windows **aprovados**.
- O teste de instalação limpa extraiu o pacote de distribuição em pasta temporária, preparou as dependências, iniciou o servidor local, verificou a API e o bloqueio de cookies e executou **33 testes dentro do ZIP extraído**, incluindo conversões de mídia sintética.

### Limitações expressas

- Os testes de mídia da CI usam arquivos sintéticos locais, não são prova de disponibilidade de qualquer vídeo do YouTube. Downloads reais da revisão após a remoção do Edge não foram comprovados neste ambiente.
- Não se realizou auditoria de segurança independente, assinatura de código Windows, certificação ISO/WCAG nem varredura antimalware de toda instalação final.
- Testar a instalação num runner Windows não garante compatibilidade em todas as versões, redes e computadores Windows 10/11.
- A integração na `main` e a publicação de tag/ZIP oficial da versão 2.1.0 exigem validação do commit consolidado e etapas distintas. CI de uma PR não é a CI do release publicado.

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
