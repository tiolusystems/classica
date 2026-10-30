<img src="assets/classica.png" width="64" height="64" alt="Símbolo da Clássica">

# Clássica

**Sua música e seus vídeos, no seu computador.**

by **☧ SYSTEMS** · versão **2.4.1**

Cole o link de uma gravação autorizada do YouTube, escolha áudio ou vídeo
e acompanhe o download em uma interface em português.

## Baixar

[![Baixar Clássica para Windows](assets/download-windows.svg)](https://github.com/tiolusystems/classica/releases/download/v2.4.1/Classica-2.4.1-Windows-x64.zip)

**Windows 10 e 11 · 64 bits · Intel/AMD**

O botão baixa o pacote pronto, **Classica-2.4.1-Windows-x64.zip**, com o
executável **Clássica.exe**. Não é necessário conhecer programação.

## Começar em três passos

1. **Baixe** pelo botão acima. Se já houver uma versão aberta, encerre-a pelo botão **Sair**.
2. **Extraia** o ZIP: clique com o botão direito no arquivo e escolha **Extrair Tudo**. Mantenha a pasta completa.
3. **Abra Clássica.exe**, dentro de **Classica-2.4.1**. Na primeira abertura, aguarde a preparação dos componentes.

A primeira preparação usa internet e requer cerca de **2 GB livres**, além
do espaço para suas músicas e vídeos. Depois, a interface abre no navegador.

Para instalar a Clássica no seu perfil e criar um ícone na Área de Trabalho e no menu Iniciar, abra
**Ajuda → Instalar e criar atalhos**. A ação é opcional e não exige administrador.
Depois da instalação, a mesma ação fica disponível como **Criar ou atualizar atalhos** caso seja necessário refazê-los.

<details>
<summary>Baixou um ZIP com outra organização de pastas?</summary>

O botão **Code → Download ZIP** e os arquivos **Source code** do GitHub são
voltados ao código-fonte. Para usar a aplicação com o executável e os recursos
de inicialização, volte ao botão **Baixar Clássica para Windows** acima.

O pacote pronto mostra apenas **Clássica.exe**, **Leia-me.txt** e **Componentes**
na pasta principal. Mantenha esses três itens juntos; os arquivos de suporte
ficam em Componentes.

</details>

## Navegação por abas

A partir da versão 2.4.0, a própria Clássica exibe as abas **YouTube** e **X**. Ao selecionar **X**, o módulo é preparado automaticamente se estiver ausente ou incompatível, sem abrir Hub, outros aplicativos ou outro navegador. Nas próximas aberturas, a instalação já preparada é reutilizada, sem novos cliques nem downloads. Se a preparação falhar, aparece uma ação para tentar novamente. O módulo X (mínimo 1.1.1) executa em processo separado, com API local autenticada, dados e histórico próprios. O Clássica YouTube continua independente. O módulo só é preparado quando a aba X é acessada; o uso do YouTube não instala o X. O Clássica X destina-se a publicações públicas autorizadas e requer Windows x64; versões oficiais são verificadas por SHA-256 antes da instalação.

## No dia a dia

- **Áudio ou vídeo:** MP3 e outros sete formatos de áudio; MP4, MKV ou WebM com imagem e som. Para vídeos, selecione resolução máxima de 144p, 240p, 360p, 480p, 720p e superiores. Resoluções menores geralmente diminuem o arquivo, mas o tamanho final depende da duração, bitrate e formatos disponíveis na fonte.
- **Seus arquivos:** use **Abrir pasta** para encontrá-los. Em **Preferências**, escolha o destino e ajuste a leitura de 100% a 200%.
- **Prévia do link:** consulte título, duração e qualidades antes de baixar um vídeo.
- **Fechar e reabrir:** fechar a aba mantém a aplicação no ícone ☧ perto do relógio. Nesse ícone, use **Abrir Clássica** ou **Encerrar Clássica**. O botão **Sair** também encerra.

## Atualizações e ajuda

Na **Ajuda**, use **Verificar atualizações**. Quando houver uma nova versão,
a aplicação oferece a atualização guiada e preserva histórico, preferências
e arquivos baixados. Após atualizar, há a opção de voltar à versão anterior.

Se algo falhar, a Ajuda oferece **Copiar relatório de diagnóstico**, com
versões e categorias de falha, sem incluir seus links, títulos ou pastas.
O relatório só é compartilhado se você o enviar.

O YouTube pode limitar requisições ou restringir gravações. A aplicação informa
a pausa e as orientações disponíveis; não há garantia de acesso a todos os vídeos.

## Transparência

O executável é compilado pelo GitHub Actions a partir deste projeto e ainda
**não tem assinatura digital**. O pacote publicado inclui um arquivo SHA256
para conferência de integridade. Consulte [Versões e arquivos de verificação](https://github.com/tiolusystems/classica/releases).

Baixe somente conteúdos para os quais tenha autorização ou fundamento legal.
Uma composição antiga pode ter gravações protegidas separadamente.

## Projeto e documentação

[Novidades](CHANGELOG.md) · [Segurança](SECURITY.md) · [Licença](LICENSE.txt)

<details>
<summary>Documentação técnica e desenvolvimento</summary>

- [Manual técnico e desenvolvimento](docs/DEVELOPMENT.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Qualidade e critérios de aceitação](docs/QUALITY.md)
- [Rastreabilidade](docs/TRACEABILITY.md)
- [Registro de verificação](docs/VALIDATION.md)
- [Identidade ☧ SYSTEMS](docs/BRAND.md)
- [Componentes e licenças de terceiros](THIRD_PARTY.md)
- [Testes automatizados](https://github.com/tiolusystems/classica/actions/workflows/quality.yml)

O código original usa a licença MIT. Os componentes externos mantêm suas próprias
licenças. As referências de qualidade orientam o projeto; não há certificação ISO
ou declaração de conformidade WCAG integral.

</details>
