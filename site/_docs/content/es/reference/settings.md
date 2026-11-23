---
title: Ajustes
description: Cada página de los ajustes de Coscribe y lo que hace cada ajuste.
---

Abre los ajustes con el engranaje arriba a la derecha, o con <kbd>Ctrl</kbd> + <kbd>,</kbd> en la aplicación de escritorio. El cuadro de búsqueda de arriba encuentra un ajuste por su nombre.

## General {#general}

| Ajuste | Qué hace |
|---|---|
| **Theme** | Claro, oscuro o igual que Windows. |
| **Interface font** | La fuente de menús, paneles y conversaciones: Figtree, la fuente del sistema u OpenDyslexic. |
| **Motion** | **Reduced** reduce la animación en las respuestas y en otras partes. |
| **Conversation view** | **Simple** muestra cada respuesta sin los pasos que hay detrás, y una línea que dice qué hace Coscribe. **Detailed** muestra cada paso. |
| **What should Coscribe call you?** | El nombre del saludo en la pantalla de inicio. |
| **Default model** | El modelo con el que empieza una conversación nueva. Cada conversación puede cambiarlo desde su propio selector. |
| **Default mode** | El [modo de permisos](../get-started/first-conversation.md#permission-modes) con el que empieza una conversación nueva. |
| **Global instructions** | Lo que Coscribe siempre debe saber. Consulta [Instrucciones](../customize/instructions.md). |
| **Prompt suggestions** | Tras una respuesta, sugiere tu siguiente mensaje en el cuadro de mensaje: <kbd>Enter</kbd> lo envía, <kbd>Tab</kbd> lo pone en el cuadro para editarlo. Suma un poco a tu uso. |
| **Background agents** | Deja que Coscribe pase trabajo a ayudantes que se ejecutan en segundo plano mientras sigues hablando. Pueden consumir mucho uso. |
| **Archive inactive conversations** | Archiva las conversaciones tras 7, 30 o 90 días sin actividad, o nunca. Una conversación abierta o con trabajo en marcha nunca se archiva. |
| **Keep running in the background** | Cerrar la ventana deja Coscribe en la bandeja, así que las tareas programadas siguen ejecutándose. Desactivado, cerrar la ventana cierra la aplicación. |
| **Notifications** | **All**: todas las ejecuciones de tareas; **Problems only**: una ejecución falló o te espera; **Off**: ninguna. |
| **Draw attention when Coscribe needs you** | Hace parpadear el botón de la barra de tareas cuando termina una respuesta o Coscribe te espera y la ventana no está delante. |
| **Keep computer awake while Coscribe works** | Impide que el PC entre en suspensión durante una respuesta, para que las tareas largas terminen. La pantalla puede apagarse, y cerrar la tapa sigue suspendiendo. **Keep awake on battery power** hace lo mismo con batería. |
| **Proxy** | Cómo llega Coscribe a internet: **System**, **Manual** (dirección, hosts a los que llegar directamente, usuario y contraseña) o **No proxy**. |

## Workspaces {#workspaces}

La lista de tus [espacios de trabajo](../workspaces/workspaces.md): **New** añade uno, y el menú **⋯** de cada uno lo edita o lo elimina. **Allowed folders** es la lista única de carpetas fuera de la carpeta principal de un espacio de trabajo, cada una con su acceso; un espacio de trabajo solo llega a las que elige. Consulta [Carpetas permitidas](../workspaces/workspaces.md#allowed-folders).

## Providers {#providers}

Los servicios de modelos que conectaste y los modelos activados en cada uno. Consulta [Añadir un proveedor de modelos](../get-started/providers.md).

## Capabilities {#capabilities}

| Ajuste | Qué hace |
|---|---|
| **Create and edit files** | Deja que Coscribe escriba y cambie archivos en las carpetas de su espacio de trabajo. Desactivado, solo los lee y responde en la conversación. |
| **Artifacts** | Docs, diseños y paneles que se abren junto a la conversación. Consulta [Docs, diseños y paneles](../office/artifacts.md). |
| **Run scripts** | Para trabajo demasiado grande para las herramientas integradas, Coscribe escribe un script de Python o Node.js y lo ejecuta después de que lo apruebes, limitado a las carpetas del espacio de trabajo. Consulta [Scripts y aislamiento](../workspaces/workspaces.md#scripts-and-isolation). |
| **Run commands** | Líneas de comandos en cmd o PowerShell, para lo que un script no puede hacer, como git o un instalador. Apruebas cada uno. **Command sandbox** y **Private folders** fijan a qué puede llegar un comando. |
| **Chats can hand tasks to Code** | Deja que una conversación pase un trabajo de programación a Codex, un agente de programación. **Model for code** elige su modelo; **Change files without asking** le deja editar sin preguntar por cada cambio. |
| **Python for scripts**, **Packages for scripts** | Qué Python ejecuta los scripts, y bibliotecas adicionales de Python y Node.js que pueden usar. |
| **LibreOffice**, **Codex** | Descargas opcionales, que instalas, actualizas o eliminas aquí. LibreOffice genera las vistas previas de páginas. |

## Secrets {#secrets}

Claves y tokens que añades una vez y das después a los espacios de trabajo que los necesitan. Coscribe solo puede usar un secreto en una petición web a los hosts que permitas, y el modelo nunca ve su valor: no aparece en los mensajes, los resultados de herramientas ni los registros. Los secretos se guardan en el Administrador de credenciales de Windows, nunca en un archivo normal.

> [!IMPORTANT]
> Esto mantiene el valor fuera de lo que lee el modelo. No protege contra un programa que lo busque: todo lo que Coscribe ejecuta en tu PC se ejecuta como tú y podría leer el almacén de credenciales por sí mismo.

## Skills, Connectors, Design systems {#skills-connectors-design-systems}

Consulta [Habilidades y plugins](../customize/skills.md), [Conectores](../customize/connectors.md) y [Sistemas de diseño](../customize/design-systems.md).
