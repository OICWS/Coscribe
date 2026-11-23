---
title: Conectores
description: Conecta coscribe con los servicios que usas, como tu correo, tu calendario o tu gestor de proyectos, y elige qué puede hacer en ellos.
---

Un conector deja que coscribe use otro servicio: leer tu correo, añadir un evento a un calendario, consultar una incidencia. Los conectores usan el Model Context Protocol (MCP), así que funciona cualquier servidor MCP, no solo los que muestra coscribe.

## Añadir un conector {#add-a-connector}

Abre **Settings** › **Connectors** › **Discover**, elige el servicio y haz clic en **Connect**.

- La mayoría de los servicios en línea te piden iniciar sesión. El inicio de sesión se abre en la propia página del servicio, en tu navegador, y solo inicias sesión una vez. coscribe nunca ve tu contraseña.
- Un servicio marcado como **Needs setup** necesita antes una aplicación registrada en él. coscribe te guía, una sola vez. Si alguien ya lo configuró para tu equipo, **Copy a message for your admin** le pide el archivo de configuración.

coscribe también puede ofrecer un conector en una conversación, cuando tu petición necesita un servicio que no has conectado. Haz clic en **Connect** en la tarjeta, y coscribe sigue cuando está conectado. **Not now** lo deja; puedes conectarlo cuando quieras en **Settings** › **Connectors**.

## Añadir un conector personalizado {#add-a-custom-connector}

Para un servidor MCP que no aparece, elige **Add** › **Add custom connector**, dale un nombre y:

- Introduce la **MCP server URL** de un servidor en línea, con las cabeceras que necesite. Para poner una clave en una cabecera sin escribirla, usa **Insert a secret**; la cabecera queda como `{{secret:NAME}}` y el valor viene de [Secretos](../reference/settings.md#secrets).
- O elige **Run a local command instead** e introduce el comando, como `npx`, sus argumentos y las variables de entorno. Se ejecuta como un programa en este ordenador, con tus permisos.

> [!WARNING]
> Un comando local se ejecuta con todo lo que puede hacer tu cuenta de Windows. Añade solo servidores en los que confíes.

## Elegir qué puede hacer {#choose-what-it-may-do}

Abre un conector en **Yours** para ver sus herramientas, divididas en **Read-only tools** y **Write/delete tools**. Para cada herramienta, elige:

| Opción | Qué pasa |
|---|---|
| **Always allow** | coscribe la usa sin preguntar. |
| **Needs approval** | coscribe te pregunta cada vez. Consulta [Aprobaciones](../use/approvals.md). |
| **Blocked** | coscribe no puede usarla. |

La página del conector también dice si está conectado. Si no lo está, **Retry** vuelve a conectar y **Sign in** abre la página de inicio de sesión del servicio.

## Conectores para una carpeta {#connectors-for-one-folder}

Una carpeta puede traer sus propios conectores en `.coscribe/mcp.json`. Solo se aplican en conversaciones que usan esa carpeta, una vez que has aceptado sus ajustes. Consulta [Notas y reglas propias de una carpeta](../workspaces/folder-settings.md).

## Usar un conector en un flujo de trabajo {#use-a-connector-in-a-workflow}

Las herramientas de un conector pueden ser pasos de un [flujo de trabajo](../workflows/workflows.md), y un flujo de trabajo puede iniciarse cuando aparece algo nuevo en un conector. Consulta [Iniciar un flujo de trabajo con un evento](../workflows/workflows.md#start-on-an-event).
