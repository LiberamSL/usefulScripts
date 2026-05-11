import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import threading
import glob

class FrameExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Extractor de Frames Optimizado - 360° y Normales")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Variables
        self.video_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.start_time = tk.DoubleVar(value=0) # Empezando en 0.5s (o 0 según ajustes)
        self.interval = tk.DoubleVar(value=0.5)
        self.format = tk.StringVar(value="jpg")

        self.create_widgets()

    def create_widgets(self):
        # 1. Video
        frame_video = tk.LabelFrame(self.root, text="1. Seleccionar video", padx=5, pady=5)
        frame_video.pack(fill="x", padx=10, pady=5)
        tk.Entry(frame_video, textvariable=self.video_path, width=45).pack(side="left", padx=5)
        tk.Button(frame_video, text="Examinar...", command=self.select_video).pack(side="left")

        # 2. Destino
        frame_out = tk.LabelFrame(self.root, text="2. Carpeta de destino", padx=5, pady=5)
        frame_out.pack(fill="x", padx=10, pady=5)
        tk.Entry(frame_out, textvariable=self.output_dir, width=45).pack(side="left", padx=5)
        tk.Button(frame_out, text="Seleccionar...", command=self.select_output_dir).pack(side="left")

        # 3. Parámetros
        frame_params = tk.LabelFrame(self.root, text="3. Parámetros de extracción", padx=5, pady=5)
        frame_params.pack(fill="x", padx=10, pady=5)

        row1 = tk.Frame(frame_params)
        row1.pack(fill="x", pady=2)
        tk.Label(row1, text="Tiempo inicio (seg):", width=18, anchor="w").pack(side="left")
        tk.Spinbox(row1, from_=0.0, to=3600.0, increment=0.1, textvariable=self.start_time, width=8).pack(side="left")

        row2 = tk.Frame(frame_params)
        row2.pack(fill="x", pady=2)
        tk.Label(row2, text="Intervalo (seg):", width=18, anchor="w").pack(side="left")
        tk.Spinbox(row2, from_=0.1, to=60.0, increment=0.1, textvariable=self.interval, width=8).pack(side="left")

        row3 = tk.Frame(frame_params)
        row3.pack(fill="x", pady=2)
        tk.Label(row3, text="Formato (Máxima Calidad):", width=22, anchor="w").pack(side="left")
        tk.Radiobutton(row3, text="JPEG (Recomendado)", variable=self.format, value="jpg").pack(side="left")
        tk.Radiobutton(row3, text="PNG (Lossless)", variable=self.format, value="png").pack(side="left")

        # Progreso y Log
        frame_progress = tk.LabelFrame(self.root, text="Progreso", padx=5, pady=5)
        frame_progress.pack(fill="both", expand=True, padx=10, pady=5)

        self.progress = ttk.Progressbar(frame_progress, orient="horizontal", mode="indeterminate")
        self.progress.pack(fill="x", pady=5)

        self.log_text = tk.Text(frame_progress, height=8, wrap="word")
        self.log_text.pack(fill="both", expand=True)

        self.btn_execute = tk.Button(self.root, text="▶ Extraer frames", command=self.start_extraction, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.btn_execute.pack(pady=10)

    def select_video(self):
        path = filedialog.askopenfilename(filetypes=[("Archivos de video", "*.mp4 *.mov *.avi *.mkv *.webm *.insv")])
        if path:
            self.video_path.set(path)

    def select_output_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir.set(directory)

    # --- CORRECCIÓN DE HILOS (THREAD-SAFE LOGGING) ---
    def log(self, message):
        # Delega la actualización de la interfaz al hilo principal usando 'after'
        self.root.after(0, self._safe_log, message)

    def _safe_log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    # -------------------------------------------------

    def start_extraction(self):
        if not self.video_path.get() or not self.output_dir.get():
            messagebox.showerror("Error", "Selecciona video y destino.")
            return

        self.btn_execute.config(state="disabled", text="Extrayendo...")
        self.log_text.delete(1.0, tk.END)
        self.progress.start(10)

        threading.Thread(target=self.run_ffmpeg, daemon=True).start()

    def run_ffmpeg(self):
        video = self.video_path.get()
        out_dir = self.output_dir.get()
        start = self.start_time.get()
        interval = self.interval.get()
        ext = self.format.get()

        fps_filter = f"fps=1/{interval}"
        temp_pattern = os.path.join(out_dir, f"temp_frame_%06d.{ext}")

        # Configuración de máxima calidad: -q:v 2 para JPEG es excelente. PNG es lossless por defecto.
        quality_args = ["-q:v", "2"] if ext == "jpg" else []

        # Comando optimizado: -ss antes de -i para búsqueda ultra rápida (Fast Seek)
        cmd = [
            './ffmpeg/ffmpeg.exe', '-y',
            '-ss', str(start),
            '-i', video,
            '-vf', fps_filter,
            *quality_args,
            temp_pattern
        ]

        self.log(f"Iniciando extracción rápida desde t={start}s, cada {interval}s...")
        
        try:
            # Ejecutamos ffmpeg de una sola vez
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Renombramos los archivos para ponerles los segundos exactos
            files = sorted(glob.glob(os.path.join(out_dir, f"temp_frame_*.{ext}")))
            for i, filepath in enumerate(files):
                actual_time = start + (i * interval)
                new_name = f"frame_{actual_time:.2f}s.{ext}"
                new_path = os.path.join(out_dir, new_name)
                
                # Manejo de errores básico por si el archivo está en uso
                try:
                    if os.path.exists(new_path):
                        os.remove(new_path)
                    os.rename(filepath, new_path)
                except Exception as e:
                    self.log(f"⚠️ Aviso al renombrar {filepath}: {str(e)}")
                
            self.log(f"✅ ¡Éxito! Se extrajeron {len(files)} frames en máxima calidad.")
            
        except subprocess.CalledProcessError as e:
            self.log("❌ Error durante la extracción de ffmpeg.")
            self.log(e.stderr.decode('utf-8', errors='ignore'))
        
        finally:
            # Aseguramos que la UI vuelva a su estado original de forma segura
            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.btn_execute.config(state="normal", text="▶ Extraer frames"))

if __name__ == "__main__":
    root = tk.Tk()
    app = FrameExtractorApp(root)
    root.mainloop()