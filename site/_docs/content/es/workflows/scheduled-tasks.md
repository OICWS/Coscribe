---
title: Tareas programadas
description: Haz que coscribe haga un trabajo según un horario, como un resumen cada mañana, y lee el informe de cada ejecución.
---

Una tarea programada es un trabajo que coscribe hace sin ti: a una hora fija, cada hora o cuando tú la inicias. Cada ejecución es su propia conversación y termina con un informe.

Hay dos tipos. Una **tarea programada** sigue instrucciones escritas, así que el modelo decide cada paso cada vez. Un **flujo de trabajo** ejecuta pasos fijos que guardaste, comprobados mientras se ejecutan; consulta [Flujos de trabajo](workflows.md). Esta página cubre lo que comparten.

## Crear una tarea {#create-a-task}

Abre **Scheduled** en la navegación y luego **New task**:

- **Create with Coscribe** abre un chat para que describas el trabajo o lo hagas una vez. coscribe redacta entonces la tarea en una tarjeta; **Review & save** la abre para que cambies lo que quieras antes de guardar.
- **Set up manually** abre el formulario, donde escribes tú el nombre, las instrucciones y el horario.
- **Build a workflow** empieza un flujo de trabajo vacío. Consulta [Flujos de trabajo](workflows.md).

Después de un trabajo hecho en un chat, coscribe también puede ofrecer **Save this job?**. **Save as workflow** lo convierte en pasos fijos que puedes volver a ejecutar o programar; **Save as skill** lo guarda como instrucciones para la próxima vez (consulta [Habilidades](../customize/skills.md)).

## Elegir cuándo se ejecuta {#choose-when-it-runs}

**Frequency** puede ser **Manual** (solo cuando la inicias), **Hourly**, **Daily**, **Weekdays**, **Weekly** o **Monthly**. Las ejecuciones diarias, de días laborables y semanales llevan una hora; las semanales también un día. Un flujo de trabajo también puede ejecutarse cada pocos minutos o cuando ocurre algo; consulta [Iniciar un flujo de trabajo con un evento](workflows.md#start-on-an-event).

Una tarea también tiene un **Workspace**, que decide las carpetas y sitios que pueden usar sus ejecuciones (consulta [Espacios de trabajo](../workspaces/workspaces.md)), y un **Model**. **Default model** usa el modelo fijado en tus ajustes.

## Elegir qué puede hacer sin ti {#choose-what-it-may-do-without-you}

Nadie vigila una ejecución, así que cada tarea fija sus propios **Permissions**:

| Ajuste | Qué pasa |
|---|---|
| **Ask before every action** | La ejecución se pausa y espera tu aprobación antes de cualquier acción que la necesite. |
| **Automatically approve** | La ejecución crea y edita archivos por su cuenta, pero se pausa antes de ejecutar código o usar conectores. |
| **Never ask** | La ejecución nunca se pausa para pedir aprobación, ni siquiera para ejecutar código o usar conectores. Tus reglas de bloqueo siguen aplicándose. |

**Most steps** termina una ejecución tras ese número de pasos, para que una ejecución que sale mal no dure mucho.

> [!WARNING]
> Con **Never ask**, una ejecución puede ejecutar código y usar tus conectores sin preguntar. Úsalo solo para una tarea cuyas instrucciones te inspiren confianza.

## Mantener la aplicación abierta {#keep-the-app-running}

Cerrar la ventana de coscribe lo deja funcionando en la bandeja del sistema, así que las tareas siguen ejecutándose. Para salir, elige **Quit** en el icono de la bandeja. Si desactivas **Keep running in the background** en **Settings** › **General**, cerrar la ventana cierra coscribe, y las tareas se detienen con él.

Si una ejecución tocaba mientras coscribe estaba cerrado, se ejecuta una vez cuando coscribe vuelve a iniciarse.

## Seguir las ejecuciones {#follow-the-runs}

La página de una tarea muestra cuándo se ejecuta la próxima vez, sus ejecuciones recientes y su estado: **Running**, **Completed**, **Failed**, **Needs approval**, **Waiting** o **Stopped**. Abre una ejecución para ver su conversación y su informe. Una ejecución que necesita aprobación te espera ahí.

- **Run now** inicia una ejecución al momento, para probar la tarea.
- El interruptor junto al estado pausa la tarea o la reanuda.
- El lápiz cambia el nombre de la tarea o cuándo se ejecuta.

**Notifications**, en **Settings** › **General**, elige si coscribe te avisa al terminar cada ejecución o solo de los problemas: una ejecución que falló o que te espera. Al hacer clic en una notificación se abre la ejecución.

## Que las ejecuciones recuerden {#remember-between-runs}

Activa **Remember between runs** en la página de una tarea programada, y cada ejecución escribe notas para la siguiente: su progreso, dónde se quedó y qué cambió. Desactivado, cada ejecución empieza sin notas.
