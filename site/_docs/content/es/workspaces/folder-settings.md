---
title: Notas y reglas propias de una carpeta
description: Deja que una carpeta le diga a Coscribe qué contiene, qué habilidades y conectores usar y qué puede ejecutarse sin preguntar.
---

Una carpeta puede llevar instrucciones para Coscribe en una carpeta `.coscribe` dentro de ella. Coscribe las lee en cualquier conversación que use la carpeta, una vez que las has aceptado.

## Qué puede contener una carpeta {#what-a-folder-can-hold}

| Archivo | Qué hace |
|---|---|
| `.coscribe/memory.md` | Notas que Coscribe lee al empezar cada conversación en esta carpeta: para qué es, convenciones, nombres. |
| `.coscribe/skills/<name>/SKILL.md` | [Habilidades](../customize/skills.md) que solo se aplican en esta carpeta. |
| `.coscribe/settings.json` | Reglas de permisos (`allow`, `ask`, `deny`) y variables de entorno para scripts. |
| `.coscribe/mcp.json` | [Conectores](../customize/connectors.md) que usa esta carpeta. |

Coscribe nunca escribe `memory.md`, `settings.json` ni `mcp.json`; solo tú los editas. Los adjuntos que envías se guardan en `.coscribe/uploads/`.

## Aceptar los ajustes de una carpeta {#accept-a-folders-settings}

Los ajustes de una carpeta podrían venir de cualquiera que pudiera escribir en ella, así que Coscribe no los sigue hasta que estés de acuerdo. El panel **Task details** muestra **What Coscribe knows about this folder**, con las habilidades, los conectores y las reglas que trae la carpeta, agrupados como **Runs without asking**, **Always asks** y **Never runs**, y las variables para scripts. Haz clic en **Use them** para aceptar.

Si alguno de estos archivos cambia fuera de Coscribe, vuelve a preguntar.

## Reglas de permisos {#permission-rules}

`.coscribe/settings.json` usa la misma forma que el archivo de ajustes de Claude Code:

```json
{
  "permissions": {
    "allow": ["write_file(reports/*)"],
    "ask": ["run_background_command"],
    "deny": ["delete_file"]
  },
  "env": {
    "REPORT_REGION": "East"
  }
}
```

Una regla es el nombre de una herramienta de Coscribe, un patrón de nombres con `*`, o cualquiera de los dos con un patrón de su argumento principal entre paréntesis, como `write_file(docs/*)`. Las reglas solo deciden acciones que de otro modo esperarían tu aprobación. **deny** gana a **ask**, y **ask** a **allow**.

Algunos límites se mantienen siempre:

- Una regla nunca permite una acción que sale de tu ordenador, como enviar un mensaje por un conector; esas siguen preguntando.
- Un `*` solo no permite nada.
- Una regla `ask` pregunta incluso en el modo **Auto**.

## Variables para scripts {#variables-for-scripts}

Los valores `env` de `settings.json` se pasan a los scripts y comandos de la carpeta. Una carpeta no puede fijar variables que cambien qué programas se ejecutan o adónde va el tráfico, como `PATH`, los ajustes de proxy o `PYTHONPATH`.
