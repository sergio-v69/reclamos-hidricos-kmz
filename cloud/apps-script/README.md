# Migracion a Google Sheets + Apps Script

Este paquete convierte el normalizador local en una Web App de Google Apps Script.

## Preparacion

1. Crear o importar una planilla Google Sheets con la base `reclamos_hidricos_geolocalizados_copia.csv`.
2. Renombrar la hoja principal a `tickets`.
3. En Apps Script, crear estos archivos:
   - `Code.gs`
   - `Index.html`
   - `appsscript.json`
4. Copiar el contenido de esta carpeta en el proyecto Apps Script.
5. Ejecutar `setupWorkbook` una vez desde Apps Script.
6. Autorizar permisos.

## Publicacion

1. En Apps Script: `Implementar` -> `Nueva implementacion`.
2. Tipo: `Aplicacion web`.
3. Ejecutar como: `Yo`.
4. Acceso: segun necesidad.
5. Abrir la URL de la Web App.

## Flujo

- `Probar geolocalizacion`: consulta Nominatim sin modificar coordenadas.
- `Guardar`: guarda direccion corregida y nota en la hoja.
- `Llamar al vecino`: marca el ticket como `requiere_llamada_vecino = SI`.
- `Geolocalizar corregidas`: escribe `lat`, `lng`, actualiza la hoja y genera un KMZ en Drive.

## Columnas esperadas

La hoja `tickets` debe incluir al menos:

- `id`
- `ticket`
- `fecha`
- `estado`
- `direccion`
- `problema`
- `descripcion`
- `lat`
- `lng`
- `fuente`

`setupWorkbook` agrega las columnas de trabajo que falten.
