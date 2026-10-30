# datos-iniciales Specification

## Purpose

`python seed.py` deja la base en el estado inicial conocido que usan los casos de prueba: vacía las tablas y carga el catálogo de estados y los datos de ejemplo del PDF, con los ids de sus ejemplos, de forma repetible y en una sola transacción. Es parte de la puesta en marcha, no un extra.

## Requirements

### Requirement: Catálogo de estados
El seed SHALL cargar primero el catálogo: `PENDIENTE` (posición 1), `EN_REPARACION` (2), `TERMINADA` (3, final) y `CANCELADA` (4, final), los mismos códigos que el contrato de la API. Las descripciones son «Pendiente», «En reparación», «Terminada» y «Cancelada» («No especificado en la consigna», decisión de la alumna).

#### Scenario: S5 — Catálogo igual al contrato
- **GIVEN** Dada la base de prueba recién cargada por el seed
- **WHEN** Cuando se lee el catálogo de estados
- **THEN** Entonces sus códigos son exactamente los del contrato de estados de la API
- **AND** posiciones, finales y descripciones son los de este requisito

### Requirement: Ids iguales a los de los ejemplos del PDF
Los ids SHALL salir del orden de alta, sobre secuencias reiniciadas y sin fijarlos a mano, y coincidir con DA-02 a DA-06: usuarios 1 a 7, clientes 1 y 2, vehículos 1 a 3, repuestos 1 a 4 y órdenes 1 y 2.

#### Scenario: S1 — Cada id con su clave natural
- **GIVEN** Dada la base de prueba recién cargada por el seed
- **WHEN** Cuando se leen los ids de usuarios, clientes, vehículos, repuestos y órdenes
- **THEN** Entonces `admin@` es 1, `admin2@` 2, `recepcion@` 3, `mecanico@` 4, `mecanico2@` 5, `cliente@` 6 y `nuevo@` 7
- **AND** Laura es el cliente 1 y Jorge el 2; `AB123CD` es el vehículo 1, `AC456EF` el 2 y `AD789GH` el 3
- **AND** `FIL-001` es el repuesto 1, `FRE-010` el 2, `BUJ-020` el 3 y `ACE-530` el 4
- **AND** la orden 1 es del vehículo 1 y la orden 2 del vehículo 3

### Requirement: Usuarios, roles y contraseñas del seed
Los siete usuarios SHALL quedar activos, sin `password_cambiada_en` y con su rol vigente sin vencimiento ni otorgante. Sólo `nuevo@example.com` debe cambiar la contraseña. Todos usan `la contraseña ficticia definida en seed.py`, que es ficticia y vive sólo en `seed.py`, y cada uno tiene su propio hash.

#### Scenario: S6 — Roles y banderas
- **GIVEN** Dada la base de prueba recién cargada por el seed
- **WHEN** Cuando se leen los usuarios y sus asignaciones de rol
- **THEN** Entonces cada usuario tiene una sola asignación vigente, con el rol de DA-02, sin vencimiento, sin revocar y sin otorgante
- **AND** todos están activos y sin `password_cambiada_en`
- **AND** sólo `nuevo@example.com` debe cambiar la contraseña

#### Scenario: S7 — Contraseña común con hashes distintos
- **GIVEN** Dada la base de prueba recién cargada por el seed
- **WHEN** Cuando se verifica `la contraseña ficticia definida en seed.py` contra el hash de cada usuario
- **THEN** Entonces verifica contra los siete
- **AND** los siete hashes son distintos entre sí

#### Scenario: S16 — La contraseña vive sólo en el seed
- **GIVEN** Dados todos los archivos `.py` del proyecto, fuera del entorno virtual
- **WHEN** Cuando se busca el texto `la contraseña ficticia definida en seed.py`
- **THEN** Entonces aparece sólo en `seed.py`

### Requirement: Stock inicial cargado como movimiento
Cada repuesto SHALL nacer con su stock de DA-05 y con exactamente un movimiento «Stock inicial» por esa misma cantidad, sin orden y a nombre del usuario 1. Escribir el stock directo es una excepción acotada a la puesta en marcha (el punto único de stock llega en CH-08).

#### Scenario: S3 — Stock igual a la suma de movimientos
- **GIVEN** Dada la base de prueba recién cargada por el seed
- **WHEN** Cuando se leen los repuestos y sus movimientos
- **THEN** Entonces cada repuesto tiene un único movimiento «Stock inicial», con cantidad igual a su stock, sin orden y del usuario 1
- **AND** el stock de cada repuesto es igual a la suma de sus movimientos

### Requirement: Órdenes con ítems, totales e historiales
La orden 1 SHALL quedar PENDIENTE con 1 × `FIL-001` a 8500.00 y 4 × `ACE-530` a 12000.00, total 56500.00. La orden 2 SHALL quedar EN_REPARACION con `mecanico@` y 4 × `BUJ-020` a 6000.00, total 24000.00, sin descontar stock. Los historiales y autores son los de DA-06.

#### Scenario: S2 — Totales e ítems
- **GIVEN** Dada la base de prueba recién cargada por el seed
- **WHEN** Cuando se leen las órdenes y sus ítems
- **THEN** Entonces la orden 1 suma exactamente 56500.00 y la orden 2 exactamente 24000.00, como montos decimales
- **AND** cada ítem tiene la cantidad y el precio unitario de este requisito
- **AND** el stock de `BUJ-020` sigue en 2

#### Scenario: S4 — Historiales de precio y de estado
- **GIVEN** Dada la base de prueba recién cargada por el seed
- **WHEN** Cuando se leen los historiales
- **THEN** Entonces hay una sola línea de precio, del repuesto 1, de 8000.00 a 8500.00, del usuario 1
- **AND** la orden 1 tiene `null → PENDIENTE` del usuario 3
- **AND** la orden 2 tiene `null → PENDIENTE` del usuario 3 y `PENDIENTE → EN_REPARACION` del usuario 4

### Requirement: Evento de seguridad del seed
El seed SHALL dejar exactamente un evento de seguridad, con el actor `SISTEMA` (texto, no un usuario) y la acción «Carga de los datos iniciales».

#### Scenario: S8 — Un evento SISTEMA
- **GIVEN** Dada la base de prueba recién cargada por el seed
- **WHEN** Cuando se leen los eventos de seguridad
- **THEN** Entonces hay exactamente uno, con actor `SISTEMA` y acción «Carga de los datos iniciales»

### Requirement: Vaciado repetible
El seed SHALL vaciar las tablas del dominio y reiniciar sus secuencias antes de cargar, sin chocar con el disparador de sólo agregado (DA-31) y sin tocar el registro de versión de las migraciones. Correrlo varias veces deja siempre el mismo estado.

#### Scenario: S9 — Dos corridas, el mismo estado
- **GIVEN** Dada la base de prueba cargada una vez por el seed
- **WHEN** Cuando se corre el seed otra vez
- **THEN** Entonces las 13 tablas tienen las mismas filas, con los mismos ids, sin contar las columnas de hora

#### Scenario: S10 — Base con datos de sólo agregado
- **GIVEN** Dada la base de prueba con filas extra en las tres tablas de sólo agregado
- **WHEN** Cuando se corre el seed
- **THEN** Entonces termina sin error y cada una de esas tablas tiene sólo las filas del seed

#### Scenario: S11 — Versión de migraciones intacta
- **GIVEN** Dada la base de prueba en la última versión de las migraciones
- **WHEN** Cuando se corre el seed
- **THEN** Entonces la versión registrada sigue siendo la misma

### Requirement: Todo o nada
Vaciado y carga SHALL ocurrir en una sola transacción. Los hashes se calculan antes de abrirla. Si algo falla, la base queda como estaba antes de correrlo.

#### Scenario: S12 — Falla a mitad
- **GIVEN** Dada la base de prueba cargada por el seed y una falla provocada después del vaciado
- **WHEN** Cuando se corre el seed
- **THEN** Entonces termina con error
- **AND** la base tiene las mismas filas que antes de correrlo

### Requirement: Punto de entrada `python seed.py`
`python seed.py`, sin argumentos, SHALL cargar la base configurada en el entorno. Antes de vaciarla SHALL mostrar el nombre de la base, el host y el puerto, nunca la contraseña. No pide confirmación ni un flag («No especificado en la consigna», decisión de la alumna).

#### Scenario: S13 — Corrida real
- **GIVEN** Dado el entorno apuntado a la base de prueba
- **WHEN** Cuando se ejecuta `python seed.py` como proceso aparte
- **THEN** Entonces termina con código 0 y la base queda cargada
- **AND** la salida muestra el nombre de la base, el host y el puerto
- **AND** la salida no contiene la contraseña de la base

### Requirement: Corte sin esquema
Si las tablas no existen, `python seed.py` SHALL terminar con un código distinto de 0 y el mensaje «Corré `alembic upgrade head` primero» («No especificado en la consigna», decisión de la alumna).

#### Scenario: S15 — Base sin esquema
- **GIVEN** Dada la base de prueba después de `alembic downgrade base`, dentro del ciclo de migraciones
- **WHEN** Cuando se ejecuta `python seed.py` como proceso aparte
- **THEN** Entonces termina con un código distinto de 0
- **AND** la salida contiene «Corré `alembic upgrade head` primero»
