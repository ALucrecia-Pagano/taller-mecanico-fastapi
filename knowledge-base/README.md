# Taller Mecánico — Base de Conocimiento

Base de conocimiento generada **únicamente** a partir de `docs/consigna/consigna-taller-mecanico.pdf` (TP integrador de Programación III, prof. Giuliano). Las aclaraciones del profesor en clase están identificadas como **[Profe]** en [09](09_decisiones_y_supuestos.md). Lo que el PDF no especifica está marcado **No especificado en la consigna** y reunido en [10](10_preguntas_abiertas.md).

## Índice de Archivos

| Archivo | Contenido |
|---|---|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, objetivos académicos y por actor, alcance, lo que queda afuera |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack y versiones, arquitectura en capas, convenciones de la API |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores, roles, **endpoints de referencia con códigos**, matriz RBAC |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | **Tablas y columnas obligatorias**, restricciones, índices, ERD, migraciones, **seed** |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | **RN-01 a RN-20**, máquina de estados, requisitos no funcionales |
| [06_funcionalidades.md](06_funcionalidades.md) | Épicas por ejercicio (1 a 8) con historias y criterios de aceptación |
| [07_flujos_principales.md](07_flujos_principales.md) | Flujos de punta a punta: auth, login, roles, órdenes, stock, precios |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones, **estructura obligatoria de carpetas**, seguridad, variables de entorno |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Decisiones (consigna / profe / alumna) y supuestos inferidos |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Inconsistencias y preguntas pendientes, priorizadas |
| [11_casos_de_prueba.md](11_casos_de_prueba.md) | **C-01 a C-19**, ejemplos de request/response de la consigna |
| [12_criterios_de_evaluacion.md](12_criterios_de_evaluacion.md) | Pesos de corrección, condiciones excluyentes, formato de entrega |

## Quick Start para Desarrolladores

1. Entender el dominio → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos → [04](04_modelo_de_datos.md)
3. Entender las reglas → [05](05_reglas_de_negocio.md)
4. Entender la arquitectura → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar → [07](07_flujos_principales.md), [06](06_funcionalidades.md)
6. Verificar → [11](11_casos_de_prueba.md), [12](12_criterios_de_evaluacion.md)
7. Antes de codificar → [10](10_preguntas_abiertas.md)

## Resumen Ejecutivo

API REST asincrónica (FastAPI + SQLModel/SQLAlchemy 2 async + PostgreSQL) para un taller mecánico: clientes y vehículos, órdenes de trabajo con ítems y estados, stock de repuestos movido sólo por movimientos, y acceso con bcrypt + JWT en cookie `HttpOnly` y roles con vigencia consultados en la base. El foco evaluado es la arquitectura Router → Service → UoW → Repository → Model, las transacciones que agrupan varias escrituras y las garantías delegadas en la base (índices únicos parciales, catálogo por FK, disparador de sólo agregado).
