# Rastreabilidade de requisitos

| ID | Requisito | Implementação | Evidência / limite |
| --- | --- | --- | --- |
| F01 | Links individuais e lote limitado | canonical_url, Manager.enqueue | testes de links e lote |
| F02 | Oito formatos de áudio | command_for | conversão sintética real nos oito formatos |
| F03 | MP4, MKV e WebM com som | command_for | FFprobe confirma imagem e áudio nos três formatos |
| F04 | Resolução máxima sem ampliação | video_selector | seleção de formatos até o limite |
| F05 | Progresso, cancelamento e falha | Manager | testes de processo e arquivo final |
| F06 | Histórico persistente | save/load | teste de reinício e retomada explícita |
| F07 | Limpar histórico preserva mídia | clear | teste de preservação de arquivo |
| U01 | Leitura responsiva | CSS clamp, grid e media queries | suíte de interface da prévia aprovada na CI; esta revisão exige repetição da CI |
| U02 | Tamanho ajustável até 200% | setReading, Preferências | controle e persistência; suíte de navegador preparada |
| U03 | Estados textuais, teclado e ajuda | HTML semântico e diálogos | revisão estrutural; avaliação humana/leitor de tela pendente |
| U04 | Contraste dos tokens principais | variáveis CSS | cálculo de cinco pares >= 4,5:1; não cobre todas as combinações ou WCAG integral |
| B01 | Assinatura canônica | HTML e favicon | referência do Elite System e contrato de marca |
| S01 | API somente local | Handler, create_server | testes de Host, Origin e token |
| S02 | Limite de acesso a arquivos | do_GET /file | teste de caminho externo rejeitado |
| S03 | Dependências iniciais registradas | locks e iniciar.ps1 | hashes de distribuição; auditoria antimalware pendente |
| D01 | Uma pasta superior no ZIP | package_release | teste de conteúdo e integridade |
| D02 | Sem ferramenta antiga de organização | allowlist de distribuição | teste de contrato e empacotamento |
| M01 | Código versionado e CI | Git e workflow | configuração preparada; status real informado separadamente |

As referências ISO ajudam a organizar objetivos e avaliação. Nenhuma linha
desta matriz representa conformidade integral com uma cláusula normativa.
