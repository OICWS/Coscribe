---
title: Espacios de trabajo y carpetas
description: Decide a qué carpetas, sitios, secretos y scripts puede llegar cada conversación.
---

Un **espacio de trabajo** es la carpeta en la que trabaja una conversación, junto con lo que puede alcanzar más allá: otras carpetas, sitios web, secretos y scripts. Cada conversación usa un espacio de trabajo. Las conversaciones que no eligen uno usan el espacio **Default**.

## Elegir un espacio de trabajo para una conversación {#pick-a-workspace-for-a-conversation}

Usa el selector de espacio de trabajo bajo el cuadro de mensaje. Muestra tus espacios de trabajo y ofrece **New workspace**. El espacio **Default** lo usa toda conversación que no haya elegido otro.

## Editar un espacio de trabajo {#edit-a-workspace}

Abre **Settings › Workspaces** y elige **Edit** en el menú **⋯** de un espacio de trabajo, o crea uno con **New**. El diálogo tiene un nombre, la **Folder** principal (los archivos nuevos, las capturas y los artefactos van ahí) y una fila por cada tipo de alcance. Cada fila muestra lo que está configurado y abre su propia página:

| Página | Qué configura |
|---|---|
| **Allowed folders** | Otras carpetas que este espacio de trabajo puede usar, cada una con su acceso. Los demás espacios de trabajo no llegan a ellas. |
| **Sites** | Qué sitios web puede usar: **None**, **Listed sites** o **Any site**, y cómo trata el [navegador integrado](../use/browser.md#allow-a-site) cada sitio de la lista. |
| **Secrets** | Cuáles de tus secretos guardados puede enviar en una petición web. El modelo nunca ve el valor de un secreto. |
| **Scripts and commands** | Si puede ejecutar **Scripts** de Python y Node.js, y **Commands**. |
| **Environment variables** | Valores que se pasan a sus scripts y comandos. |

Lo que significa cada opción de **Sites**:

- **None**: sin búsqueda web, páginas web, descargas ni pasos de navegador, y los scripts no se conectan.
- **Listed sites**: abre, descarga y usa en el navegador solo los sitios de la lista y sus subdominios. La búsqueda sigue funcionando; los scripts no se conectan.
- **Any site**: cualquier sitio. Añade un sitio a la lista para elegir cómo lo usa el navegador.

## Carpetas permitidas {#allowed-folders}

Todas las carpetas que coscribe puede usar fuera de la carpeta principal de un espacio de trabajo se guardan en una sola lista, **Allowed folders**, en **Settings › Workspaces › Manage**. Cada carpeta tiene un nivel de acceso (**Read only**, **Read and write** o **Read, write and delete**). Un espacio de trabajo solo llega a las carpetas permitidas que elige en su página **Allowed folders**: **Use an allowed folder** elige una de la lista, y **Add new folder…** añade una nueva, que entra en la lista como lectura y escritura.

Quitar una carpeta de **Allowed folders** la quita de todos los espacios de trabajo. Una carpeta que ahora no se encuentra, como una unidad desconectada, queda marcada y se vuelve a usar cuando regresa.

Cuando una conversación necesita una carpeta a la que no llega, lo pide en una tarjeta; consulta [Dar acceso a otra carpeta](../use/approvals.md#give-access-to-another-folder).

## Scripts y aislamiento {#scripts-and-isolation}

En Windows, los scripts se ejecutan aislados: solo pueden usar las carpetas de la conversación, no pueden eliminar ni renombrar archivos en ellas y solo llegan a internet cuando el ajuste **Sites** del espacio de trabajo es **Any site**. coscribe comprueba una vez si el aislamiento funciona en tu ordenador. Si la comprobación falló, los scripts quedan desactivados; **Run scripts without isolation**, en la página **Scripts and commands**, los vuelve a activar para ese espacio de trabajo, con el riesgo que eso conlleva.
