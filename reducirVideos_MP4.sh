#!/bin/bash

# Directorio de videos de entrada
INPUT_DIR="videos"
# Directorio para guardar los videos de salida
OUTPUT_DIR="videos_reducidos"
# Crear el directorio de salida si no existe
mkdir -p "$OUTPUT_DIR"

# Recorre cada archivo .mp4 en el directorio de entrada
for video in "$INPUT_DIR"/*.MP4; do
    # Obtiene el nombre base del archivo sin la extensiĂłn
    filename=$(basename "$video" .mp4)
    
    # Comprime el video
    ffmpeg -i "$video" -vcodec libx265 -crf 28 "$OUTPUT_DIR/${filename}_reducido.mp4"
    
    echo "Video $filename reducido y guardado en $OUTPUT_DIR"
done
