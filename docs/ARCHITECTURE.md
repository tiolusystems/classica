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

## Desktop e manutenção (2.2.1)

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
