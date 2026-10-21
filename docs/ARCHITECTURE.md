# Arquitetura

Aplicação local, sem serviço remoto próprio. `app.py` contém um servidor HTTP
na interface de loopback, uma fila sequencial e um gerenciador de processos.
`web/` contém HTML, CSS e JavaScript sem framework e sem build obrigatório.

O navegador envia um pedido à API local. O gerenciador valida links e opções,
persiste o trabalho e invoca yt-dlp por argumentos estruturados. yt-dlp baixa
o conteúdo; FFmpeg realiza o processamento necessário. A confirmação final
depende da existência do arquivo retornado pelo extrator. O navegador consulta
o estado e oferece acesso ao arquivo concluído.

Um lock de processo protege o histórico contra duas instâncias simultâneas.
O histórico é escrito por substituição atômica. Um encerramento interrompe os
trabalhos pendentes para que o usuário escolha retomá-los na próxima sessão.
As filas das versões 1.x continuam legíveis.

Os componentes locais ficam fora do controle de versão. `scripts/` possui
verificação e empacotamento, e `.github/workflows/` possui CI e release. Os
testes de interface criam um gerenciador sem worker em diretório temporário;
portanto, não conectam ao YouTube. Os testes de conversão exercitam yt-dlp e
FFmpeg reais com conteúdo sintético.

Limites: o servidor não foi projetado para exposição pública, clientes remotos,
multiusuário, banco de dados remoto ou execução como serviço do Windows.

## Desktop e manutenção (2.2.2)

O controlador C# mantém o NotifyIcon enquanto o servidor Python está ativo. Um
mutex por pasta/perfil evita controladores duplicados; eventos locais sinalizam
Abrir/Encerrar. A sessão é confirmada no loopback com token privado antes de
qualquer comando. A interface pode funcionar no navegador padrão.

`maintenance.py` busca versões estáveis apenas em tiolusystems/classica, verifica
tamanho e SHA256 do asset oficial, rejeita caminhos especiais, colisões Windows,
links e conteúdo excessivo no ZIP. Copia somente a lista de distribuição na
instalação inicial. Nenhuma versão existente é sobrescrita.

O controlador executa `scripts/update_app.ps1` com apenas um ID aleatório. O helper
confere sessão, destino e manifesto de hashes, prepara dependências, encerra a
sessão antiga, abre a nova e confirma a resposta autenticada antes de registrar
`instalacao.json` e os atalhos estáveis. Se falhar após a troca, tenta reabrir a
versão de origem. Histórico/configuração permanecem em `%LOCALAPPDATA%\Classica`.
Operações de manutenção exigem fila sem itens pendentes e consulta de detalhes
encerrada. Não há serviço, autostart, removedor ou envio automático de diagnóstico.

## Plataforma modular (2.4.0)

O Clássica YouTube continua usando exclusivamente seu motor, fila e dados locais. O arquivo `module_manager.py` opera de forma separada: consulta os Releases oficiais de `tiolusystems/classica-x` e `tiolusystems/classica-hub`, verifica o digest SHA-256 informado pela API do GitHub e extrai pacotes exclusivamente em diretórios próprios de cada módulo no perfil Windows. Não incorpora binários externos ao ZIP do YouTube nem altera o contrato de atualização e rollback da aplicação original. A instalação é iniciada explicitamente no diálogo Plataformas; a interface não exige login no GitHub nem privilégios administrativos. Cada módulo mantém seu próprio processo e atualização, inclusive rollback individual.


## Navegação única (2.4.0)

A interface principal do Clássica passa a ser um shell de abas YouTube/X, sem
janelas Tkinter ou navegadores adicionais durante a alternância. O X é um
executável/processo independente >=1.1.1, iniciado em modo incorporado por
arquivo de sessão descartável dentro do perfil Windows. O servidor principal
verifica o token contra a API loopback do X antes de expor uma URL local ao
cliente autenticado. A interface X é renderizada em iframe sandboxed apenas de
origem loopback; os dados, extrator, estado, downloads e atualizações X ficam
completamente fora do motor YouTube. O processo filho X é encerrado juntamente
com o shell que o iniciou. Não há migração de históricos.
