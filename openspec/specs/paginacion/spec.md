# paginacion Specification

## Purpose

Define cómo se piden y se devuelven todos los listados de la API: los parámetros `page` y `size`, el envoltorio `{items, total, page, size, pages}` y el error de una página que no existe (Ejercicio 3, sección 2.9 de la consigna).

## Requirements

### Requirement: Parámetros de página
Todo listado paginado SHALL aceptar `page` (entero desde 1, por defecto 1) y `size` (entero de 1 a 100, por defecto 20). Un valor fuera de rango o que no es entero SHALL responder 422 por contrato.

#### Scenario: P5 — Defaults, límites y valores inválidos
- **GIVEN** Dada una ruta de prueba que usa los parámetros de página
- **WHEN** Cuando se la llama sin parámetros, con `size=100`, con `size=500`, con `size=0`, con `page=0` y con `page=abc`
- **THEN** Entonces sin parámetros recibe `page=1` y `size=20`, con `size=100` responde 200, y en los otros cuatro casos responde 422

### Requirement: Cálculo de las páginas
La cantidad de páginas SHALL ser el total dividido por `size`, redondeado hacia arriba, y nunca menor que 1. Cada página SHALL abarcar las filas desde `(page - 1) * size`, como máximo `size`.

#### Scenario: P1 — Ventana de cada página
- **GIVEN** Dados un total de 5 y `size=2`
- **WHEN** Cuando se calcula la página 1 y luego la página 3
- **THEN** Entonces hay 3 páginas
- **AND** la página 1 abarca desde la fila 0, como máximo 2, y la página 3 desde la fila 4

#### Scenario: P4 — Bordes del redondeo
- **GIVEN** Dado `size=100`
- **WHEN** Cuando el total es 100, y luego 101
- **THEN** Entonces hay 1 página, y después 2

### Requirement: Página inexistente
Pedir una página mayor que la última SHALL responder 422 con el cuerpo `{"detail": "La página <page> no existe: hay <pages>"}`, con `detail` como texto, sin consultar las filas.

#### Scenario: P2 — Más allá de la última
- **GIVEN** Dados un total de 4 y `size=2` (2 páginas)
- **WHEN** Cuando se pide la página 3
- **THEN** Entonces el error tiene exactamente el mensaje «La página 3 no existe: hay 2»

### Requirement: Cero resultados
Con cero resultados SHALL haber una página, vacía: la página 1 es válida y devuelve `items` vacío, y la página 2 es inexistente.

#### Scenario: P3 — Listado sin resultados
- **GIVEN** Dado un total de 0
- **WHEN** Cuando se pide la página 1, y luego la página 2
- **THEN** Entonces la página 1 es válida, con `pages=1`
- **AND** la página 2 da el error «La página 2 no existe: hay 1»

### Requirement: Envoltorio de los listados
La respuesta de todo listado paginado SHALL ser exactamente `{items, total, page, size, pages}`.

#### Scenario: P6 — Forma del envoltorio
- **GIVEN** Dada una página de resultados armada con sus items, el total y la ventana
- **WHEN** Cuando se la serializa a JSON
- **THEN** Entonces el objeto tiene exactamente las claves `items`, `total`, `page`, `size` y `pages`

### Requirement: Total con los mismos filtros
El `total` de un listado paginado SHALL contarse con los mismos filtros que las filas de la página.

#### Scenario: P7 — De punta a punta con la base
- **GIVEN** Dados artículos guardados que cumplen y que no cumplen un filtro
- **WHEN** Cuando se arma una página filtrada a partir del repositorio
- **THEN** Entonces `total` es la cantidad de artículos que cumplen el filtro, y `items` contiene sólo esos artículos
