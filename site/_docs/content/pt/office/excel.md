---
title: Pastas de trabalho do Excel
description: Faça o Coscribe ler, limpar, totalizar e conciliar planilhas, e criar pastas de trabalho com fórmulas e gráficos.
---

O Coscribe lê arquivos `.xlsx` planilha por planilha e escreve pastas de trabalho reais: células, estilos, fórmulas e gráficos nativos do Excel.

## O que pedir {#what-to-ask-for}

- **Limpar e totalizar**: "Remova as linhas sem endereço de entrega e some os valores por fornecedor."
- **Conciliar**: "Compare o extrato do banco com o nosso razão e liste o que não bate."
- **Montar um modelo**: "Faça um orçamento de 12 meses com uma planilha de resumo que some os departamentos."
- **Fazer um gráfico**: "Adicione um gráfico de colunas da receita por região ao lado da tabela."

Cite os arquivos e as planilhas, se uma pasta de trabalho tiver várias, e diga qual deve ser o resultado: um arquivo novo, uma planilha nova ou uma alteração na existente.

## Fórmulas continuam fórmulas {#formulas-stay-formulas}

Quando um valor depende de outras células, o Coscribe o escreve como uma fórmula do Excel, para que a pasta de trabalho continue funcionando quando você mudar um número. Ele também calcula as fórmulas e salva os resultados no arquivo, para que os valores apareçam mesmo em programas que não recalculam ao abrir.

## Trabalhos grandes ou incomuns {#large-or-unusual-jobs}

Para trabalhos que as ferramentas integradas não cobrem, o Coscribe pode escrever um script Python (com `pandas` e `openpyxl`, por exemplo) e executá-lo, com a sua aprovação. Veja [Aprovações e modos de permissão](../use/approvals.md).

> [!TIP]
> Quer que o Coscribe siga as convenções da sua equipe, como cores para entradas e saídas ou um formato de número? Coloque-as nas suas [instruções](../customize/instructions.md) ou em uma [habilidade](../customize/skills.md).
