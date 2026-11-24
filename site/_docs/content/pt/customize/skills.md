---
title: Habilidades e plugins
description: Ensine ao Coscribe um jeito de trabalhar uma vez, adicione habilidades que outras pessoas criaram e ative ou desative cada uma.
---

Uma habilidade (skill) é um conjunto de instruções para um tipo de trabalho, como o jeito que sua equipe escreve um relatório semanal. Quando um trabalho corresponde à descrição de uma habilidade, o Coscribe a segue. O Coscribe vem com algumas habilidades integradas, e você pode adicionar as suas.

## Usar uma habilidade {#use-a-skill}

Você não precisa fazer nada: o Coscribe escolhe uma habilidade quando ela se encaixa. Para usar uma de propósito, digite <kbd>/</kbd> na caixa de mensagem e escolha-a na lista, ou digite o nome dela depois da barra, seguido do seu pedido.

## Salvar um trabalho como habilidade {#save-a-job-as-a-skill}

Depois de fazer um trabalho em uma conversa, você pode guardar como ele foi feito:

- Digite `/create-skill` seguido de um nome.
- Ou escolha **Save as skill** quando o Coscribe oferecer **Save this job?** depois de um trabalho de vários passos.

Você também pode começar em **Settings** › **Skills** › **Add** › **Create with Coscribe**, que abre uma conversa para você descrever a habilidade.

## Adicionar habilidades que outras pessoas criaram {#add-skills-others-made}

Em **Settings** › **Skills**:

- **Discover** lista habilidades de código aberto de [github.com/anthropics/skills](https://github.com/anthropics/skills) e [github.com/anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins). A maioria vem como plugin: um pacote de habilidades. Abra um para ver suas habilidades, os conectores que usa e a licença; **Add** baixa todas as habilidades dele.
- **Add** › **Upload a skill** recebe um arquivo de habilidade que você ganhou: um `SKILL.md` ou um arquivo `.zip`, `.skill` ou `.plugin`.

> [!WARNING]
> Uma habilidade é um conjunto de instruções que o Coscribe segue. Adicione habilidades apenas de pessoas em quem você confia e leia uma antes de usá-la: abra-a em **Yours** para ver seus arquivos.

## Ativar ou desativar habilidades {#turn-skills-on-or-off}

**Yours** lista suas habilidades. Abra uma para ler seus arquivos e use a chave dela para desativá-la sem excluí-la. O menu ao lado de uma habilidade a remove. Remover uma habilidade que veio em um plugin remove todas as habilidades daquele plugin.

## Habilidades para uma pasta {#skills-for-one-folder}

Uma pasta pode trazer suas próprias habilidades em `.coscribe/skills/`. Elas valem apenas nas conversas que usam aquela pasta, depois que você aceitar as configurações dela. Veja [Notas e regras próprias de uma pasta](../workspaces/folder-settings.md).

## Escrever uma habilidade à mão {#write-a-skill-by-hand}

Uma habilidade é uma pasta com um arquivo `SKILL.md`. O arquivo começa com um `name` e uma `description`, e depois vêm as instruções em Markdown:

```markdown
---
name: Weekly report
description: Write the weekly sales report from the order export. Use when asked for the weekly report.
---

1. Read the latest export in Reports/Exports.
2. ...
```

A descrição decide quando o Coscribe usa a habilidade, então diga para que ela serve e quando usá-la. É o mesmo formato das habilidades do Claude Code.
