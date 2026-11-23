---
title: Espaços de trabalho e pastas
description: Decida quais pastas, sites, segredos e scripts cada conversa pode alcançar.
---

Um **espaço de trabalho** (workspace) é a pasta em que uma conversa trabalha, junto com o que ela pode alcançar além dela: outras pastas, sites, segredos e scripts. Cada conversa usa um espaço de trabalho. As conversas que não escolhem um usam o espaço de trabalho **Default**.

## Escolher um espaço de trabalho para uma conversa {#pick-a-workspace-for-a-conversation}

Use o seletor de espaço de trabalho abaixo da caixa de mensagem. Ele lista seus espaços de trabalho e oferece **New workspace**. O espaço de trabalho **Default** é usado por toda conversa que não escolheu outro.

## Editar um espaço de trabalho {#edit-a-workspace}

Abra **Settings › Workspaces** e escolha **Edit** no menu **⋯** de um espaço de trabalho, ou crie um com **New**. A caixa de diálogo tem um nome, a **Folder** principal (arquivos novos, capturas de tela e artefatos vão para ela) e uma linha por tipo de alcance. Cada linha mostra o que está definido e abre sua própria página:

| Página | O que define |
|---|---|
| **Allowed folders** | Outras pastas que este espaço de trabalho pode usar, cada uma com seu acesso. Outros espaços de trabalho não as alcançam. |
| **Sites** | Quais sites ele pode usar: **None**, **Listed sites** ou **Any site**, e como o [navegador integrado](../use/browser.md#allow-a-site) trata cada site listado. |
| **Secrets** | Quais dos seus segredos salvos ele pode enviar em uma requisição web. O modelo nunca vê o valor de um segredo. |
| **Scripts and commands** | Se ele pode executar **Scripts** em Python e Node.js, e **Commands**. |
| **Environment variables** | Valores passados aos seus scripts e comandos. |

O que significa a escolha em **Sites**:

- **None**: sem pesquisa na web, páginas web, downloads ou passos no navegador, e os scripts ficam offline.
- **Listed sites**: ele abre, baixa e usa no navegador apenas os sites listados e seus subdomínios. A pesquisa continua funcionando; os scripts ficam offline.
- **Any site**: qualquer site. Liste um site para escolher como o navegador o usa.

## Pastas permitidas {#allowed-folders}

Toda pasta que o coscribe pode usar fora da pasta principal de um espaço de trabalho fica em uma única lista, **Allowed folders**, em **Settings › Workspaces › Manage**. Cada pasta ali tem um nível de acesso (**Read only**, **Read and write** ou **Read, write and delete**). Um espaço de trabalho alcança apenas as pastas permitidas que escolher na sua página **Allowed folders**: **Use an allowed folder** escolhe uma da lista, e **Add new folder…** adiciona uma nova, que entra na lista com leitura e gravação.

Remover uma pasta de **Allowed folders** a remove de todos os espaços de trabalho. Uma pasta que não pode ser encontrada no momento, como uma unidade desconectada, é marcada e volta a ser usada quando reaparece.

Quando uma conversa precisa de uma pasta que não consegue alcançar, ela pergunta em um cartão; veja [Dar acesso a outra pasta](../use/approvals.md#give-access-to-another-folder).

## Scripts e isolamento {#scripts-and-isolation}

No Windows, os scripts rodam isolados: só podem usar as pastas da conversa, não podem excluir nem renomear arquivos nelas e só acessam a internet quando a configuração **Sites** do espaço de trabalho é **Any site**. O coscribe verifica uma vez se o isolamento funciona no seu computador. Se a verificação falhou, os scripts ficam desativados; **Run scripts without isolation**, na página **Scripts and commands**, os reativa para aquele espaço de trabalho, com o risco que isso traz.
