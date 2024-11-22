# sudo apt update
# sudo apt install python3 python3-pip -y
# sudo apt install ffmpeg exiftool -y
# sudo apt install python3-opencv -y


import cv2
import re
from datetime import datetime, timedelta
import os
import subprocess  # Para ejecutar ExifTool desde Python

# Ruta al archivo de video y al archivo SRT con datos GPS
video_path = "video.mp4"
srt_path = "video.SRT"
output_folder = "frames"

# Crear la carpeta de salida para los frames
os.makedirs(output_folder, exist_ok=True)

# Abrir el archivo de video
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
frame_interval = 120  # Extraer una imagen cada 30 frames

# Nueva expresión regular para manejar rel_alt y abs_alt en el mismo corchete
pattern = re.compile(r"\[latitude: ([\d.-]+)\] \[longitude: ([\d.-]+)\].* \[rel_alt: [\d.]+ abs_alt: ([\d.]+)\]")

# Leer el archivo SRT y extraer los datos de GPS con sus marcas de tiempo
gps_data = []
with open(srt_path, "r") as file:
    for line in file:
        if "-->" in line:
            timestamp_str = line.split(" --> ")[0].strip()
            timestamp = datetime.strptime(timestamp_str, "%H:%M:%S,%f")
        match = pattern.search(line)
        if match:
            latitude, longitude, abs_alt = match.groups()
            gps_data.append({
                "timestamp": timestamp,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "absolute_altitude": float(abs_alt)
            })

# Verificar si gps_data contiene datos
if not gps_data:
    print("No se encontraron datos GPS en el archivo SRT. Verifica el formato del archivo.")
    cap.release()
    exit()

# Definir el tiempo de inicio según el archivo SRT
start_time = gps_data[0]["timestamp"]  # Primer timestamp del SRT

# Procesar cada frame y asociarlo con los datos GPS más recientes disponibles
frame_count = 0
gps_index = 0  # Índice para rastrear el dato GPS más cercano
success, frame = cap.read()

while success:
    # Extraer una imagen cada 30 frames
    if frame_count % frame_interval == 0 and gps_index < len(gps_data):
        # Calcular el tiempo actual en el video como un objeto datetime basado en start_time
        current_time = start_time + timedelta(seconds=(frame_count / fps))

        # Avanzar el índice gps_index hasta que el timestamp sea mayor o igual a current_time
        while gps_index < len(gps_data) - 1 and gps_data[gps_index]["timestamp"] <= current_time:
            gps_index += 1

        # Guardar el frame con el dato GPS asociado
        gps_info = gps_data[gps_index - 1]  # Usar el último valor válido
        frame_filename = f"{output_folder}/frame_{frame_count:04d}.jpg"
        cv2.imwrite(frame_filename, frame)

        # Agregar datos GPS a los metadatos del frame usando ExifTool
        latitude = gps_info["latitude"]
        longitude = gps_info["longitude"]
        altitude = gps_info["absolute_altitude"]

        subprocess.run([
            "exiftool",
            f"-GPSLatitude={latitude}",
            f"-GPSLongitude={longitude}",
            f"-GPSAltitude={altitude}",
            f"-GPSLatitudeRef={'N' if latitude >= 0 else 'S'}",
            f"-GPSLongitudeRef={'E' if longitude >= 0 else 'W'}",
            "-overwrite_original",  # Evita crear copias de respaldo
            frame_filename
        ])

        # Imprimir la asociación (opcional)
        print(f"Frame {frame_count} saved as {frame_filename} with GPS data: {gps_info}")

    # Leer el siguiente frame
    success, frame = cap.read()
    frame_count += 1

cap.release()
print("Proceso completado.")
