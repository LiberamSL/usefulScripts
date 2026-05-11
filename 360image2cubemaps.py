import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Listbox, MULTIPLE, END
import subprocess
import os
import sys
import shutil

class Split360App:
    def __init__(self, root):
        self.root = root
        self.root.title("Split360Images GUI - Lote (Organización por Caras)")
        self.root.geometry("750x700")

        # Variables
        self.image_list = []         # lista de rutas de imágenes
        self.output_dir = tk.StringVar()
        self.out_sfm_pattern = tk.StringVar(value="")
        self.split_mode = tk.StringVar(value="equirectangular")
        self.equi_splits = tk.IntVar(value=6)
        self.split_res = tk.IntVar(value=2560)
        self.fov = tk.IntVar(value=110)
        self.dual_offset_x = tk.StringVar(value="center")
        self.dual_offset_y = tk.StringVar(value="center")
        self.dual_model = tk.StringVar(value="fisheye4")
        self.extension = tk.StringVar(value="")

        # Rutas ejecutable y entorno
        
        # Averiguar la ruta real y absoluta donde está guardado este script .py
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Construir las rutas absolutas uniendo las carpetas
        self.exe_path = os.path.join(script_dir, "Meshroom", "aliceVision", "bin", "aliceVision_split360Images.exe")
        self.root_env = os.path.join(script_dir, "Meshroom", "aliceVision")

        self.create_widgets()

    def create_widgets(self):
        # ========== SECCIÓN IMÁGENES ==========
        frame_images = tk.LabelFrame(self.root, text="Imágenes a procesar", padx=5, pady=5)
        frame_images.pack(fill="both", expand=True, padx=10, pady=5)

        self.listbox = Listbox(frame_images, selectmode=MULTIPLE, height=6)
        self.listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(frame_images, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        btn_frame = tk.Frame(frame_images)
        btn_frame.pack(side="top", fill="x", pady=5)
        tk.Button(btn_frame, text="Añadir imágenes...", command=self.add_images).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Eliminar seleccionadas", command=self.remove_selected).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Limpiar lista", command=self.clear_list).pack(side="left", padx=5)

        # ========== CARPETA DE SALIDA ==========
        frame_output = tk.LabelFrame(self.root, text="Carpeta de salida (raíz)", padx=5, pady=5)
        frame_output.pack(fill="x", padx=10, pady=5)
        tk.Entry(frame_output, textvariable=self.output_dir, width=60).pack(side="left", padx=5)
        tk.Button(frame_output, text="Examinar...", command=self.browse_output).pack(side="left", padx=5)

        # ========== PARÁMETROS ==========
        frame_opts = tk.LabelFrame(self.root, text="Parámetros de división", padx=5, pady=5)
        frame_opts.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_opts, text="Split mode:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        tk.Radiobutton(frame_opts, text="Equirectangular", variable=self.split_mode, value="equirectangular", command=self.update_mode).grid(row=0, column=1, sticky="w")
        tk.Radiobutton(frame_opts, text="Dual-fisheye", variable=self.split_mode, value="dualfisheye", command=self.update_mode).grid(row=0, column=2, sticky="w")

        self.frame_equi = tk.LabelFrame(frame_opts, text="Equirectangular")
        self.frame_equi.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        tk.Label(self.frame_equi, text="Número de splits:").grid(row=0, column=0, sticky="e", padx=5)
        tk.Scale(self.frame_equi, from_=2, to=12, orient="horizontal", variable=self.equi_splits).grid(row=0, column=1, sticky="w")
        tk.Label(self.frame_equi, text="Resolución split (px):").grid(row=1, column=0, sticky="e", padx=5)
        tk.Entry(self.frame_equi, textvariable=self.split_res, width=10).grid(row=1, column=1, sticky="w")

        self.frame_dual = tk.LabelFrame(frame_opts, text="Dual-fisheye")
        self.frame_dual.grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        tk.Label(self.frame_dual, text="Offset X:").grid(row=0, column=0, sticky="e", padx=5)
        tk.OptionMenu(self.frame_dual, self.dual_offset_x, "left", "center", "right").grid(row=0, column=1, sticky="w")
        tk.Label(self.frame_dual, text="Offset Y:").grid(row=1, column=0, sticky="e", padx=5)
        tk.OptionMenu(self.frame_dual, self.dual_offset_y, "top", "center", "bottom").grid(row=1, column=1, sticky="w")
        tk.Label(self.frame_dual, text="Modelo cámara:").grid(row=2, column=0, sticky="e", padx=5)
        tk.OptionMenu(self.frame_dual, self.dual_model, "fisheye4", "equidistant_r3").grid(row=2, column=1, sticky="w")

        frame_common = tk.Frame(frame_opts)
        frame_common.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        tk.Label(frame_common, text="Campo de visión (FOV) °:").pack(side="left", padx=5)
        tk.Entry(frame_common, textvariable=self.fov, width=6).pack(side="left")
        tk.Label(frame_common, text="Extensión salida (vacío = igual que entrada):").pack(side="left", padx=5)
        tk.Entry(frame_common, textvariable=self.extension, width=8).pack(side="left")

        self.update_mode()

        self.btn_run = tk.Button(self.root, text="Ejecutar proceso por lotes", command=self.run_batch, bg="lightblue", font=("Arial", 12))
        self.btn_run.pack(pady=10)

        self.output_text = scrolledtext.ScrolledText(self.root, height=15, width=80, wrap=tk.WORD)
        self.output_text.pack(padx=10, pady=5, fill="both", expand=True)

    def add_images(self):
        files = filedialog.askopenfilenames(
            title="Seleccionar una o más imágenes",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.tif *.bmp"), ("All files", "*.*")]
        )
        for f in files:
            if f not in self.image_list:
                self.image_list.append(f)
                self.listbox.insert(END, os.path.basename(f) + "  (" + f + ")")
        self.log_message(f"Se añadieron {len(files)} imágenes. Total: {len(self.image_list)}")

    def remove_selected(self):
        selected = self.listbox.curselection()
        for idx in reversed(selected):
            del self.image_list[idx]
            self.listbox.delete(idx)
        self.log_message(f"Eliminadas {len(selected)} imágenes. Restantes: {len(self.image_list)}")

    def clear_list(self):
        self.image_list.clear()
        self.listbox.delete(0, END)
        self.log_message("Lista de imágenes vaciada.")

    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir.set(folder)

    def update_mode(self):
        if self.split_mode.get() == "equirectangular":
            self.frame_equi.grid()
            self.frame_dual.grid_remove()
        else:
            self.frame_equi.grid_remove()
            self.frame_dual.grid()

    def log_message(self, msg):
        self.output_text.insert(tk.END, msg + "\n")
        self.output_text.see(tk.END)
        self.root.update()

    def run_batch(self):
        if not self.image_list:
            messagebox.showerror("Error", "No hay imágenes seleccionadas.")
            return
        if not self.output_dir.get():
            messagebox.showerror("Error", "Selecciona una carpeta de salida raíz.")
            return
        if not os.path.exists(self.output_dir.get()):
            try:
                os.makedirs(self.output_dir.get())
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta de salida: {e}")
                return

        self.log_message("=== INICIO DEL PROCESO POR LOTES ===")
        total = len(self.image_list)
        success = 0
        errors = []

        for idx, img_path in enumerate(self.image_list, 1):
            self.log_message(f"\n--- Procesando imagen {idx}/{total}: {os.path.basename(img_path)} ---")

            base_name = os.path.splitext(os.path.basename(img_path))[0]
            # Carpeta de trabajo temporal para AliceVision
            out_subfolder = os.path.join(self.output_dir.get(), f"_temp_{base_name}")
            os.makedirs(out_subfolder, exist_ok=True)

            out_sfm_path = os.path.join(out_subfolder, base_name + ".sfm")

            cmd = [
                self.exe_path,
                "-i", img_path,
                "-o", out_subfolder,
                "--outSfMData", out_sfm_path,
                "--splitMode", self.split_mode.get(),
                "--fov", str(self.fov.get())
            ]

            if self.split_mode.get() == "equirectangular":
                cmd.extend(["--equirectangularNbSplits", str(self.equi_splits.get())])
                cmd.extend(["--equirectangularSplitResolution", str(self.split_res.get())])
            else:
                cmd.extend(["--dualFisheyeOffsetPresetX", self.dual_offset_x.get()])
                cmd.extend(["--dualFisheyeOffsetPresetY", self.dual_offset_y.get()])
                cmd.extend(["--dualFisheyeCameraModel", self.dual_model.get()])

            if self.extension.get().strip():
                cmd.extend(["--extension", self.extension.get().strip()])

            env = os.environ.copy()
            env["ALICEVISION_ROOT"] = self.root_env

            self.log_message("Comando en ejecución...")

            try:
                process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in process.stdout:
                    pass # Ocultamos los logs internos de meshroom para no saturar la UI, si los quieres, descomenta la linea de abajo
                    # self.log_message(line.rstrip())
                process.wait()
                
                if process.returncode == 0:
                    self.log_message(f"✅ División completada. Organizando caras...")
                    
                    # --- NUEVO CÓDIGO: DISTRIBUCIÓN POR CARAS/CUBOS ---
                    try:
                        imagenes_generadas = []
                        # 1. Buscar todas las imágenes en la subcarpeta temporal
                        for root_dir, dirs, files in os.walk(out_subfolder):
                            for file_name in files:
                                if file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.exr', '.tif', '.bmp')):
                                    imagenes_generadas.append(os.path.join(root_dir, file_name))
                        
                        # 2. Ordenarlas alfabéticamente para mantener la coherencia de las caras (0, 1, 2, 3...)
                        imagenes_generadas.sort()

                        # 3. Mover a su respectiva carpeta
                        for idx_cubo, old_path in enumerate(imagenes_generadas):
                            # Crea carpetas llamadas Cubo_1, Cubo_2, Cubo_3, etc. en el directorio raíz
                            carpeta_cubo = os.path.join(self.output_dir.get(), f"Cubo_{idx_cubo + 1}")
                            os.makedirs(carpeta_cubo, exist_ok=True)

                            # Nombramos el archivo igual que el panorama original para la secuencia
                            ext = os.path.splitext(old_path)[1]
                            new_name = f"{base_name}{ext}" 
                            new_path = os.path.join(carpeta_cubo, new_name)

                            shutil.move(old_path, new_path)
                        
                        # 4. Eliminar toda la estructura temporal sobrante
                        shutil.rmtree(out_subfolder)
                        self.log_message(f"  -> {len(imagenes_generadas)} imágenes movidas a sus respectivas carpetas 'Cubo_X'.")
                        success += 1
                        
                    except Exception as ex:
                        error_msg = f"❌ Error al organizar los cubos de {base_name}: {str(ex)}"
                        self.log_message(error_msg)
                        errors.append((img_path, error_msg))
                    # --------------------------------------------------
                else:
                    error_msg = f"❌ Error en {os.path.basename(img_path)} (código {process.returncode})"
                    self.log_message(error_msg)
                    errors.append((img_path, error_msg))
            except Exception as e:
                error_msg = f"❌ Excepción en {os.path.basename(img_path)}: {str(e)}"
                self.log_message(error_msg)
                errors.append((img_path, error_msg))

        self.log_message("\n=== RESUMEN ===")
        self.log_message(f"Procesadas: {total}, Exitosas: {success}, Fallidas: {len(errors)}")
        if errors:
            self.log_message("Imágenes con error:")
            for img, err in errors:
                self.log_message(f"  - {img}: {err}")

        if success == total:
            messagebox.showinfo("Completado", f"Todas las imágenes ({total}) se procesaron y organizaron por Cubos correctamente.")
        else:
            messagebox.showwarning("Atención", f"Se completó con {success} éxitos y {len(errors)} errores. Revisa los logs.")

if __name__ == "__main__":
    root = tk.Tk()
    app = Split360App(root)
    root.mainloop()