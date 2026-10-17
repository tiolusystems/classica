# Clássica

**Áudio e vídeo, no seu computador.**

by **☧ SYSTEMS** · versão **2.1.0**

Aplicação local em português para salvar gravações autorizadas do YouTube.
Cole o link, escolha áudio ou vídeo, selecione o formato e acompanhe a fila.

## Começar no Windows

1. Baixe o pacote da versão publicada e extraia o ZIP.
2. Entre na pasta **Classica** e abra **Iniciar.bat**.
3. Na primeira abertura, aguarde a preparação dos componentes. Reserve cerca
   de **2 GB livres**, além do espaço necessário para seus downloads.
4. A interface abre no navegador do computador. Mantenha a janela de execução
   aberta enquanto usa a aplicação. Para encerrar, use **Sair**.

**Windows 10/11 x64 (Intel/AMD).** Não é um APK. A interface local não é uma
página hospedada no GitHub Pages: o processamento exige Python, yt-dlp e FFmpeg
no computador. Não é necessário fornecer senha, conta ou chave de API.

O ZIP sempre contém uma única pasta `Classica/`. O inicializador recusa execução
diretamente na raiz de uma unidade. Esta versão **não inclui ferramenta de
remoção, recuperação ou organização de arquivos de versões antigas**.

## Recursos

| Opção | Formatos e comportamento |
| --- | --- |
| Somente áudio | MP3, M4A, AAC, WAV, FLAC, OGG/Vorbis, OPUS e Original |
| Vídeo com áudio | MP4, MKV ou WebM, com imagem e som |
| Resolução máxima | Melhor disponível ou até 480p, 720p, 1080p, 1440p e 2160p |
| Acompanhamento | Fila sequencial, progresso, cancelamento, novas tentativas e histórico |
| Leitura | Tipografia responsiva e ajuste manual de 100% a 200%, salvo no navegador |
| Destino | Pasta configurável, botão Abrir pasta e Salvar cópia |

São aceitos até 50 links de vídeos individuais por envio. A aplicação não
expande playlists. A mesma fila pode combinar downloads de áudio e vídeo.
Resoluções diferentes são tratadas como arquivos diferentes.

MP3 é convertido em 320 kbps. Isso não melhora uma fonte de menor qualidade.
Converter para WAV ou FLAC não recupera detalhes perdidos. Original preserva
o áudio recebido. A resolução nunca é ampliada artificialmente. WebM pode
exigir conversão e demorar mais. MP4 é um contêiner; a compatibilidade dos
codecs de origem também depende do reprodutor usado.

## Onde ficam meus arquivos?

O destino inicial é `Music\Classica` no seu perfil. O caminho exato aparece na
interface e pode ser alterado em Preferências. Áudio e vídeo usam a mesma pasta
configurada. Limpar histórico **preserva** os arquivos baixados.

Histórico e configurações ficam em `%LOCALAPPDATA%\Classica`. A versão 2.0
mantém compatibilidade com o histórico da versão anterior. Encerrar interrompe
os itens pendentes; ao reabrir, use Tentar novamente para retomá-los.

## Atualizar

Feche a aplicação e execute `Atualizar.bat` para buscar uma versão mais recente
do extrator. É uma ação explícita: a versão resultante pode diferir da baseline
testada registrada em `requirements.lock`. Os componentes externos do pacote
base usam versões e hashes de `tools.lock.json`.

### YouTube pede login ou retorna HTTP 429

A fila é sequencial, com espaçamento entre requisições e antes de downloads.
Ao receber HTTP 429, pausa toda a fila por 60 segundos e faz **uma única** nova
tentativa automática. Se ocorrer novamente, mantém a fila pausada e aguarda
uma ação explícita. O botão Retomar fila fica disponível após a pausa mínima;
o item com falha pode ser reiniciado em Tentar novamente. A pausa é persistida
ao reiniciar. Sessões autenticadas não são ativadas automaticamente.
Esses 60 segundos são uma política conservadora da aplicação, não um prazo de
desbloqueio informado ou garantido pelo YouTube.

Antes de marcar um item como concluído, FFprobe deve identificar áudio e,
quando solicitado, vídeo no arquivo final. Uma página HTML recebida da rede,
um arquivo vazio ou um vídeo sem som gera erro em vez de sucesso.

Atualizar o extrator **não garante** remover limites de requisições, exigências
de login ou PO Token. Pare as tentativas e confira o vídeo diretamente no Edge.
Se funcionar com sua conta e o download for autorizado, marque **Usar minha
sessão do Edge** e leia a confirmação antes de adicionar o download ou usar
**Tentar novamente**. Aguarde antes de uma nova tentativa; não repita em massa.

A opção inicia desmarcada e não é salva ao reabrir a interface. Ela vale para
os itens adicionados ou reiniciados enquanto estiver marcada; desmarcar não
altera itens já enfileirados (cancele-os, desmarque e tente novamente).
O yt-dlp lê o banco de cookies do perfil padrão do Edge localmente. A Clássica
não exporta um arquivo de cookies, não pede sua senha nem envia cookies ao GitHub.
Cookies aplicáveis são usados nas conexões com o YouTube. O uso da conta pode
resultar em restrições ou suspensão pelo serviço; use somente quando necessário.

Se o banco de cookies estiver ocupado, feche o Edge após confirmar sua sessão e
tente uma vez. Se o Windows impedir a descriptografia (DPAPI), não desative
proteções nem execute como administrador. A opção pode não funcionar em algumas
instalações. Não há garantia de eliminar HTTP 429 ou exigências de PO Token.

Para instalar uma nova versão da Clássica, substitua os arquivos dentro da
**mesma pasta**. Mantenha os componentes locais já instalados. Não mova o
ambiente Python depois de criado; se precisar mudar de lugar, extraia a versão
em outra pasta e deixe o inicializador preparar um ambiente novo.

## Qualidade, marca e limites

A assinatura **by ☧ SYSTEMS** foi confirmada no componente
`apps/web/app/developer-signature.tsx` do Elite System. A paleta desta aplicação
é funcional e independente da marca comercial Elite Agrociências.

Há requisitos rastreáveis, testes, versionamento e critérios de aceitação
inspirados em referências de qualidade e interação. **Não há certificação ISO,
declaração de conformidade integral ou certificação WCAG.** Veja
[Qualidade](docs/QUALITY.md), [Rastreabilidade](docs/TRACEABILITY.md),
[Verificação](docs/VALIDATION.md) e [Identidade](docs/BRAND.md).

O código é inspecionável; isso não equivale a uma garantia de ausência de
malware. A distribuição não é um instalador EXE assinado. Não desative a
proteção do computador para executar arquivos. Consulte [Segurança](SECURITY.md).

O YouTube pode mudar, exigir verificação ou recusar um download. A aplicação
não contorna autenticação, DRM ou pagamento. Uma composição em domínio público
pode ter uma gravação ainda protegida. Use conteúdo próprio, em domínio público
ou com autorização aplicável. Não existe análise automática de licença.

## Desenvolver e verificar

Python 3.11+ é aceito pelo código; a baseline de distribuição usa Python 3.13.
Instale FFmpeg/FFprobe e Deno no PATH para a funcionalidade completa.

```sh
python -m venv .venv
# Ative o ambiente conforme seu sistema.
python -m pip install --require-hashes -r requirements.lock
python app.py
python -m unittest discover -s tests -v
node --check web/app.js
python scripts/verify_release.py
python scripts/package_release.py
```

Os testes de conversão usam conteúdo sintético local, sem baixar vídeos de
terceiros. A suíte de interface usa dados de teste e um servidor local isolado:

```sh
npm ci
npx playwright install chromium
npm run test:ui
```

GitHub Actions inclui testes Linux, preparação e testes Windows, testes de
interface e construção do ZIP. Um tag `v2.1.0` aciona a publicação de uma versão
com ZIP e SHA256 **apenas se os testes anteriores passarem**. Não confunda a
existência do workflow com um resultado de CI já aprovado.

## Componentes e licenças

O código original usa a [licença MIT](LICENSE.txt). A marca ☧ SYSTEMS não é
licenciada para sugerir autoria ou endosso de terceiros; veja [Marca](docs/BRAND.md).
Os componentes de terceiros são baixados na preparação e conservam suas
licenças: [yt-dlp](https://github.com/yt-dlp/yt-dlp),
[FFmpeg](https://github.com/yt-dlp/FFmpeg-Builds),
[Deno](https://github.com/denoland/deno), [uv](https://github.com/astral-sh/uv)
e [Python](https://www.python.org/). Veja [Avisos de terceiros](THIRD_PARTY.md).
