# Reclamos Hidricos KMZ

Herramienta en Python para leer una planilla de reclamos, detectar direcciones y coordenadas, geolocalizar registros con OpenStreetMap/Nominatim y generar un archivo `.kmz` compatible con Google Earth.

## Que hace

- Lee una planilla `.xlsx` con columnas como `ID`, `Nº`, `Estado`, `Dirección del Ticket`, `Problema`, `Descripción`, `Lat` y `Lng`.
- Usa coordenadas existentes si ya estan en `Lat`/`Lng`.
- Extrae coordenadas escritas dentro de la descripcion, por ejemplo `-27.449512300000;-59.009170300000`.
- Consulta Nominatim para direcciones sin coordenadas.
- Genera:
  - `outputs/reclamos_hidricos_geolocalizados.kmz`
  - `outputs/reclamos_hidricos_geolocalizados.csv`
  - `cache/geocode_cache.json`

## Instalacion

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Verificacion

```bash
pip install -r requirements.txt
python -m unittest discover -s tests
```

En Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

Coloca la planilla en `data/` y ejecuta:

```bash
python src/geocode_reclamos.py data/reclamos_hidricos.xlsx
```

Tambien se pueden indicar nombres de columnas y carpeta de salida:

```bash
python src/geocode_reclamos.py data/reclamos_hidricos.xlsx ^
  --sheet "Reclamos - Hidricos" ^
  --address-column "Dirección del Ticket" ^
  --description-column "Descripción" ^
  --ticket-column "Nº" ^
  --output-dir outputs
```

## Google Earth

Abre `outputs/reclamos_hidricos_geolocalizados.kmz` en Google Earth Pro o Google Earth web. Cada punto incluye ticket, estado, problema, direccion y fuente de la coordenada.

## Mapa interactivo

Despues de generar el CSV geolocalizado, podes crear un mapa HTML interactivo con filtros, busqueda y popups:

```bash
python src/build_interactive_map.py outputs/reclamos_hidricos_geolocalizados.csv outputs/mapa_reclamos_interactivo.html
```

El HTML resultante se puede abrir en el navegador. Usa Leaflet y OpenStreetMap para mostrar el mapa.

El mapa permite corregir posiciones manualmente:

- Presiona `Editar ubicaciones`.
- Arrastra el punto mal ubicado hasta la posicion correcta.
- Presiona `Terminar edicion`.
- Presiona `Actualizar CSV/KMZ` para escribir las correcciones en los archivos.
- Los cambios quedan guardados en el navegador con `localStorage`.
- Usa `Exportar correcciones` para descargar un CSV con ticket, coordenadas originales y coordenadas corregidas.
- Desde el panel de edicion tambien podes descargar GeoJSON, revertir puntos o borrar todas las correcciones locales.

Para que el boton `Actualizar CSV/KMZ` escriba en disco, inicia el servidor editable en lugar de un servidor estatico:

```bash
python src/edit_server.py
```

Luego abre `http://127.0.0.1:8765/mapa_reclamos_interactivo.html`. Al presionar `Actualizar CSV/KMZ`, el servidor aplica las correcciones guardadas al CSV y regenera el KMZ.

## Precision

La geolocalizacion automatica no siempre encuentra direcciones informales como manzana/parcela, barrios sin altura, intersecciones ambiguas o textos incompletos. Por eso el script solo genera puntos cuando encuentra una coordenada dentro del area configurada para Resistencia, Chaco.

## Nominatim

Este proyecto usa el servicio publico de Nominatim con una pausa entre consultas. Para volumenes grandes o uso frecuente, conviene usar un proveedor propio o una API de geocodificacion con clave.

## Estructura

```text
reclamos-hidricos-kmz/
  src/geocode_reclamos.py
  data/.gitkeep
  outputs/.gitkeep
  cache/.gitkeep
  requirements.txt
  README.md
  LICENSE
```
