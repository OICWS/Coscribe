---
title: Modelos, esfuerzo y contexto
description: Elige el modelo de una conversación, ajusta cuánto piensa y mira cuánto de su contexto está ocupado.
---

## Elegir un modelo {#pick-a-model}

Haz clic en el nombre del modelo bajo el cuadro de mensaje para cambiar de modelo. El cambio se aplica desde el siguiente mensaje, y la conversación conserva todo lo dicho hasta ahora. Con el selector abierto, las teclas <kbd>1</kbd> a <kbd>9</kbd> eligen el modelo con ese número.

El selector muestra los modelos que activaste para cada proveedor en **Settings** › **Providers**; consulta [Añadir un proveedor de modelos](../get-started/providers.md). Una conversación nueva empieza con el **Default model** de **Settings** › **General**.

## Ajustar el esfuerzo {#set-the-effort}

Junto al modelo está el control de esfuerzo, una escala de **Faster** a **Smarter**. Más esfuerzo deja que el modelo razone más: mejor en tareas difíciles, más lento y más caro. **Medium** es un buen punto de partida.

Cuando Coscribe conoce los niveles propios del modelo, la escala muestra esos, como **Low**, **Medium**, **High**, **Extra high** y **Max**. Si no, muestra la escala completa y el modelo usa el nivel más cercano que admite. Un modelo sin ajuste de esfuerzo muestra el control en gris.

Tu elección se mantiene al cambiar de modelo: el nuevo modelo usa su nivel más cercano.

## Vigilar el contexto {#watch-the-context}

Cada modelo solo puede leer cierta cantidad a la vez: su ventana de contexto. Cuando una conversación ha empezado, un anillo junto al cuadro de mensaje muestra cuánto se ha usado. Haz clic en el anillo para ver qué ocupa el espacio: los mensajes, el prompt del sistema, las herramientas y habilidades, y el espacio libre que queda.

Cuando la ventana está llena en unas cuatro quintas partes, Coscribe resume por sí solo la parte anterior de la conversación para poder seguir. También puedes escribir `/compact` para hacerlo ya. Consulta [Mantener una conversación larga](conversations.md#keep-a-long-conversation-going).

## Gastar menos {#keep-costs-down}

Pagas al proveedor por lo que el modelo lee y escribe. Algunos hábitos ayudan:

- Usa menos esfuerzo para el trabajo rutinario.
- Empieza una conversación nueva para un trabajo nuevo, en lugar de seguir en una larga.
- Desactiva **Prompt suggestions** y **Background agents** en **Settings** › **General** si no los usas; ambos añaden llamadas al modelo.
- Para trabajo que no debe salir de tu PC, o que haces a menudo, un [modelo en tu PC](../get-started/providers.md#run-a-model-on-your-pc) no cuesta nada por uso.
