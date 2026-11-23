---
title: Tarefas agendadas
description: Faça o Coscribe executar um trabalho em um horário programado, como um resumo matinal, e leia o relatório de cada execução.
---

Uma tarefa agendada é um trabalho que o Coscribe faz sem você: em um horário definido, a cada hora ou quando você a inicia. Cada execução é uma conversa própria e termina com um relatório.

Há dois tipos. Uma **tarefa agendada** segue instruções escritas, então o modelo decide cada passo a cada vez. Um **fluxo de trabalho** executa passos fixos que você salvou, verificados durante a execução; veja [Fluxos de trabalho](workflows.md). Esta página trata do que os dois têm em comum.

## Criar uma tarefa {#create-a-task}

Abra **Scheduled** na navegação e depois **New task**:

- **Create with Coscribe** inicia um chat para você descrever o trabalho, ou para percorrê-lo uma vez. O Coscribe então rascunha a tarefa em um cartão; **Review & save** a abre para que você possa mudar o que quiser antes de salvar.
- **Set up manually** abre o formulário, onde você mesmo escreve o nome, as instruções e o horário.
- **Build a workflow** inicia um fluxo de trabalho vazio. Veja [Fluxos de trabalho](workflows.md).

Depois de um trabalho feito em um chat, o Coscribe também pode oferecer **Save this job?**. **Save as workflow** o transforma em passos fixos que você pode executar de novo ou agendar; **Save as skill** o guarda como instruções para a próxima vez (veja [Habilidades](../customize/skills.md)).

## Escolher quando ela roda {#choose-when-it-runs}

**Frequency** pode ser **Manual** (só quando você a inicia), **Hourly**, **Daily**, **Weekdays**, **Weekly** ou **Monthly**. Execuções diárias, em dias úteis e semanais recebem um horário; as semanais também recebem um dia. Um fluxo de trabalho também pode rodar a cada poucos minutos, ou quando algo acontece; veja [Iniciar um fluxo de trabalho com um evento](workflows.md#start-on-an-event).

Uma tarefa também tem um **Workspace**, que decide as pastas e os sites que suas execuções podem usar (veja [Espaços de trabalho e pastas](../workspaces/workspaces.md)), e um **Model**. **Default model** usa o modelo definido nas suas configurações.

## Escolher o que ela pode fazer sem você {#choose-what-it-may-do-without-you}

Ninguém acompanha uma execução, então uma tarefa define suas próprias **Permissions**:

| Configuração | O que acontece |
|---|---|
| **Ask before every action** | A execução pausa e espera sua aprovação antes de qualquer ação que precise dela. |
| **Automatically approve** | A execução cria e edita arquivos por conta própria, mas pausa antes de executar código ou usar conectores. |
| **Never ask** | A execução nunca pausa para aprovação, inclusive para executar código e usar conectores. Suas regras de bloqueio continuam valendo. |

**Most steps** encerra uma execução depois desse número de passos, para que uma execução que dá errado não continue por muito tempo.

> [!WARNING]
> Com **Never ask**, uma execução pode rodar código e usar seus conectores sem perguntar. Use-o apenas para uma tarefa cujas instruções você confia.

## Manter o app rodando {#keep-the-app-running}

Fechar a janela do Coscribe o mantém rodando na bandeja do sistema, então as tarefas continuam rodando. Para sair, escolha **Quit** no ícone da bandeja. Se você desativar **Keep running in the background** em **Settings** › **General**, fechar a janela encerra o Coscribe, e as tarefas param junto.

Se uma execução estava prevista enquanto o Coscribe estava fechado, ela roda uma vez quando o Coscribe abrir de novo.

## Acompanhar as execuções {#follow-the-runs}

A página de uma tarefa mostra quando ela roda da próxima vez, suas execuções recentes e o status delas: **Running**, **Completed**, **Failed**, **Needs approval**, **Waiting** ou **Stopped**. Abra uma execução para ver sua conversa e seu relatório. Uma execução que precisa de aprovação espera por você ali.

- **Run now** inicia uma execução na hora, para testar a tarefa.
- O botão ao lado do status pausa a tarefa ou a retoma.
- O lápis renomeia a tarefa ou muda quando ela roda.

**Notifications**, em **Settings** › **General**, escolhe se o Coscribe avisa quando cada execução termina, ou só sobre problemas: uma execução que falhou ou está esperando por você. Clicar em uma notificação abre a execução.

## Deixar as execuções lembrarem {#remember-between-runs}

Ative **Remember between runs** na página de uma tarefa agendada, e cada execução escreve notas para a próxima: seu progresso, onde parou e o que mudou. Com a opção desativada, cada execução começa sem notas.
