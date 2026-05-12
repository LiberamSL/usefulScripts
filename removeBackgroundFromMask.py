import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import scrolledtext
import cv2
import numpy as np
import os
from pathlib import Path
import threading

class MaskApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Recorte de Texturas para Fotogrametría")
        self.root.geometry("600x450")
        self.root.resizable(False, False)

        # Variables de ruta
        self.var_texturas = tk.StringVar()
        self.var_mascaras = tk.StringVar()
        self.var_salida = tk.StringVar()
        self.var_sufijo = tk.StringVar(value="") # Por si las máscaras tienen sufijo ej: "_mask"

        self.crear_interfaz()

    def crear_interfaz(self):
        # --- Marco de Selección de Carpetas ---
        frame_rutas = tk.LabelFrame(self.root, text="Configuración de Carpetas", padx=10, pady=10)
        frame_rutas.pack(padx=10, pady=10, fill="x")

        # Texturas
        tk.Label(frame_rutas, text="1. Texturas (Originales):").grid(row=0, column=0, sticky="w", pady=5)
        tk.Entry(frame_rutas, textvariable=self.var_texturas, width=40, state="readonly").grid(row=0, column=1, padx=5)
        tk.Button(frame_rutas, text="Explorar...", command=lambda: self.seleccionar_carpeta(self.var_texturas)).grid(row=0, column=2)

        # Máscaras
        tk.Label(frame_rutas, text="2. Máscaras:").grid(row=1, column=0, sticky="w", pady=5)
        tk.Entry(frame_rutas, textvariable=self.var_mascaras, width=40, state="readonly").grid(row=1, column=1, padx=5)
        tk.Button(frame_rutas, text="Explorar...", command=lambda: self.seleccionar_carpeta(self.var_mascaras)).grid(row=1, column=2)

        # Salida
        tk.Label(frame_rutas, text="3. Carpeta de Salida:").grid(row=2, column=0, sticky="w", pady=5)
        tk.Entry(frame_rutas, textvariable=self.var_salida, width=40, state="readonly").grid(row=2, column=1, padx=5)
        tk.Button(frame_rutas, text="Explorar...", command=lambda: self.seleccionar_carpeta(self.var_salida)).grid(row=2, column=2)

        # Sufijo
        tk.Label(frame_rutas, text="Sufijo máscara (opcional):").grid(row=3, column=0, sticky="w", pady=5)
        tk.Entry(frame_rutas, textvariable=self.var_sufijo, width=15).grid(row=3, column=1, sticky="w", padx=5)
        tk.Label(frame_rutas, text="Ej: '_mask' si el archivo es foto_01_mask.png", fg="gray").grid(row=3, column=1, sticky="e")

        # --- Botón de Procesar ---
        self.btn_procesar = tk.Button(self.root, text="🚀 INICIAR PROCESAMIENTO", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=self.iniciar_hilo)
        self.btn_procesar.pack(pady=10)

        # --- Consola de Log ---
        self.log_area = scrolledtext.ScrolledText(self.root, width=70, height=10, state='disabled', bg="#f4f4f4")
        self.log_area.pack(padx=10, pady=5)

    def seleccionar_carpeta(self, variable):
        carpeta = filedialog.askdirectory()
        if carpeta:
            variable.set(carpeta)

    def registrar_log(self, mensaje):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, mensaje + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def iniciar_hilo(self):
        if not all([self.var_texturas.get(), self.var_mascaras.get(), self.var_salida.get()]):
            messagebox.showwarning("Faltan datos", "Por favor, selecciona las tres carpetas antes de continuar.")
            return

        self.btn_procesar.config(state="disabled", text="PROCESANDO...")
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')
        
        # Ejecutar en segundo plano para no congelar la GUI
        hilo = threading.Thread(target=self.procesar_imagenes)
        hilo.start()

    def procesar_imagenes(self):
        ruta_tex = self.var_texturas.get()
        ruta_mask = self.var_mascaras.get()
        ruta_out = self.var_salida.get()
        sufijo = self.var_sufijo.get()

        exts = ('.jpg', '.jpeg', '.png', '.tiff')
        archivos = [f for f in os.listdir(ruta_tex) if f.lower().endswith(exts)]
        
        if not archivos:
            self.registrar_log("❌ No se encontraron imágenes en la carpeta de texturas.")
            self.finalizar_proceso()
            return

        self.registrar_log(f"Iniciando: {len(archivos)} imágenes encontradas...\n" + "-"*40)

        procesadas = 0
        errores = 0

        for archivo in archivos:
            path_img = os.path.join(ruta_tex, archivo)
            nombre_base = Path(archivo).stem
            
            # Buscar máscara (probando PNG primero, luego JPG)
            nombre_mascara = f"{nombre_base}{sufijo}"
            path_mask = os.path.join(ruta_mask, f"{nombre_mascara}.png")
            
            if not os.path.exists(path_mask):
                path_mask = os.path.join(ruta_mask, f"{nombre_mascara}.jpg")

            if os.path.exists(path_mask):
                try:
                    # Cargar textura
                    img = cv2.imread(path_img)
                    
                    # Cargar máscara con canal Alpha si existe (IMREAD_UNCHANGED)
                    mask_img = cv2.imread(path_mask, cv2.IMREAD_UNCHANGED)
                    
                    # Extraer el canal que define la forma de la máscara
                    if len(mask_img.shape) == 3 and mask_img.shape[2] == 4:
                        # Tiene canal Alpha (Transparencia)
                        mask_canal = mask_img[:, :, 3] 
                    else:
                        # Es RGB o Grayscale puro
                        if len(mask_img.shape) == 3:
                            mask_canal = cv2.cvtColor(mask_img, cv2.COLOR_BGR2GRAY)
                        else:
                            mask_canal = mask_img

                    # Redimensionar si hay discrepancia de tamaños
                    if img.shape[:2] != mask_canal.shape[:2]:
                        mask_canal = cv2.resize(mask_canal, (img.shape[1], img.shape[0]))

                    # Fusionar
                    b, g, r = cv2.split(img)
                    rgba = [b, g, r, mask_canal]
                    img_final = cv2.merge(rgba)

                    # Guardar
                    cv2.imwrite(os.path.join(ruta_out, f"{nombre_base}_masked.png"), img_final)
                    self.registrar_log(f"✅ Procesado: {archivo}")
                    procesadas += 1

                except Exception as e:
                    self.registrar_log(f"❌ Error con {archivo}: {str(e)}")
                    errores += 1
            else:
                self.registrar_log(f"⚠️ Salto: No se encontró máscara para {archivo}")
                errores += 1

        self.registrar_log("-" * 40)
        self.registrar_log(f"🎉 PROCESO FINALIZADO. Éxitos: {procesadas} | Errores/Saltos: {errores}")
        self.finalizar_proceso()

    def finalizar_proceso(self):
        # Devolver el botón a su estado original de forma segura
        self.root.after(0, lambda: self.btn_procesar.config(state="normal", text="🚀 INICIAR PROCESAMIENTO", bg="#4CAF50"))

if __name__ == "__main__":
    root = tk.Tk()
    app = MaskApp(root)
    root.mainloop()