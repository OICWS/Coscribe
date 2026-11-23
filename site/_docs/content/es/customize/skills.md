---
title: Habilidades y plugins
description: Enseña a Coscribe una forma de trabajar una sola vez, añade habilidades que hicieron otros y actívalas o desactívalas.
---

Una habilidad es un conjunto de instrucciones para un tipo de trabajo, como la forma en que tu equipo escribe un informe semanal. Cuando un trabajo encaja con la descripción de una habilidad, Coscribe la sigue. Coscribe trae algunas habilidades integradas, y puedes añadir las tuyas.

## Usar una habilidad {#use-a-skill}

No tienes que hacer nada: Coscribe elige una habilidad cuando encaja. Para usar una a propósito, escribe <kbd>/</kbd> en el cuadro de mensaje y elígela de la lista, o escribe su nombre tras la barra, seguido de tu petición.

## Guardar un trabajo como habilidad {#save-a-job-as-a-skill}

Después de hacer un trabajo en una conversación, puedes guardar cómo se hizo:

- Escribe `/create-skill` seguido de un nombre.
- O elige **Save as skill** cuando Coscribe ofrezca **Save this job?** tras un trabajo de varios pasos.

También puedes empezar desde **Settings** › **Skills** › **Add** › **Create with Coscribe**, que abre una conversación para que describas la habilidad.

## Añadir habilidades que hicieron otros {#add-skills-others-made}

En **Settings** › **Skills**:

- **Discover** muestra habilidades de código abierto de [github.com/anthropics/skills](https://github.com/anthropics/skills) y [github.com/anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins). La mayoría vienen como plugin: un conjunto de habilidades. Abre uno para ver sus habilidades, los conectores que usa y su licencia; **Add** descarga todas sus habilidades.
- **Add** › **Upload a skill** acepta un archivo de habilidad que te dieron: un `SKILL.md`, o un archivo `.zip`, `.skill` o `.plugin`.

> [!WARNING]
> Una habilidad son instrucciones que Coscribe sigue. Añade habilidades solo de personas en las que confíes, y lee una antes de usarla: ábrela en **Yours** para ver sus archivos.

## Activar o desactivar habilidades {#turn-skills-on-or-off}

**Yours** muestra tus habilidades. Abre una para leer sus archivos y usa su interruptor para desactivarla sin borrarla. El menú junto a una habilidad la elimina. Eliminar una habilidad que vino en un plugin elimina todas las habilidades de ese plugin.

## Habilidades para una carpeta {#skills-for-one-folder}

Una carpeta puede traer sus propias habilidades en `.coscribe/skills/`. Solo se aplican en conversaciones que usan esa carpeta, una vez que has aceptado sus ajustes. Consulta [Notas y reglas propias de una carpeta](../workspaces/folder-settings.md).

## Escribir una habilidad a mano {#write-a-skill-by-hand}

Una habilidad es una carpeta con un archivo `SKILL.md`. El archivo empieza con un `name` y una `description`, y luego las instrucciones en Markdown:

```markdown
---
name: Weekly report
description: Write the weekly sales report from the order export. Use when asked for the weekly report.
---

1. Read the latest export in Reports/Exports.
2. ...
```

La descripción decide cuándo usa Coscribe la habilidad, así que di para qué sirve y cuándo usarla. Es el mismo formato que las habilidades de Claude Code.
