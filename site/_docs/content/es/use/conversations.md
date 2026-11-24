---
title: Trabajar en una conversación
description: Envía mensajes y archivos, añade algo a una petición mientras Coscribe trabaja, detenlo y retira o cambia lo que enviaste.
---

Todo en Coscribe empieza en una conversación. Cada una tiene su propio historial, modelo, modo de permisos y carpetas.

## Enviar mensajes y archivos {#send-messages-and-files}

Escribe en el cuadro de mensaje y pulsa <kbd>Enter</kbd>. Para adjuntar un archivo o una imagen, haz clic en **+** abajo a la izquierda del cuadro de mensaje o arrástralo a la ventana. Los archivos adjuntos se guardan en la carpeta `.coscribe/uploads/` del espacio de trabajo, para que Coscribe pueda abrirlos de nuevo más tarde.

## Añadir algo mientras trabaja {#add-to-a-request-while-it-works}

No tienes que esperar a que termine una respuesta. Todo lo que envíes mientras Coscribe trabaja se convierte en una nota que lee antes de su siguiente paso, imágenes y archivos incluidos. Una nota en espera tiene sus propios botones:

- **Send now** la envía al momento.
- **Cancel and edit message** la devuelve al cuadro de mensaje. Solo es posible mientras el cuadro de mensaje está vacío.

Cuando Coscribe espera una tarjeta (una pregunta o una aprobación), lo que escribes responde a esa tarjeta: una respuesta escrita a una pregunta es tu respuesta, y una respuesta escrita a una aprobación rechaza la acción y le dice a Coscribe por qué.

## Detener una respuesta {#stop-a-reply}

Haz clic en **Stop** a la derecha del cuadro de mensaje. Lo que Coscribe ya escribió e hizo se conserva, y la respuesta termina con «Stopped · What should I do instead?». No retomará el trabajo detenido a menos que se lo pidas.

Detener una respuesta no detiene los scripts ni los comandos que dejó ejecutándose en segundo plano; la línea bajo la respuesta dice cuántos siguen en marcha y abre el panel **Background tasks**, donde puedes detenerlos.

## Rebobinar o editar un mensaje {#rewind-or-edit-a-message}

Pasa el ratón sobre un mensaje que enviaste para ver cuándo lo enviaste y tres botones:

- **Rewind to here** elimina ese mensaje y todo lo posterior, y devuelve su texto al cuadro de mensaje.
- **Edit** te deja cambiar el mensaje; **Save** elimina los turnos posteriores y envía el texto nuevo.
- **Copy** copia el texto.

> [!WARNING]
> Rebobinar elimina turnos de la conversación, no sus efectos. Un archivo que escribió Coscribe, un comando que ejecutó o un mensaje que envió por un conector se quedan como están. La información emergente te avisa cuando un turno que vas a eliminar hizo alguna de estas cosas.

Rebobinar y editar no están disponibles mientras se ejecuta una respuesta o una tarjeta te espera, ni para mensajes anteriores a un `/compact`.

## Copiar una conversación {#copy-a-conversation}

Escribe `/fork` para copiar la conversación en una nueva y abrirla; `/fork Borrador B del T3` le pone nombre a la copia. Las dos conversaciones siguen desde el mismo punto y trabajan sobre los mismos archivos, así que un archivo cambiado desde una cambia también para la otra.

## Mantener una conversación larga {#keep-a-long-conversation-going}

Cada modelo solo puede leer cierta cantidad a la vez. Cuando una conversación se alarga, escribe `/compact`: Coscribe la resume para liberar espacio y sigue. `/clear` archiva la conversación y empieza una nueva en el mismo espacio de trabajo.

## Hacer una pregunta al margen {#ask-a-side-question}

El panel **Side chat** (los dos bocadillos de la barra de herramientas) responde preguntas sobre la conversación sin añadirle nada, incluso mientras se ejecuta una respuesta. Ve la conversación tal como está ahora. Sus mensajes solo se conservan mientras el panel está abierto.

## Vista simple o detallada {#simple-or-detailed-view}

De forma predeterminada, una conversación muestra cada paso que da Coscribe. En **Settings › General**, pon **Conversation view** en **Simple** para ver solo la respuesta y una línea que dice qué está haciendo Coscribe, como «Reading» o «Running commands». Las tarjetas que te necesitan, como aprobaciones y preguntas, se muestran en ambas vistas, y volver a **Detailed** muestra de nuevo cada paso.
