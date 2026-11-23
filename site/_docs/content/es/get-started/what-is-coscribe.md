---
title: Qué es coscribe
description: Un asistente de oficina que funciona en tu PC y crea archivos de Word, Excel y PowerPoint que puedes editar.
---

coscribe es un asistente de oficina con IA para Windows. Di en una frase lo que necesitas, y lee tus hojas de cálculo y documentos y crea el archivo terminado: un contrato con control de cambios y comentarios, una presentación de informe con gráficos, un libro de Excel conciliado.

Es de código abierto (licencia MIT) y gratuito. Solo pagas el servicio de modelos que elijas.

## Qué puede hacer {#what-it-can-do}

- **Excel**: leer, limpiar, resumir y conciliar datos; escribir fórmulas y gráficos.
- **Word**: redactar y revisar documentos, marcando los cambios con control de cambios y comentarios para que otros los revisen.
- **PowerPoint**: convertir datos y material en una presentación, con la plantilla y los colores de tu empresa si los tienes.
- **PDF**: buscar, extraer y organizar contenido.
- **La web**: abrir sitios en un navegador integrado, rellenar formularios y guardar tablas.
- **Flujos de trabajo**: guardar lo que hizo una conversación como pasos fijos y volver a ejecutarlo con un clic o según un horario.

## En qué se diferencia de otras herramientas de IA {#how-it-differs-from-other-ai-tools}

**Tus archivos se quedan en tu PC.** coscribe no tiene un servicio en la nube propio. Solo lo que el modelo necesita leer va al proveedor de modelos que elegiste; con un modelo que se ejecuta en tu propio ordenador mediante Ollama, nada sale de la máquina.

**Tú eliges el modelo.** Claude, GPT y Gemini vienen integrados. DeepSeek, Kimi, GLM, Qwen, Doubao y cualquier otro servicio con una API compatible con OpenAI funcionan en cuanto introduces su dirección y tu clave de API. Consulta [Añadir un proveedor de modelos](providers.md).

**Pregunta antes de cambiar cosas.** Cuatro modos de permisos van desde «pregúntame antes de cada paso» hasta «deja que un modelo revisor apruebe el trabajo rutinario por mí». En todos los modos solo escribe en las carpetas que permitiste. Consulta [Tu primera conversación](first-conversation.md#permission-modes).

**Te entrega archivos terminados, no borradores.** Después de escribir un archivo, coscribe lo renderiza y mira el resultado para comprobar el diseño y el contenido, en lugar de darte un bloque de texto.

## Requisitos del sistema {#system-requirements}

- Windows 10 o Windows 11.
- Una clave de API de un servicio de modelos, u Ollama o LM Studio en tu PC.

> [!NOTE]
> coscribe solo está disponible para Windows. Todavía no hay versión para Mac ni Linux.
