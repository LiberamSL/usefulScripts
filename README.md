# usefulScripts
A variety of scripts to use on a daily basis
- [reducirVideos.sh](https://github.com/LiberamSL/usefulScripts/blob/main/reducirVideos_MP4.sh) | script en BASH para reducir el tamaño de los videos mediante ffmpeg
- [extract_GEO_Frames.py](https://github.com/LiberamSL/usefulScripts/blob/main/extract_GEO_Frames.py) | script en Python para extraer frames de videos de drones DJI y georeferenciarlos con su fichero SRT. [Video](https://youtu.be/w59uDUbYOiI)

## GDAL
**Compresión / Asignación SRC**
`gdalwarp -t_srs EPSG:25830 -co COMPRESS=JPEG -of GTiff input.tif output.tif`

**Extraer banda**
`gdal_translate -b 1 -of AAIGrid ortomosaico.tif ortomosaico_band1.asc` 

**Transformamos el Tiff a COG**
gdal_translate ortoInn.tiff ortoOut.tif -of COG -co COMPRESS=DEFLATE -co BIGTIFF=YES -co NUM_THREADS=ALL_CPUS

## ogr2ogr 
**Transformar varias capas vectoriales:: geojson en SRC 25830 a formato kml en SRC 4326**
`for i in *.geojson; do ogr2ogr -f "KML" -s_srs EPSG:25830 -t_srs EPSG:4326 kml/$i.kml $i; done`

## CLOUDCOMPARE
** De e57 a LAS **
1 en 1: `C:\Program Files\CloudCompare\CloudCompare.exe" -SILENT -O -GLOBAL_SHIFT AUTO "nubeIn.e57" -C_EXPORT_FMT LAS -SAVE_CLOUDS`
Batch: `for %i in (*.e57) do "C:\Program Files\CloudCompare\CloudCompare.exe" -SILENT -GLOBAL_SHIFT AUTO -O "%i" -C_EXPORT_FMT LAS -SAVE_CLOUDS`
.bat para Windows
```
@echo off
REM Configura la ruta de CloudCompare
set CC_PATH="C:\Program Files\CloudCompare\CloudCompare.exe"

REM Carpeta donde están los archivos LAS
set INPUT_FOLDER="F:\25_09_10_Sardas\LAS\7_1"

REM Carpeta de salida (puede ser la misma que la de entrada)
set OUTPUT_FOLDER="F:\25_09_10_Sardas\LAS\7_1\e57"

REM Crear carpeta de salida si no existe
if not exist %OUTPUT_FOLDER% mkdir %OUTPUT_FOLDER%

REM Bucle para convertir todos los LAS a E57 solo XYZ + RGB
for %%f in (%INPUT_FOLDER%\*.laz) do (
    echo Procesando %%~nxf
    %CC_PATH% -SILENT -NO_TIMESTAMP -O "%%f" -SAVE_CLOUDS FILE "%OUTPUT_FOLDER%\%%~nf.e57" PREC=FLOAT RGB=ON
)

echo Conversión finalizada.
pause
```

## PDAL
**Reducir**
`pdal translate D:\nubeIn.las D:\nubeOut.laz decimation --filters.decimation.step=10`

Bash
```
mkdir -p 2mm

# 2. Iniciar el bucle sobre todos los archivos .e57
for i in *.e57; do
    # Verifica que $i no sea la cadena literal "*.e57" si no hay archivos
    if [ -f "$i" ]; then
        
        # Extrae el nombre base del archivo (sin extensiÃ³n .e57)
        BASE_NAME=$(basename "$i" .e57)

        echo "Procesando: $i -> 2mm/$BASE_NAME.txt"
        
        # Comando PDAL con la sintaxis validada
        pdal translate "$i" "2mm/$BASE_NAME.txt" sample assign \
        --filters.sample.radius=0.002 \
        --filters.assign.value="Red=Red/256" \
        --filters.assign.value="Green=Green/256" \
        --filters.assign.value="Blue=Blue/256" \
        --writers.text.order="X,Y,Z,Intensity,Red,Green,Blue" \
        --writers.text.keep_unspecified=false

        echo "âœ” '$i' completado."
    fi
done

echo "ðŸŽ‰ Procesamiento de lotes finalizado."
```

CMD Windows
```
@echo off
mkdir "2mm" 2>nul

for %%F in (*.e57) do (
    echo Procesando: %%F
    pdal translate "%%F" "2mm\%%~nF.txt" sample assign --filters.sample.radius=0.002 --filters.assign.value="Red=Red/256" --filters.assign.value="Green=Green/256" --filters.assign.value="Blue=Blue/256" --writers.text.order="X,Y,Z,Intensity,Red,Green,Blue" --writers.text.keep_unspecified=false
)

echo ✔ Procesamiento completado.
pause
```

**Reproyectar**
`pdal translate nubeIn.las nubeOut.las reprojection --filters.reprojection.in_srs="EPSG:25830" --filters.reprojection.out_srs="EPSG:25830”`
