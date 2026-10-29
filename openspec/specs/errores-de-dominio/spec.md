# errores-de-dominio Specification

## Purpose

Convierte los choques con lo guardado en errores propios con mensaje propio, y los errores de dominio en respuestas HTTP, sin entregar nunca texto interno de la base ni terminar en un 500 por una entrada inválida (RN-18, RN-01, DD-04).

## Requirements

### Requirement: Choque con una restricción conocida
Cuando una escritura dentro de un Unit of Work viola una restricción de la base (UNIQUE, CHECK o FK) que el módulo tiene mapeada, el sistema SHALL lanzar un error de conflicto con el mensaje propio del módulo. Ese mensaje no contiene el nombre de la restricción, de la tabla ni de la columna, ni texto de la base.

#### Scenario: E1 — UNIQUE mapeado
- **GIVEN** Dado un artículo guardado y un mapa que asocia el UNIQUE del nombre a un mensaje propio
- **WHEN** Cuando se da de alta otro artículo con el mismo nombre
- **THEN** Entonces se lanza un conflicto con el mensaje propio
- **AND** el mensaje no contiene el nombre de la restricción, `prueba_articulo`, `nombre`, `duplicate`, `violates` ni `unique`

#### Scenario: E2 — CHECK mapeado
- **GIVEN** Dado un mapa que asocia el CHECK de `cantidad` a un mensaje propio
- **WHEN** Cuando se da de alta un artículo con una cantidad que el CHECK rechaza
- **THEN** Entonces se lanza un conflicto con ese mensaje propio, distinto del de E1

#### Scenario: E6 — FK mapeada al borrar un referenciado
- **GIVEN** Dado un artículo referenciado por un registro de `prueba_baja`, y un mapa que asocia la FK a un mensaje propio
- **WHEN** Cuando se borra el artículo (baja física, con envío inmediato a la base)
- **THEN** Entonces se lanza un conflicto con el mensaje propio de la FK
- **AND** el artículo sigue en la base (decisión de la alumna)

### Requirement: Choque sin mensaje mapeado
Cuando la restricción violada no está mapeada, incluida una NOT NULL, el sistema SHALL lanzar un error de conflicto con un mensaje genérico propio («La operación choca con datos existentes»), nunca un 500 ni texto de la base. Mensaje genérico y tratamiento de NOT NULL: **No especificado en la consigna**.

#### Scenario: E3 — Restricción sin mapear
- **GIVEN** Dado un Unit of Work sin mensaje para el UNIQUE del nombre
- **WHEN** Cuando se da de alta un artículo con un nombre repetido
- **THEN** Entonces se lanza un conflicto con el mensaje genérico propio

#### Scenario: E4 — NOT NULL
- **GIVEN** Dado un artículo sin `nombre`, que es NOT NULL
- **WHEN** Cuando se lo da de alta
- **THEN** Entonces se lanza un conflicto con el mensaje genérico propio
- **AND** queda un registro de nivel ERROR en el log del servidor

### Requirement: Registro del choque en el servidor
Al traducir un choque, el sistema SHALL dejar en el log del servidor el nombre de la restricción y el código SQLSTATE, que nunca llegan al cliente. **No especificado en la consigna.**

#### Scenario: E5 — Log con el detalle, mensaje sin el detalle
- **GIVEN** Dado un choque con el UNIQUE mapeado del nombre
- **WHEN** Cuando se traduce
- **THEN** Entonces el log del servidor contiene el nombre de la restricción y el SQLSTATE
- **AND** el mensaje del conflicto no contiene ninguno de los dos

### Requirement: Error de dominio a HTTP
Toda ruta de la API SHALL traducir los errores de dominio, se lancen en el handler o en una de sus dependencias: no encontrado → 404, conflicto → 409, página inexistente → 422, token inválido → 401. En los cuatro casos el cuerpo es `{"detail": "<mensaje>"}`.

#### Scenario: T1 — Los tres códigos
- **GIVEN** Dada una aplicación de prueba con rutas que lanzan no encontrado, conflicto y página inexistente
- **WHEN** Cuando se llama a cada ruta
- **THEN** Entonces las respuestas son 404, 409 y 422, cada una con `{"detail": "<mensaje del error>"}`

#### Scenario: T2 — Error lanzado desde una dependencia
- **GIVEN** Dada una ruta de prueba cuya dependencia lanza un conflicto
- **WHEN** Cuando se llama a la ruta
- **THEN** Entonces la respuesta es 409 con `{"detail": "<mensaje del error>"}`

#### Scenario: T6 — Token inválido
- **GIVEN** Dada una ruta de prueba cuya dependencia lanza token inválido
- **WHEN** Cuando se llama a la ruta
- **THEN** Entonces la respuesta es 401 con `{"detail": "Token inválido"}`

### Requirement: Un bug no se disfraza
Una excepción que no es de dominio SHALL quedar sin traducir y terminar como error interno (500), para que un bug se vea como bug.

#### Scenario: T3 — Excepción que no es de dominio
- **GIVEN** Dada una ruta de prueba que lanza un `ValueError`
- **WHEN** Cuando se la llama
- **THEN** Entonces la excepción no se traduce y la respuesta es 500

### Requirement: Toda ruta traduce los errores de dominio
Cada router de la aplicación SHALL declarar la traducción de errores de dominio, incluidas las rutas de salud. Sólo quedan exceptuadas las rutas propias de FastAPI (`/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc`). La forma declarativa en el router y el archivo que la implementa son **No especificado en la consigna** (decisión de la alumna, por la letra del PDF: el router «traduce errores»).

#### Scenario: T4 — Recorrido de las rutas de la aplicación
- **GIVEN** Dada la aplicación real
- **WHEN** Cuando se recorren todas sus rutas, salvo las propias de FastAPI
- **THEN** Entonces cada una declara la traducción de errores de dominio
- **AND** el conjunto recorrido no está vacío e incluye `/health/live`

#### Scenario: T5 — Salud sin cambios de comportamiento
- **GIVEN** Dadas las rutas de salud declarando la traducción de errores
- **WHEN** Cuando se corre la suite de CH-01
- **THEN** Entonces todos sus escenarios (H1-H7 y los demás) siguen en verde

### Requirement: Todo error de dominio tiene código HTTP
Cada subclase de error de dominio de la aplicación, directa o indirecta, SHALL tener un código HTTP en el mapa de traducción, propio o heredado de una clase de su jerarquía. Así ningún error de dominio nuevo puede terminar en 500 por falta de mapeo (decisión de la alumna).

#### Scenario: T7 — Recorrido de las subclases
- **GIVEN** Dada la aplicación real importada, con todos sus módulos
- **WHEN** Cuando se recorren todas las subclases de error de dominio, directas e indirectas
- **THEN** Entonces cada una resuelve un código HTTP
- **AND** el conjunto recorrido no está vacío e incluye token inválido


### Requirement: Límite de acceso a HTTP
Un error de dominio por límite de acceso SHALL traducirse en el router a 429 con cuerpo detail propio y Retry-After entero en segundos. No SHALL exponerse texto interno ni cambiar la traducción vigente de otros errores.

#### Scenario: E429 — Límite traducido
- **GIVEN** Dado una ruta o dependencia que lanza límite con dos segundos restantes
- **WHEN** Cuando se atiende la petición
- **THEN** Entonces responde 429 con Retry-After: 2 y detail propio

#### Scenario: E429b — Regresión
- **GIVEN** Dado una dependencia que lanza TokenInvalido con mensaje «Token inválido» y las rutas nuevas importadas
- **WHEN** Cuando se ejecutan T6 y T7 existentes
- **THEN** Entonces T6 conserva su 401 y mensaje original, y todos los errores de dominio nuevos tienen código HTTP; D6 se normaliza sólo en autenticación


