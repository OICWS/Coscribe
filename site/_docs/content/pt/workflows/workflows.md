---
title: Fluxos de trabalho
description: Salve um trabalho como passos fixos, inicie-o em um horário ou com um evento e escolha quanto a IA pode decidir quando um passo deixa de funcionar.
---

Um fluxo de trabalho é uma tarefa feita de passos fixos. Ao contrário de uma tarefa agendada que segue instruções escritas, um fluxo de trabalho executa os mesmos passos todas as vezes e os verifica durante a execução, então você pode ver o que ele fará antes que faça. Agendamento, permissões e relatórios de execução funcionam como em [Tarefas agendadas](scheduled-tasks.md).

## Criar um fluxo de trabalho {#make-a-workflow}

O jeito mais fácil é fazer o trabalho uma vez em um chat e depois criar um fluxo de trabalho a partir dele:

- Escolha **Save as workflow** quando o Coscribe oferecer **Save this job?**, ou no painel **Task details**.
- Ou digite `/saveworkflow` na caixa de mensagem, seguido de um nome, se quiser.

O Coscribe rascunha os passos a partir da conversa. Revise-os e salve.

Você também pode começar do zero: **Scheduled** › **New task** › **Build a workflow**. Dê um nome e um horário, salve e adicione os passos na página dele.

## A página do fluxo de trabalho {#the-workflow-page}

A página tem quatro abas:

- **Overview** diz em palavras simples o que o fluxo de trabalho faz: quando roda, em que trabalha, onde para e espera por você e o que pode alterar. **Show the flowchart** desenha os passos.
- **Steps** lista os passos, onde você os adiciona, altera e reordena. A visualização também pode ser um **Flowchart**.
- **Runs** lista as execuções anteriores.
- **Settings** guarda o horário, o espaço de trabalho e as permissões.

**Run now** fica desativado até o fluxo de trabalho ter passos. Se o fluxo de trabalho recebe entradas, como um arquivo, ele as pede primeiro.

## Tipos de passos {#kinds-of-steps}

**Add a step** oferece estes tipos:

| Passo | O que faz |
|---|---|
| **Tool** | Usa uma das ferramentas do Coscribe, sem envolver nenhum modelo. |
| **Script** | Executa um script Python fixo que você revisou. |
| **Model** | Uma chamada ao modelo que precisa devolver campos definidos. |
| **Agent** | Trabalha em direção a um objetivo com ferramentas, dentro dos limites que você define: as ferramentas que pode chamar, as pastas que pode alterar e os sites que pode abrir. |
| **Check** | Para a execução, a menos que certos valores se confirmem. |
| **Approval** | Pausa até você aprovar. |
| **Ask you** | Pausa até você preencher valores que os passos seguintes usam. |
| **Wait** | Pausa por um tempo, até um horário ou até um arquivo aparecer. |
| **Remember** | Guarda um valor para a próxima execução, como o que já foi tratado. |
| **Run a task** | Executa outra das suas tarefas como um passo e usa os resultados dela. |
| **If / otherwise** | Executa passos diferentes dependendo de um valor. |
| **Choose a path** | Vários caminhos, escolhidos pelo que um valor é. |
| **At the same time** | Executa de 2 a 6 faixas de passos ao mesmo tempo e depois continua. |
| **For each** | Repete passos para cada item de uma lista. |

Para cada passo, você pode escolher o que acontece se ele falhar: **Stop the run**, **Skip it and go on** ou **Run other steps instead**. Um passo também pode tentar de novo um número definido de vezes.

## Quando um passo deixa de funcionar {#autonomy}

Sites mudam e arquivos variam de uma execução para outra. A configuração **If a step stops working** decide quanto a IA pode decidir quando isso acontece:

| Nível | O que acontece |
|---|---|
| **Fixed** | Só os passos salvos rodam. Se um falhar, a execução para e avisa você. |
| **Self-healing** | Se um site mudou, a IA faz aquele passo na página como ela está agora. |
| **Proactive** | Os passos de IA decidem como fazer a sua parte. Se um passo falhar, a IA pode acrescentar alguns passos; os que alteram algo esperam por você. |
| **Autonomous** | A IA pode fazer a tarefa inteira do seu próprio jeito. |

Quando uma execução contornou uma mudança, o Coscribe pode sugerir passos atualizados para você revisar, para que a próxima execução não precise contornar.

## Iniciar um fluxo de trabalho com um evento {#start-on-an-event}

Além dos horários que toda tarefa tem, a **Frequency** de um fluxo de trabalho pode ser:

- **Every few minutes**.
- **When a file arrives in a folder**: escolha a **Folder to watch** e, se quiser, um **File name pattern**. Cada arquivo novo inicia uma execução, com o arquivo como entrada de arquivo do fluxo de trabalho. A opção exige um fluxo de trabalho que receba um arquivo.
- **When something new shows up in a connector**: escolha um conector e o que perguntar a ele. O Coscribe pergunta a cada poucos minutos, e cada item novo inicia uma execução. A primeira verificação considera como já visto o que já existe.
- **When a program sends it an event**: outro programa no mesmo computador envia uma requisição para um endereço que o Coscribe mostra, com uma chave. **Wait for a sample** guarda o próximo evento para você escolher quais campos dele preenchem as entradas. O endereço só aceita requisições do seu próprio computador.

Um arquivo que chegou enquanto o Coscribe estava fechado inicia uma execução quando o Coscribe abre de novo.
