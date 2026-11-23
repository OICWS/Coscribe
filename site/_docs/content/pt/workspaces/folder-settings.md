---
title: Notas e regras próprias de uma pasta
description: Deixe uma pasta dizer ao coscribe o que ela contém, quais habilidades e conectores usar e o que pode rodar sem perguntar.
---

Uma pasta pode levar instruções para o coscribe em uma pasta `.coscribe` dentro dela. O coscribe as lê em qualquer conversa que use a pasta, depois que você as aceitar.

## O que uma pasta pode conter {#what-a-folder-can-hold}

| Arquivo | O que faz |
|---|---|
| `.coscribe/memory.md` | Notas que o coscribe lê no início de cada conversa nesta pasta: para que a pasta serve, convenções, nomes. |
| `.coscribe/skills/<name>/SKILL.md` | [Habilidades](../customize/skills.md) que valem apenas nesta pasta. |
| `.coscribe/settings.json` | Regras de permissão (`allow`, `ask`, `deny`) e variáveis de ambiente para scripts. |
| `.coscribe/mcp.json` | [Conectores](../customize/connectors.md) que esta pasta usa. |

O próprio coscribe nunca grava `memory.md`, `settings.json` nem `mcp.json`; só você os edita. Os anexos que você envia ficam em `.coscribe/uploads/`.

## Aceitar as configurações de uma pasta {#accept-a-folders-settings}

As configurações de uma pasta podem vir de qualquer pessoa que consiga gravar nela, então o coscribe não as segue até você concordar. O painel **Task details** mostra **What Coscribe knows about this folder**, listando as habilidades, os conectores e as regras que a pasta traz, agrupados em **Runs without asking**, **Always asks** e **Never runs**, além de eventuais variáveis para scripts. Clique em **Use them** para aceitar.

Se algum desses arquivos mudar fora do coscribe, ele pergunta de novo.

## Regras de permissão {#permission-rules}

`.coscribe/settings.json` usa o mesmo formato do arquivo de configurações do Claude Code:

```json
{
  "permissions": {
    "allow": ["write_file(reports/*)"],
    "ask": ["run_background_command"],
    "deny": ["delete_file"]
  },
  "env": {
    "REPORT_REGION": "East"
  }
}
```

Uma regra é o nome de uma ferramenta do coscribe, um padrão de nomes com `*`, ou qualquer um dos dois com um padrão do argumento principal entre parênteses, como `write_file(docs/*)`. As regras decidem apenas ações que, de outra forma, esperariam sua aprovação. **deny** prevalece sobre **ask**, e **ask** sobre **allow**.

Alguns limites sempre valem:

- Uma regra nunca permite uma ação que sai do seu computador, como enviar uma mensagem por um conector; essas continuam perguntando.
- Um `*` sozinho não permite nada.
- Uma regra `ask` pergunta mesmo no modo **Auto**.

## Variáveis para scripts {#variables-for-scripts}

Os valores de `env` em `settings.json` são passados aos scripts e comandos na pasta. Uma pasta não pode definir variáveis que mudem quais programas rodam ou para onde vai o tráfego, como `PATH`, configurações de proxy ou `PYTHONPATH`.
