# Referencia de la API

Base URL: `http://localhost:8000/api/v1`
Documentación interactiva (OpenAPI/Swagger): `http://localhost:8000/docs`

La autenticación usa **Bearer JWT**. Obtén un token en `/auth/login` y envíalo
en la cabecera `Authorization: Bearer <token>`.

## Autenticación

| Método | Ruta            | Descripción                         | Auth |
| ------ | --------------- | ----------------------------------- | ---- |
| POST   | `/auth/login`   | Login con `{email, password}` (JSON)| —    |
| POST   | `/auth/token`   | Login OAuth2 (form) para Swagger    | —    |
| GET    | `/auth/me`      | Usuario autenticado                 | ✅   |

## Participantes

| Método | Ruta                     | Descripción          | Auth   |
| ------ | ------------------------ | -------------------- | ------ |
| GET    | `/participants`          | Lista                | —      |
| GET    | `/participants/{id}`     | Detalle              | —      |
| POST   | `/participants`          | Crear                | Admin  |
| PUT    | `/participants/{id}`     | Actualizar           | Admin  |
| DELETE | `/participants/{id}`     | Eliminar             | Admin  |

## Partidos

| Método | Ruta                       | Descripción                          | Auth  |
| ------ | -------------------------- | ------------------------------------ | ----- |
| GET    | `/matches`                 | Lista (`?fase=&estado=`)             | —     |
| GET    | `/matches/{id}`            | Detalle                              | —     |
| POST   | `/matches`                 | Crear                                | Admin |
| PUT    | `/matches/{id}`            | Actualizar                           | Admin |
| POST   | `/matches/{id}/result`     | Registrar resultado + recalcular     | Admin |

## Predicciones

| Método | Ruta                    | Descripción                         | Auth |
| ------ | ----------------------- | ----------------------------------- | ---- |
| GET    | `/predictions`          | Lista (`?participant_id=&match_id=`)| —    |
| POST   | `/predictions`          | Crear/actualizar (upsert)           | ✅   |
| DELETE | `/predictions/{id}`     | Eliminar                            | ✅   |

## Ranking, Dashboard y Estadísticas

| Método | Ruta                          | Descripción                  | Auth  |
| ------ | ----------------------------- | ---------------------------- | ----- |
| GET    | `/ranking`                    | Clasificación general        | —     |
| POST   | `/ranking/recalculate`        | Forzar recálculo             | Admin |
| GET    | `/dashboard/summary`          | Resumen del panel            | —     |
| GET    | `/stats/hits`                 | Aciertos por participante    | —     |
| GET    | `/stats/phases`               | Puntos por fase              | —     |
| GET    | `/stats/participant/{id}`     | Estadísticas individuales    | —     |

## Exportación

| Método | Ruta                         | Formato       |
| ------ | ---------------------------- | ------------- |
| GET    | `/export/ranking.xlsx`       | Excel         |
| GET    | `/export/results.xlsx`       | Excel         |
| GET    | `/export/predictions.xlsx`   | Excel         |
| GET    | `/export/summary.pdf`        | PDF           |

## Administración (requiere rol Admin)

| Método | Ruta                          | Descripción                       |
| ------ | ----------------------------- | --------------------------------- |
| POST   | `/admin/sync`                 | Sincronización manual             |
| POST   | `/admin/import/calendar`      | Importar calendario del proveedor |
| POST   | `/admin/import/predictions`   | Importar predicciones (Excel)     |
| POST   | `/admin/import/rules`         | Importar reglas (Excel)           |
| GET    | `/admin/rules`                | Listar reglas                     |
| PUT    | `/admin/rules/{code}`         | Editar regla                      |
| GET    | `/admin/audit`                | Log de auditoría                  |
| POST   | `/admin/users`                | Crear usuario                     |
| GET    | `/admin/users`                | Listar usuarios                   |

## Ejemplo de login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@mundial2026.com","password":"admin1234"}'
```

Respuesta:

```json
{ "access_token": "eyJhbGc...", "token_type": "bearer" }
```
