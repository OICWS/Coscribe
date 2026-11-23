---
title: Configurações
description: Todas as páginas das configurações do coscribe e o que cada configuração faz.
---

Abra as configurações pela engrenagem no canto superior direito ou com <kbd>Ctrl</kbd> + <kbd>,</kbd> no app para desktop. A caixa de pesquisa no topo encontra uma configuração pelo nome.

## General {#general}

| Configuração | O que faz |
|---|---|
| **Theme** | Claro, escuro ou igual ao Windows. |
| **Interface font** | A fonte de menus, painéis e conversas: Figtree, a fonte do próprio sistema ou OpenDyslexic. |
| **Motion** | **Reduced** reduz a animação nas respostas em andamento e em outros lugares. |
| **Conversation view** | **Simple** mostra cada resposta sem os passos por trás dela, e uma linha dizendo o que o coscribe está fazendo. **Detailed** mostra todos os passos. |
| **What should Coscribe call you?** | O nome na saudação da tela inicial. |
| **Default model** | O modelo com que uma nova conversa começa. Cada conversa pode trocar no seu próprio seletor de modelos. |
| **Default mode** | O [modo de permissão](../get-started/first-conversation.md#permission-modes) com que uma nova conversa começa. |
| **Global instructions** | O que o coscribe deve sempre saber. Veja [Instruções](../customize/instructions.md). |
| **Prompt suggestions** | Depois de uma resposta, sugere sua próxima mensagem na caixa de mensagem: <kbd>Enter</kbd> a envia, <kbd>Tab</kbd> a coloca na caixa para editar. Aumenta um pouco o seu uso. |
| **Background agents** | Permite que o coscribe passe trabalho para ajudantes que rodam em segundo plano enquanto você continua conversando. Eles podem consumir bastante do seu uso. |
| **Archive inactive conversations** | Arquiva conversas depois de 7, 30 ou 90 dias sem atividade, ou nunca. Uma conversa aberta ou com trabalho em andamento nunca é arquivada. |
| **Keep running in the background** | Fechar a janela mantém o coscribe na bandeja do sistema, então as tarefas agendadas continuam rodando. Desativado, fechar a janela encerra o app. |
| **Notifications** | **All** (todas as execuções de tarefas), **Problems only** (uma execução falhou ou está esperando por você) ou **Off**. |
| **Draw attention when Coscribe needs you** | Faz piscar o botão da barra de tarefas quando uma resposta termina ou o coscribe espera por você, e a janela não está em primeiro plano. |
| **Keep computer awake while Coscribe works** | Impede o PC de entrar em suspensão durante uma resposta, para que tarefas longas terminem. A tela ainda pode desligar, e fechar a tampa ainda suspende o PC. **Keep awake on battery power** faz o mesmo na bateria. |
| **Proxy** | Como o coscribe acessa a internet: **System**, **Manual** (endereço, hosts acessados diretamente, nome de usuário e senha) ou **No proxy**. |

## Workspaces {#workspaces}

A lista dos seus [espaços de trabalho](../workspaces/workspaces.md): **New** adiciona um, e o menu **⋯** de cada um o edita ou exclui. **Allowed folders** é a lista única de pastas fora da pasta principal de um espaço de trabalho, cada uma com seu acesso; um espaço de trabalho só alcança as que escolher. Veja [Pastas permitidas](../workspaces/workspaces.md#allowed-folders).

## Providers {#providers}

Os serviços de modelos que você conectou e os modelos ativados em cada um. Veja [Adicionar um provedor de modelos](../get-started/providers.md).

## Capabilities {#capabilities}

| Configuração | O que faz |
|---|---|
| **Create and edit files** | Permite que o coscribe grave e altere arquivos nas pastas do espaço de trabalho. Desativado, ele só os lê e responde na conversa. |
| **Artifacts** | Docs, designs e painéis que abrem ao lado da conversa. Veja [Docs, designs e painéis](../office/artifacts.md). |
| **Run scripts** | Para trabalhos grandes demais para as ferramentas integradas, o coscribe escreve um script Python ou Node.js e o executa depois que você aprova, restrito às pastas do espaço de trabalho. Veja [Scripts e isolamento](../workspaces/workspaces.md#scripts-and-isolation). |
| **Run commands** | Linhas de comando no cmd ou no PowerShell, para o que um script não consegue fazer, como git ou um instalador. Você aprova cada uma. **Command sandbox** e **Private folders** definem o que um comando pode alcançar. |
| **Chats can hand tasks to Code** | Permite que uma conversa passe um trabalho de programação para o Codex, um agente de programação. **Model for code** escolhe o modelo dele; **Change files without asking** permite que ele edite sem perguntar a cada alteração. |
| **Python for scripts**, **Packages for scripts** | Qual Python executa os scripts, e as bibliotecas extras de Python e Node.js que eles podem usar. |
| **LibreOffice**, **Codex** | Downloads opcionais, que você instala, atualiza ou remove aqui. O LibreOffice gera as visualizações de páginas. |

## Secrets {#secrets}

Chaves e tokens que você adiciona uma vez e depois entrega aos espaços de trabalho que precisam deles. O coscribe só pode usar um segredo em uma requisição web para os hosts que você permitir, e o modelo nunca vê o valor: ele fica fora das mensagens, dos resultados das ferramentas e dos logs. Os segredos ficam no Gerenciador de Credenciais do Windows, nunca em um arquivo de texto simples.

> [!IMPORTANT]
> Isso mantém o valor fora do que o modelo lê. Não é uma defesa contra um programa que vá procurá-lo: tudo o que o coscribe executa no seu PC roda como você e poderia ler o cofre de credenciais por conta própria.

## Skills, Connectors, Design systems {#skills-connectors-design-systems}

Veja [Habilidades e plugins](../customize/skills.md), [Conectores](../customize/connectors.md) e [Sistemas de design](../customize/design-systems.md).
