---
title: Libros de Excel
description: Haz que coscribe lea, limpie, sume y concilie hojas de cálculo, y cree libros con fórmulas y gráficos.
---

coscribe lee los archivos `.xlsx` hoja por hoja y escribe libros reales: celdas, estilos, fórmulas y gráficos nativos de Excel.

## Qué pedir {#what-to-ask-for}

- **Limpiar y sumar**: «Quita las filas sin dirección de envío y suma los importes por proveedor».
- **Conciliar**: «Cruza el extracto del banco con nuestro libro mayor y enumera lo que no cuadra».
- **Crear un modelo**: «Haz un presupuesto de 12 meses con una hoja resumen que sume los departamentos».
- **Graficar**: «Añade un gráfico de columnas de ingresos por región junto a la tabla».

Nombra los archivos y las hojas si un libro tiene varias, y di cómo debe ser el resultado: un archivo nuevo, una hoja nueva o un cambio en la existente.

## Las fórmulas siguen siendo fórmulas {#formulas-stay-formulas}

Cuando un valor depende de otras celdas, coscribe lo escribe como fórmula de Excel, así el libro sigue funcionando cuando cambias un número. También calcula las fórmulas y guarda sus resultados en el archivo, para que los valores se vean incluso en programas que no recalculan al abrir.

## Trabajos grandes o poco comunes {#large-or-unusual-jobs}

Para lo que las herramientas integradas no cubren, coscribe puede escribir un script de Python (con `pandas` y `openpyxl`, por ejemplo) y ejecutarlo con tu aprobación. Consulta [Aprobaciones y modos de permisos](../use/approvals.md).

> [!TIP]
> ¿Quieres que coscribe siga las convenciones de tu equipo, como colores para entradas y salidas o un formato de número? Ponlas en tus [instrucciones](../customize/instructions.md) o en una [habilidad](../customize/skills.md).
