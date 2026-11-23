---
title: Privacidad y seguridad
description: Qué sale de tu ordenador al usar coscribe, dónde se guardan tus datos y qué mantiene sus acciones bajo control.
---

coscribe funciona en tu PC. No tiene cuenta ni servidor propio, y no envía nada sobre ti ni sobre tu uso a sus creadores.

## Qué sale de tu ordenador {#what-leaves-your-computer}

| Va a | Qué | Cuándo |
|---|---|---|
| El proveedor de modelos que elegiste | Tus mensajes, las partes de archivos que coscribe lee para responder y los resultados de sus herramientas | En cada respuesta. Un [modelo en tu PC](../get-started/providers.md#run-a-model-on-your-pc) también lo mantiene en tu ordenador. |
| Buscadores | Las palabras de búsqueda | Cuando coscribe busca en la web. Usa buscadores gratuitos como DuckDuckGo, sin clave. |
| Sitios web | Peticiones de página normales | Cuando coscribe abre una página que pediste o que necesita una tarea. Consulta [El navegador integrado](../use/browser.md). |
| Servicios que conectaste | Lo que envía la herramienta de un conector | Cuando coscribe usa ese [conector](../customize/connectors.md). |

Las condiciones del propio proveedor deciden qué guarda y durante cuánto tiempo. Léelas antes de enviarle documentos de trabajo.

## Dónde se guardan tus datos {#where-your-data-is-kept}

Todo lo demás se queda en tu PC:

- Tus archivos se quedan donde están; coscribe trabaja sobre ellos en su sitio.
- Las conversaciones, las tareas programadas, las habilidades y los ajustes están en `%APPDATA%\Coscribe`.
- Las claves de API y los [secretos](../reference/settings.md#secrets) están en el Administrador de credenciales de Windows, nunca en un archivo normal.
- Un registro de cómo fue cada turno (el modelo, las llamadas a herramientas, los errores, los tokens y el tiempo, sin las palabras de la conversación) se queda en tu PC para la solución de problemas. Nada lo sube.

## Qué mantiene las acciones bajo control {#what-keeps-actions-in-check}

- **Carpetas**: coscribe solo escribe en su espacio de trabajo y en las otras carpetas que permitiste. Consulta [Espacios de trabajo](../workspaces/workspaces.md).
- **Aprobaciones**: las acciones que cambian cosas te esperan, según diga el [modo de permisos](../use/approvals.md). Un archivo que coscribe elimina con sus propias herramientas de archivos va a la Papelera de reciclaje.
- **Scripts**: se ejecutan en un contenedor aislado donde Windows lo permite, limitados a las carpetas del espacio de trabajo; donde no se puede crear el aislamiento, los scripts quedan desactivados salvo que elijas otra cosa. Consulta [Scripts y aislamiento](../workspaces/workspaces.md#scripts-and-isolation).
- **Sitios**: lo que coscribe puede abrir en el navegador sigue el ajuste de sitios del espacio de trabajo. Consulta [Permitir un sitio](../use/browser.md#allow-a-site).

> [!IMPORTANT]
> Las aprobaciones son una comprobación tuya, no un entorno aislado. Un script o comando que apruebas puede hacer lo que puede hacer tu cuenta de Windows, salvo que el aislamiento lo limite. Lee lo que dice una tarjeta de aprobación antes de hacer clic en **Allow**.

## A qué prestar atención {#things-to-watch-for}

- Un texto de la web, un correo o un documento puede contener instrucciones dirigidas a una IA. coscribe trata lo que lee como material, no como órdenes tuyas, pero ningún modelo es perfecto: ten cuidado con **Never ask** y **Auto** cuando una tarea lee cosas que escribieron otros.
- Añade habilidades, plugins y conectores solo de personas en las que confíes.
