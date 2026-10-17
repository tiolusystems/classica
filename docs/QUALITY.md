# Qualidade e critérios de aceitação

Este projeto traduz objetivos de qualidade em critérios verificáveis. As
referências abaixo orientam o trabalho; **não houve avaliação integral dos
textos normativos, auditoria de certificação ou declaração de conformidade**.
Não existe selo “ISO” aplicado ao produto.

## Referências

- [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html): referência de
  modelo de qualidade de produto para especificação e avaliação.
- [ISO 9241-110:2020](https://www.iso.org/standard/75258.html): referência de
  princípios de interação, não um padrão de aparência ou logomarca.
- [WCAG 2.2 — Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)
  e [Resize Text](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html):
  referências para leitura, adaptação e ampliação. A aplicação não declara
  conformidade WCAG AA integral.

## Critérios do produto

1. O usuário consegue configurar áudio ou vídeo em uma única tela.
2. Toda conclusão aponta para um arquivo existente; uma falha não vira sucesso.
3. Vídeo inclui imagem e áudio; a resolução respeita o limite sem upscaling.
4. Cancelar interrompe o processo; limpar histórico preserva os arquivos.
5. Os dados da fila sobrevivem a reinícios; retomada é explícita.
6. Estados possuem texto e ação; a comunicação não depende só de cores.
7. Interface usa HTML semântico, labels, foco visível e diálogos rotulados.
8. Layout prevê 320, 768, 1366 e 1920 pixels sem rolagem horizontal do documento.
9. Preferência de fonte funciona até 200%; o zoom do navegador permanece livre.
10. Dependências iniciais são registradas por versão e hash; atualizações
    voluntárias são distinguidas da baseline de distribuição.
11. O ZIP contém apenas arquivos previstos, dentro de uma única pasta Classica.
12. Histórico, mídia, ambientes, logs e ferramentas antigas não são publicados.

## Processo de versão

Usar versões semânticas, manter CHANGELOG, executar testes e empacotar pela
lista explícita. Um tag de versão aciona CI e release. Falha em testes impede
o job de publicação. O arquivo SHA256 permite comparar a integridade do ZIP;
não é assinatura de autoria e não prova ausência de malware.

Uma versão deve ser descrita como “verificada” apenas nos ambientes que
realmente foram executados. Resultados pendentes continuam pendentes na
documentação de verificação. Testes de usabilidade com pessoas, leitores de
tela e reprodução real em Windows continuam sendo avaliações distintas.

## Aceitação da versão candidata 2.1.1

- O aviso de uso responsável deve ser legível, acessível por teclado e não simular exoneração jurídica absoluta.
- Limpar concluídos deve preservar gravações no disco, erros, cancelamentos e downloads pendentes, inclusive após reiniciar o aplicativo.
- A opção de limpar todo o histórico continua removendo apenas registros de tarefas encerradas.
- Layout com Chi-Rho preservado, sem conteúdo transbordando em 320/768/1366/1920 px nem com zoom tipográfico de 200%.
- Os modos de áudio/vídeo, token local, cancelamento e nova tentativa continuam inalterados.
- Executar CI Linux/Windows/UI, validação do ZIP e instalação Windows limpa antes de mesclar ou publicar.

## Aceitação da inicialização discreta opcional

- `Iniciar.bat` mantém o comportamento clássico sem modificações; o modo discreto é um arquivo alternativo.
- A janela de preparação aparece somente durante a inicialização; depois ela se fecha e o processo continua com o console oculto.
- O processo não se torna um serviço do Windows, não inicia com o sistema e permanece acessível exclusivamente em `127.0.0.1`.
- O botão `Sair` deve encerrar o processo em segundo plano. Fechar só a aba não interrompe a fila, como no modo clássico.
- Erros devem ser registrados para diagnóstico; o `Iniciar.bat` original segue disponível.
- O runner Windows deve validar a abertura real do servidor em segundo plano e seu encerramento via API.
