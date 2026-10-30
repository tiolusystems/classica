# Componentes de terceiros

| Componente | Finalidade | Origem |
| --- | --- | --- |
| yt-dlp e yt-dlp-ejs | Extração e downloads | https://github.com/yt-dlp/yt-dlp |
| FFmpeg e FFprobe | Conversão, remux e inspeção | https://github.com/GyanD/codexffmpeg |
| Deno | Runtime JavaScript do extrator | https://github.com/denoland/deno |
| uv | Preparação de Python e pacotes | https://github.com/astral-sh/uv |
| CPython | Execução da aplicação | https://www.python.org/ |
| Playwright | Testes de interface; não é dependência do usuário | https://github.com/microsoft/playwright |

Os pacotes externos não são incorporados ao ZIP da aplicação. A preparação
baixa os componentes; documentos de licença incluídos no pacote FFmpeg são
preservados. O código original da aplicação usa MIT, sem substituir as licenças
dos fornecedores. A compilação FFmpeg selecionada é GPL; uv é MIT/Apache-2.0;
Deno é MIT; Python segue suas licenças PSF e associadas; as distribuições Python
do yt-dlp seguem Unlicense e as dependências têm seus próprios termos.

As versões exatas, arquivos e hashes estão nos dois arquivos de lock. Para
redistribuir binários externos, avalie separadamente as obrigações de cada
pacote, inclusive disponibilização do código-fonte correspondente quando
exigida. A distribuição atual fornece somente o código original e os scripts
de preparação.
