# ADR 0005: SQLite para empleados y tickets

Estado: aceptada

## Contexto

El asistente necesita leer la fecha de ingreso y los días tomados de cada empleado, y guardar tickets con folio consecutivo. Es una demo con cinco empleados ficticios que debe arrancar con un solo comando y sin servicios externos.

## Opciones consideradas

1. **SQLite con `sqlite3` de la librería estándar.** Sin dependencias ni servidor; un archivo `data/rrhh.db`.
2. **PostgreSQL.** Concurrencia real y listo para producción, pero exige un servidor o Docker para correr la demo.
3. **Archivos JSON o CSV.** Aún más simple, pero sin transacciones ni consultas, y con riesgo de corromper el archivo al escribir tickets.
4. **ORM (SQLAlchemy).** Abstracción útil para crecer, pero excesiva para dos tablas.

## Decisión

Usar SQLite con `sqlite3` en `asistente_rrhh/db.py`:

- Tablas `empleados` (`id_empleado`, `nombre`, `puesto`, `fecha_ingreso`, `dias_vacaciones_tomados`) y `tickets` (`folio`, `id_empleado`, `tema`, `resumen`, `estado`, `creado_en`).
- `inicializar_bd()` es idempotente (`CREATE TABLE IF NOT EXISTS` e `INSERT OR IGNORE`) y la API la llama al arrancar si la base no existe.
- La ruta se lee de `config.RUTA_BD` en tiempo de ejecución para que las pruebas usen una base en `tmp_path`.
- Consultas siempre parametrizadas.

## Consecuencias

- **Se gana:** cero configuración, pruebas aisladas con una base temporal y transacciones para crear tickets.
- **Se sacrifica:** concurrencia de escritura y despliegue en varias instancias.
- **Riesgo que queda:** el folio `RH-AAAA-NNNN` se calcula contando los tickets del año dentro de una transacción; con escrituras simultáneas de varios procesos podría chocar la clave primaria y la tool respondería `error`. En producción se usaría PostgreSQL con una secuencia.
