# Criterios de Evaluación y Entrega

Textual de la consigna (p. 22). Puntajes de cada ejercicio (pp. 10-15) al lado.

| Criterio | Peso | Ejercicio (puntos) | Qué se mira |
|---|---|---|---|
| Proyecto, configuración y ciclo de vida | 8 % | Ej. 1 (8) | Estructura, Settings sin secretos por defecto, motor y fábrica creados en el lifespan, `get_session`, salud |
| Modelos, relaciones y migraciones | 14 % | Ej. 2 (14) | Restricciones, índices únicos parciales, catálogo con clave foránea, navegación, dos migraciones (una a mano), upgrade y downgrade |
| Contratos y CRUD | 10 % | Ej. 3 (10) | Contratos separados, `extra="forbid"`, códigos, ninguna entrada inválida en 500, PATCH parcial, envoltorio y paginación de la sección 2.9 |
| Autenticación | 16 % | Ej. 4 (16) | bcrypt fuera del bucle y con semáforo, orden del login, límite, hash ficticio, cookie `HttpOnly` |
| Autorización | 14 % | Ej. 5 (14) | 401 y 403, roles vigentes en la base, autoprotección, dos grupos de rutas, `iat`, lo propio |
| Repositorios y Unit of Work | 20 % | Ej. 6 (20) | Dos jerarquías, clase del modelo, `flush` y no `commit`, precarga en el repositorio, quién crea, abre, confirma y cierra, operaciones de varias escrituras |
| Integridad | 10 % | Ej. 7 (10) | Disparador de sólo agregado en las tres tablas; historial de precios en la misma transacción; intento de acceso en su propia sesión |
| Lecturas sin N+1 y asincronía | 8 % | Ej. 8 (8) | Consultas fijas en el detalle; ninguna llamada bloqueante; aviso en segundo plano |

## Condiciones excluyentes

> Un proyecto que **no levanta**, que **no crea su esquema con `alembic upgrade head` sobre una base vacía** o que **contiene credenciales reales en el repositorio** no se corrige hasta que se subsane.

## Formato de entrega

- Repositorio con el código fuente completo, `requirements.txt`, `env.example`, `alembic.ini`, la carpeta `migrations/` y la carpeta `test/`. El archivo `.env` no se sube.
- `README.md` con los pasos para levantar el proyecto desde cero: entorno virtual, dependencias, `.env` (con cómo generar la clave de firma), `alembic upgrade head`, `python seed.py` y arranque del servidor.
- **Evidencia del caso C-15**: una captura o un fragmento de la consola con las consultas del detalle de una orden con 2 ítems y de otra con 4.
- **Evidencia del caso C-14**: una captura de `psql` con los seis rechazos del disparador y el de la clave foránea.

## Checklist de entrega (derivado)

- [ ] `.env` en `.gitignore`; `env.example` sin secretos.
- [ ] Ningún secreto con valor por defecto en `Settings`; `alembic.ini` sin URL con contraseña.
- [ ] `alembic upgrade head` → `downgrade base` → `upgrade head` sobre base vacía.
- [ ] `python seed.py` corre sobre el esquema migrado.
- [ ] Un `.http` por grupo de casos, con la respuesta esperada en comentarios; `test/solo_agregado.sql`.
- [ ] Capturas de C-14 y C-15.
- [ ] README con la generación de la clave: `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
