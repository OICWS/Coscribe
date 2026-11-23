---
title: Flujos de trabajo
description: Guarda un trabajo como pasos fijos, inícialo con un horario o un evento y elige cuánto puede decidir la IA cuando un paso deja de funcionar.
---

Un flujo de trabajo es una tarea hecha de pasos fijos. A diferencia de una tarea programada que sigue instrucciones escritas, un flujo de trabajo hace los mismos pasos cada vez y los comprueba mientras se ejecutan, así que puedes ver lo que hará antes de que lo haga. Los horarios, los permisos y los informes de ejecución funcionan como en las [Tareas programadas](scheduled-tasks.md).

## Crear un flujo de trabajo {#make-a-workflow}

Lo más sencillo es hacer el trabajo una vez en un chat y luego crear un flujo de trabajo a partir de él:

- Elige **Save as workflow** cuando coscribe ofrezca **Save this job?**, o en el panel **Task details**.
- O escribe `/saveworkflow` en el cuadro de mensaje, seguido de un nombre si quieres.

coscribe redacta los pasos a partir de la conversación. Revísalos y guarda.

También puedes empezar de cero: **Scheduled** › **New task** › **Build a workflow**. Dale un nombre y un horario, guarda y luego añade los pasos en su página.

## La página del flujo de trabajo {#the-workflow-page}

La página tiene cuatro pestañas:

- **Overview** dice en palabras sencillas qué hace el flujo de trabajo: cuándo se ejecuta, sobre qué trabaja, dónde se detiene y te espera, y qué puede tocar. **Show the flowchart** dibuja los pasos.
- **Steps** enumera los pasos, donde los añades, cambias y reordenas. La vista también puede ser un **Flowchart**.
- **Runs** enumera las ejecuciones anteriores.
- **Settings** contiene el horario, el espacio de trabajo y los permisos.

**Run now** está en gris hasta que el flujo de trabajo tiene pasos. Si el flujo de trabajo recibe entradas, como un archivo, las pide primero.

## Tipos de pasos {#kinds-of-steps}

**Add a step** ofrece estos tipos:

| Paso | Qué hace |
|---|---|
| **Tool** | Usa una de las herramientas de coscribe, sin modelo. |
| **Script** | Ejecuta un script de Python fijo que has revisado. |
| **Model** | Una llamada al modelo que debe devolver campos definidos. |
| **Agent** | Trabaja hacia un objetivo con herramientas, dentro de los límites que fijas: las herramientas que puede llamar, las carpetas que puede cambiar y los sitios que puede abrir. |
| **Check** | Detiene la ejecución a menos que se cumplan unos valores. |
| **Approval** | Se pausa hasta que apruebas. |
| **Ask you** | Se pausa hasta que rellenas valores que usan los pasos siguientes. |
| **Wait** | Se pausa un tiempo, hasta una hora o hasta que aparece un archivo. |
| **Remember** | Guarda un valor para la siguiente ejecución, como lo que ya se procesó. |
| **Run a task** | Ejecuta otra de tus tareas como un paso y usa sus resultados. |
| **If / otherwise** | Ejecuta pasos distintos según un valor. |
| **Choose a path** | Varios caminos, elegidos según el valor. |
| **At the same time** | Ejecuta de 2 a 6 carriles de pasos a la vez y luego sigue. |
| **For each** | Repite pasos para cada elemento de una lista. |

Para cada paso puedes elegir qué pasa si falla: **Stop the run**, **Skip it and go on** o **Run other steps instead**. Un paso también puede reintentarse un número de veces.

## Cuando un paso deja de funcionar {#autonomy}

Los sitios web cambian y los archivos varían de una ejecución a otra. El ajuste **If a step stops working** decide cuánto puede decidir la IA cuando eso ocurre:

| Nivel | Qué pasa |
|---|---|
| **Fixed** | Solo se ejecutan los pasos guardados. Si uno falla, la ejecución se detiene y te lo dice. |
| **Self-healing** | Si un sitio web cambió, la IA hace ese paso sobre la página tal como es ahora. |
| **Proactive** | Los pasos de IA deciden cómo hacer su parte. Si un paso falla, la IA puede añadir algunos pasos; los que cambian algo te esperan. |
| **Autonomous** | La IA puede hacer toda la tarea a su manera. |

Cuando una ejecución sorteó un cambio, coscribe puede proponer pasos actualizados para que los revises, así la siguiente ejecución no tiene que hacerlo.

## Iniciar un flujo de trabajo con un evento {#start-on-an-event}

Además de los horarios de cualquier tarea, la **Frequency** de un flujo de trabajo puede ser:

- **Every few minutes**: cada pocos minutos.
- **When a file arrives in a folder**: elige la **Folder to watch** y, si quieres, un **File name pattern**. Cada archivo nuevo inicia una ejecución, con el archivo como entrada de archivo del flujo de trabajo. La opción necesita un flujo de trabajo que reciba un archivo.
- **When something new shows up in a connector**: elige un conector y qué preguntarle. coscribe pregunta cada pocos minutos, y cada elemento nuevo inicia una ejecución. La primera comprobación da por visto lo que ya hay.
- **When a program sends it an event**: otro programa del mismo ordenador envía una petición, con una clave, a una dirección que muestra coscribe. **Wait for a sample** guarda el siguiente evento para que elijas cuáles de sus campos rellenan las entradas. La dirección solo acepta peticiones de tu propio ordenador.

Un archivo que llegó mientras coscribe estaba cerrado inicia una ejecución cuando coscribe vuelve a iniciarse.
