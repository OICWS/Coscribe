---
title: Aprobaciones y modos de permisos
description: Elige cuánto puede hacer coscribe por su cuenta y responde a las tarjetas que muestra cuando te necesita.
---

coscribe no hace nada fuera de su alcance sin tu permiso. Cuánto te pregunta depende del modo de permisos de la conversación; a qué puede llegar depende del [espacio de trabajo](../workspaces/workspaces.md).

## Los cuatro modos {#the-four-modes}

Elige un modo con el botón de modo bajo el cuadro de mensaje. El predeterminado para conversaciones nuevas se fija en **Settings › General › Default mode**.

| Modo | Qué hace |
|---|---|
| **Manual** | Pregunta antes de cada cambio, script o acción externa. |
| **Accept Edits** | Edita archivos en tus carpetas sin preguntar; sigue preguntando antes de ejecutar código o acciones externas. |
| **Plan** | Investiga y escribe un plan para que lo apruebes antes de cualquier cambio. Consulta [Planes y listas de tareas](plans.md). |
| **Auto** | Un modelo revisor aprueba las acciones rutinarias y bloquea las arriesgadas en lugar de preguntarte. |

Si cambias de modo mientras se ejecuta una respuesta, el nuevo modo se aplica cuando termina.

## Aprobar una acción {#approve-an-action}

Cuando coscribe necesita tu aprobación, una tarjeta en la conversación nombra la acción, como «Run a command», y muestra lo que hará: el archivo que escribirá, el script o el comando. Léela y elige:

- **Approve** deja que esta acción siga adelante.
- **Allow for this task** (se muestra para los comandos y cambios del módulo de código) permite el mismo tipo de acción durante el resto de la tarea sin volver a preguntar.
- **Deny** la rechaza. Para decir por qué, escribe el motivo en el cuadro de mensaje; coscribe lo lee y se ajusta.

Si la tarjeta quedó fuera de la vista, un aviso sobre el cuadro de mensaje dice que algo espera; **Show** te lleva de vuelta.

> [!IMPORTANT]
> La tarjeta de un script dice cómo se ejecutará. Normalmente un script se ejecuta aislado: solo puede usar las carpetas de la conversación, no puede eliminar ni renombrar archivos en ellas y solo llega a internet cuando el ajuste **Sites** del espacio de trabajo es **Any site**. Una insignia **Not isolated** significa que el script se ejecutará sin ese aislamiento y puede llegar a cualquier archivo al que tú llegues; pasa el ratón sobre la insignia para ver por qué y lee el script antes de aprobarlo.

## Dar acceso a otra carpeta {#give-access-to-another-folder}

Cuando coscribe necesita una carpeta fuera del espacio de trabajo y de las carpetas que permitiste, lo pide en una tarjeta. Elige el acceso (**Read only**, **Read and write** o **Read, write and delete**) y luego:

- **Allow** añade la carpeta a tus carpetas permitidas de forma permanente.
- **Only this chat** la permite solo para esta conversación.
- **Save in my workspace instead** (cuando quería escribir) guarda el archivo en el espacio de trabajo.
- **Don't allow** lo rechaza.

coscribe nunca ofrece una unidad entera ni tu carpeta de usuario.

## Instalar un paquete para un script {#install-a-package-for-a-script}

Un script puede necesitar una biblioteca de Python o Node.js que coscribe aún no tiene. La tarjeta **Install a Python package** (o Node.js) la nombra y dice por qué. **Install** la instala en el entorno propio de coscribe, que el resto de tu ordenador no usa; **Not now** dice que no para esta conversación. Si la instalación falla, **Details** muestra la salida del instalador.

## Responder una pregunta {#answer-a-question}

A veces coscribe te pide que elijas, por ejemplo entre dos diseños. Elige una opción en la tarjeta o escribe tu propia respuesta en el cuadro de mensaje.
