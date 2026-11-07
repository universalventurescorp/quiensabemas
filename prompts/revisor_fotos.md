# Revisor de fotos de las alternativas

En `trabajo/revision/` hay una imagen por pregunta (`p012.jpg`, …) con las 4 fotos que saldrán en las tarjetas A, B, C y D, y `indice.json` con la pregunta, las alternativas y lo que se buscó para cada foto.

Abre **cada** imagen con la herramienta Read (sin saltarte ninguna) y decide si la pregunta puede salir con fotos. Apruébala (`"ok": true`) solo si se cumplen las cuatro cosas:

1. **Cada foto muestra de verdad lo que dice su alternativa.** No basta con que se parezca: un planeta tiene que ser ESE planeta, un órgano ESE órgano, un animal ESA especie (o una tan parecida que un niño no notaría la diferencia), un instrumento ESE instrumento, un plato ESE plato.
2. **La foto no regala la respuesta** (por ejemplo, un texto escrito en la foto con el nombre o la respuesta, o una foto que contesta la pregunta por sí sola).
3. **Es apta para toda la familia y no muestra a una persona reconocible** (salvo que la alternativa sea esa persona histórica y sea un retrato de dominio público).
4. **Se entiende en tamaño tarjeta**: no es un mapa diminuto, un diagrama ilegible, un logo, una foto casi negra o un collage de varias cosas.

Si UNA sola foto falla, toda la pregunta va con `"ok": false` (las tarjetas deben ser parejas). Ante la duda, `false`: es mejor una tarjeta de texto que una foto equivocada.

Escribe `trabajo/revision/veredicto.json` con este formato exacto, una entrada por cada imagen:

```json
{"12": {"ok": true}, "15": {"ok": false, "motivo": "B es Mercurio, no Venus"}}
```

No modifiques ningún otro archivo. Al terminar, escribe un resumen de una línea: cuántas aprobaste y cuántas rechazaste.
