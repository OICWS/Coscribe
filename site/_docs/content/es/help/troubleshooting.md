---
title: Solución de problemas
description: Comprueba con /doctor lo que coscribe necesita en tu PC, resuelve problemas comunes e informa de uno.
---

## Ejecutar una comprobación {#run-a-check}

Escribe `/doctor` en cualquier conversación. coscribe comprueba lo que necesita en este ordenador y muestra una tarjeta con cada resultado, primero los problemas, y cómo resolver cada uno. Si la solución es un ajuste, enlaza a su página.

| Comprobación | Qué mira |
|---|---|
| **Model** | Si el modelo predeterminado responde. Si no: revisa la clave, la dirección y el nombre del modelo del proveedor, o la red y el [proxy](../reference/settings.md#general). |
| **Python for scripts** | Si hay un Python para los scripts. Si no, descarga el propio de coscribe en **Settings** › **Capabilities**. |
| **Node.js for scripts** | Si `node` y `npm` están instalados, para scripts de Node.js. Instálalos desde [nodejs.org](https://nodejs.org) si los necesitas. |
| **Office conversion** | Si hay Microsoft Office o LibreOffice para generar vistas previas y convertir documentos. Si no hay ninguno, instala Office o descarga LibreOffice en **Settings** › **Capabilities**. |
| **Browser** | Si Microsoft Edge o Google Chrome están instalados, para el panel del navegador y las capturas de páginas. |
| **Script isolation** | Si los scripts pueden ejecutarse en su contenedor aislado. Hasta que pasa la autocomprobación, los scripts están desactivados; vuelve a ejecutarla en los ajustes del espacio de trabajo. |
| **Command sandbox** | Si los comandos se ejecutan en el entorno aislado. Si no está configurado, cada comando se ejecuta como tú, después de que lo apruebes. |

## Problemas comunes {#common-problems}

### Una respuesta falla o no llega {#a-reply-fails-or-never-comes}

Ejecuta `/doctor` y mira **Model**. Las causas habituales son una clave caducada, un nombre de modelo equivocado o una red que necesita proxy. Algunas redes de empresa bloquean los servicios de IA; pregunta a tu equipo de TI o configura el proxy en **Settings** › **General** › **Proxy**.

### coscribe no puede abrir un archivo o una carpeta {#coscribe-cant-open-a-file-or-folder}

coscribe solo trabaja en su espacio de trabajo y en las carpetas que permitiste. Cuando pida otra carpeta, permítela o añádela al espacio de trabajo. Consulta [Dar acceso a otra carpeta](../use/approvals.md#give-access-to-another-folder).

Si estás editando el mismo archivo de Word, Excel o PowerPoint, guarda tus cambios antes de pedir algo. coscribe nota cuándo un archivo cambió desde la última vez que lo leyó, lo vuelve a leer y hace su cambio sobre tu versión, pero solo ve lo que guardaste.

### Los scripts no se ejecutan {#scripts-dont-run}

Comprueba que **Run scripts** está activado en **Settings** › **Capabilities** y luego ejecuta `/doctor` y mira **Python for scripts** y **Script isolation**.

### Un conector deja de funcionar {#a-connector-stops-working}

Ábrelo en **Settings** › **Connectors**. Si dice que no está conectado, haz clic en **Retry**, o en **Sign in** si caducó su inicio de sesión.

### Una tarea programada no se ejecutó {#a-scheduled-task-didnt-run}

Las tareas solo se ejecutan mientras coscribe está en marcha, en la ventana o en la bandeja. Comprueba que **Keep running in the background** está activado en **Settings** › **General** y que la tarea no está en pausa. Una ejecución que tocaba con coscribe cerrado se ejecuta una vez cuando vuelve a iniciarse. Consulta [Tareas programadas](../workflows/scheduled-tasks.md).

## Informar de un problema {#report-a-problem}

Infórmalo en [GitHub](https://github.com/OICWS/coscribe/issues/new). Di qué pediste, qué pasó en su lugar y qué muestra `/doctor`.

Para mostrar cómo falló un turno sin compartir tus palabras, haz clic derecho en la conversación en la barra lateral y elige **Export a failed turn…**. El archivo dice cómo fue el turno: el modelo, sus llamadas a herramientas y fallos, los tokens y el tiempo, y el inicio de cada error de herramienta. No contiene ninguna palabra de la conversación, y no se envía nada: tú guardas el archivo y decides quién lo recibe.

El registro del servidor está en `%APPDATA%\Coscribe\logs\coscribe-server.log`.
