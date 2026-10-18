# Clássica

**Áudio e vídeo, no seu computador.**

by **☧ SYSTEMS** · versão **2.1.2**

Aplicação local em português para salvar gravações autorizadas do YouTube.
Cole o link, escolha áudio ou vídeo, selecione o formato e acompanhe a fila.

## Começar no Windows

1. Baixe o pacote da versão publicada e extraia o ZIP.
2. Entre na pasta **Classica-2.1.2** e abra **Clássica.exe**, identificado pelo ícone ☧.
3. Na primeira abertura, aguarde a preparação dos componentes. Reserve cerca
   de **2 GB livres**, além do espaço necessário para seus downloads.
4. A interface abre no navegador do computador e a janela de preparação fecha. Para encerrar a aplicação, use **Sair**.

### Um único ponto de entrada

O ZIP já inclui **Clássica.exe**, com nome e ícone próprios. Não é necessário criar
atalhos, escolher um navegador ou instalar um lançador separado. Extraia a pasta
inteira: o executável depende dos arquivos que o acompanham. Ele funciona a partir
da própria pasta, mesmo se for aberto de outro diretório.

A pasta principal mostra apenas **Clássica.exe**, **Leia-me.txt** e **Componentes**.
Os scripts e arquivos técnicos ficam dentro de Componentes; a abertura normal
é sempre pelo ícone Clássica. Mantenha essa pasta junto do executável.

Uma janela clara mostra a preparação e eventuais erros. Depois da abertura da
interface, essa janela fecha; use **Sair** na aplicação para encerrar o servidor.
Não exige administrador, não cria atalhos nem adiciona inicialização com o Windows.
O lançador confere se o programa e a interface têm a mesma versão do executável;
se encontrar arquivos de versões diferentes, informa como extrair o pacote correto.

O executável é compilado do código `launcher/Classica.cs` pelo GitHub Actions,
com o compilador .NET Framework do Windows. O ícone não é uma assinatura digital:
esta distribuição ainda não tem certificado de assinatura de código e o Windows
pode exibir um aviso de reputação.

### Alternativas de suporte

Além do **Iniciar.bat**, há **Iniciar discreto.bat**. No modo discreto, a janela preta aparece apenas durante a preparação inicial e se fecha automaticamente depois que o navegador abre. A Clássica continua executando em segundo plano, sem depender de um console aberto. Para encerrar de fato, clique em **Sair** dentro da interface; apenas fechar a aba não interrompe o servidor nem a fila.

Essas alternativas e `Atualizar.bat` ficam dentro de **Componentes** no ZIP.
O início normal é sempre por **Clássica.exe**, na pasta principal.

O modo clássico **Iniciar.bat** permanece como alternativa recomendada para diagnóstico. Se o início discreto falhar, consulte `ultimo-inicio.log` e `ultimo-discreto-erros.log` na pasta da Clássica e volte a usar o modo clássico. Não há serviço permanente instalado nem inicialização automática junto com o Windows.

**Windows 10/11 x64 (Intel/AMD).** Não é um APK. A interface local não é uma
página hospedada no GitHub Pages: o processamento exige Python, yt-dlp e FFmpeg
no computador. Não é necessário fornecer senha, conta ou chave de API.

O ZIP contém uma única pasta `Classica-2.1.2/`, identificada pela versão.
Extraia como uma pasta nova; não mescle arquivos com outra versão. O histórico e
as preferências continuam no perfil do usuário. Se fechar apenas a aba, abrir
Clássica de novo recupera a mesma sessão. Use **Sair** para encerrar de fato.
Se outra versão estiver ativa, encerre-a antes de abrir a nova.
O inicializador recusa execução
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
configurada. O comando **Limpar biblioteca** exige confirmação e **preserva** os arquivos baixados.

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
de login ou PO Token. Pare as tentativas e confira o vídeo diretamente no navegador.
A interface de download não solicita cookies nem depende de um navegador específico.
Quando uma gravação não estiver disponível, interrompa as tentativas e consulte o vídeo no navegador. Não existe garantia de acesso a todos os conteúdos do YouTube.

Para instalar uma nova versão, encerre a aplicação pelo botão **Sair** e extraia
o novo ZIP em sua própria pasta, identificada pela versão. Não copie arquivos
sobre a pasta antiga nem mova o ambiente Python já preparado. A nova pasta
prepara seus componentes; histórico e preferências continuam no perfil do usuário.

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
## No Windows, antes de empacotar:
powershell -NoProfile -File scripts/build_launcher.ps1
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
interface e construção do ZIP. Uma tag `v2.1.2` aciona a publicação de uma versão
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
