---
title: Trabalhar em uma conversa
description: Envie mensagens e arquivos, complemente um pedido enquanto o Coscribe trabalha, pare-o e desfaça ou altere o que você enviou.
---

Tudo no Coscribe começa em uma conversa. Cada uma tem seu próprio histórico, modelo, modo de permissão e pastas.

## Enviar mensagens e arquivos {#send-messages-and-files}

Digite na caixa de mensagem e pressione <kbd>Enter</kbd>. Para anexar um arquivo ou uma imagem, clique em **+**, no canto inferior esquerdo da caixa de mensagem, ou arraste-o para a janela. Os arquivos anexados são salvos na pasta `.coscribe/uploads/` do espaço de trabalho, para que o Coscribe possa abri-los de novo depois.

## Complementar um pedido enquanto ele trabalha {#add-to-a-request-while-it-works}

Você não precisa esperar uma resposta terminar. Tudo o que você envia enquanto o Coscribe trabalha vira uma nota que ele lê antes do próximo passo, incluindo imagens e arquivos. Uma nota em espera tem seus próprios botões:

- **Send now** a envia na hora.
- **Cancel and edit message** a devolve para a caixa de mensagem. Isso só é possível enquanto a caixa de mensagem estiver vazia.

Quando o Coscribe está esperando em um cartão (uma pergunta ou uma aprovação), o que você digita responde a esse cartão: uma resposta digitada a uma pergunta é a sua resposta, e uma resposta digitada a uma aprovação nega a ação e diz ao Coscribe por quê.

## Parar uma resposta {#stop-a-reply}

Clique em **Stop**, à direita da caixa de mensagem. O que o Coscribe já escreveu e fez é mantido, e a resposta termina com "Stopped · What should I do instead?". Ele não retoma o trabalho interrompido, a menos que você peça.

Parar uma resposta não para scripts ou comandos que ela deixou rodando em segundo plano; a linha abaixo da resposta diz quantos ainda estão rodando e abre o painel **Background tasks**, onde você pode pará-los.

## Voltar ou editar uma mensagem {#rewind-or-edit-a-message}

Passe o mouse sobre uma mensagem que você enviou para ver quando a enviou e três botões:

- **Rewind to here** remove essa mensagem e tudo o que vem depois dela, e coloca o texto de volta na caixa de mensagem.
- **Edit** permite alterar a mensagem; **Save** remove os turnos seguintes e envia o novo texto.
- **Copy** copia o texto.

> [!WARNING]
> Voltar remove turnos da conversa, não os efeitos deles. Um arquivo que o Coscribe gravou, um comando que executou ou uma mensagem que enviou por um conector continuam como estão. A dica de ferramenta avisa quando um turno que você está prestes a remover fez alguma dessas coisas.

Rewind e Edit não estão disponíveis enquanto uma resposta está em andamento ou um cartão espera por você, nem para mensagens anteriores a um `/compact`.

## Copiar uma conversa {#copy-a-conversation}

Digite `/fork` para copiar a conversa para uma nova e abri-la; `/fork Rascunho T3 B` dá um nome à cópia. As duas conversas continuam do mesmo ponto e trabalham nos mesmos arquivos, então um arquivo alterado por uma também muda para a outra.

## Manter uma conversa longa {#keep-a-long-conversation-going}

Cada modelo só consegue ler uma certa quantidade de cada vez. Quando uma conversa fica longa, digite `/compact`: o Coscribe a resume para liberar espaço e continua. `/clear` arquiva a conversa e começa uma nova no mesmo espaço de trabalho.

## Fazer uma pergunta paralela {#ask-a-side-question}

O painel **Side chat** (os dois balões de fala na barra de ferramentas) responde perguntas sobre a conversa sem acrescentar nada a ela, mesmo enquanto uma resposta está em andamento. Ele vê a conversa como ela está agora. As mensagens dele são mantidas apenas enquanto o painel está aberto.

## Visualização simples ou detalhada {#simple-or-detailed-view}

Por padrão, uma conversa mostra cada passo que o Coscribe dá. Em **Settings › General**, defina **Conversation view** como **Simple** para ver apenas a resposta e uma linha dizendo o que o Coscribe está fazendo, como "Reading" ou "Running commands". Os cartões que precisam de você, como aprovações e perguntas, aparecem nas duas visualizações, e voltar para **Detailed** mostra todos os passos de novo.
