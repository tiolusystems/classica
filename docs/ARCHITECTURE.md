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
