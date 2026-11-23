---
title: Modelos, esforço e contexto
description: Escolha o modelo de uma conversa, defina o quanto ele pensa e veja quão cheio está o contexto.
---

## Escolher um modelo {#pick-a-model}

Clique no nome do modelo abaixo da caixa de mensagem para trocar de modelo. A troca vale a partir da próxima mensagem, e a conversa mantém tudo o que foi dito até ali. Com o seletor aberto, as teclas <kbd>1</kbd> a <kbd>9</kbd> escolhem o modelo com aquele número.

O seletor lista os modelos que você ativou para cada provedor em **Settings** › **Providers**; veja [Adicionar um provedor de modelos](../get-started/providers.md). Uma nova conversa começa com o **Default model** de **Settings** › **General**.

## Definir o esforço {#set-the-effort}

Ao lado do modelo fica o controle de esforço, uma escala de **Faster** a **Smarter**. Mais esforço deixa o modelo raciocinar por mais tempo: melhor em tarefas difíceis, mais lento e mais caro. **Medium** é um bom começo.

Quando o coscribe conhece os níveis próprios do modelo, a escala mostra esses níveis, como **Low**, **Medium**, **High**, **Extra high** e **Max**. Caso contrário, mostra a escala inteira, e o modelo usa o nível mais próximo que suporta. Um modelo sem configuração de esforço mostra o controle desativado.

Sua escolha é mantida quando você troca de modelo: o novo modelo usa o nível mais próximo que tem.

## Acompanhar o contexto {#watch-the-context}

Cada modelo só consegue ler uma certa quantidade de uma vez: a sua janela de contexto. Depois que uma conversa começa, um anel ao lado da caixa de mensagem mostra quanto dela está em uso. Clique no anel para ver o que ocupa o espaço: as mensagens, o prompt do sistema, ferramentas e habilidades, e o espaço livre restante.

Quando a janela está cerca de quatro quintos cheia, o coscribe resume por conta própria a parte anterior da conversa para poder continuar. Você também pode digitar `/compact` para fazer isso agora. Veja [Manter uma conversa longa](conversations.md#keep-a-long-conversation-going).

## Reduzir custos {#keep-costs-down}

Você paga ao provedor pelo que o modelo lê e escreve. Alguns hábitos ajudam:

- Use um esforço menor para trabalho rotineiro.
- Comece uma nova conversa para um novo trabalho, em vez de continuar em uma longa.
- Desative **Prompt suggestions** e **Background agents** em **Settings** › **General** se não os usar; ambos acrescentam chamadas ao modelo.
- Para trabalhos que não podem sair do seu PC, ou que você faz com frequência, um [modelo no seu PC](../get-started/providers.md#run-a-model-on-your-pc) não tem custo por uso.
