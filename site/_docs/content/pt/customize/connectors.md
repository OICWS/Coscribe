---
title: Conectores
description: Conecte o coscribe aos serviços que você usa, como e-mail, agenda ou gerenciador de projetos, e escolha o que ele pode fazer neles.
---

Um conector permite que o coscribe use outro serviço: ler seus e-mails, adicionar um evento a uma agenda, consultar um chamado. Os conectores usam o Model Context Protocol (MCP), então qualquer servidor MCP funciona, não apenas os que o coscribe lista.

## Adicionar um conector {#add-a-connector}

Abra **Settings** › **Connectors** › **Discover**, escolha o serviço e clique em **Connect**.

- A maioria dos serviços hospedados pede que você entre na sua conta. O login abre na própria página do serviço, no seu navegador, e você entra só uma vez. O coscribe nunca vê sua senha.
- Um serviço marcado como **Needs setup** exige antes um app registrado nele. O coscribe guia você nisso, uma única vez. Se alguém já configurou isso para sua equipe, **Copy a message for your admin** pede a essa pessoa o arquivo de configuração.

O coscribe também pode oferecer um conector em uma conversa, quando seu pedido precisa de um serviço que você não conectou. Clique em **Connect** no cartão, e o coscribe continua assim que ele estiver conectado. **Not now** deixa para depois; você pode conectá-lo a qualquer momento em **Settings** › **Connectors**.

## Adicionar um conector personalizado {#add-a-custom-connector}

Para um servidor MCP que não está na lista, escolha **Add** › **Add custom connector**, dê um nome e então:

- Informe a **MCP server URL** de um servidor hospedado, com os cabeçalhos de que ele precisar. Para colocar uma chave em um cabeçalho sem escrevê-la, use **Insert a secret**; o cabeçalho fica `{{secret:NAME}}` e o valor vem de [Secrets](../reference/settings.md#secrets).
- Ou escolha **Run a local command instead** e informe o comando, como `npx`, seus argumentos e as variáveis de ambiente necessárias. Ele roda como um programa neste computador, com as suas permissões.

> [!WARNING]
> Um comando local roda com tudo o que sua conta do Windows pode fazer. Adicione apenas servidores em que você confia.

## Escolher o que ele pode fazer {#choose-what-it-may-do}

Abra um conector em **Yours** para ver suas ferramentas, divididas em **Read-only tools** e **Write/delete tools**. Para cada ferramenta, escolha:

| Escolha | O que acontece |
|---|---|
| **Always allow** | O coscribe a usa sem perguntar. |
| **Needs approval** | O coscribe pergunta a você a cada vez. Veja [Aprovações e modos de permissão](../use/approvals.md). |
| **Blocked** | O coscribe não pode usá-la. |

A página do conector também diz se ele está conectado. Se não estiver, **Retry** conecta de novo, e **Sign in** abre a página de login do serviço.

## Conectores para uma pasta {#connectors-for-one-folder}

Uma pasta pode trazer seus próprios conectores em `.coscribe/mcp.json`. Eles valem apenas nas conversas que usam aquela pasta, depois que você aceitar as configurações dela. Veja [Notas e regras próprias de uma pasta](../workspaces/folder-settings.md).

## Usar um conector em um fluxo de trabalho {#use-a-connector-in-a-workflow}

As ferramentas de um conector podem ser passos de um [fluxo de trabalho](../workflows/workflows.md), e um fluxo de trabalho pode começar quando algo novo aparece em um conector. Veja [Iniciar um fluxo de trabalho com um evento](../workflows/workflows.md#start-on-an-event).
