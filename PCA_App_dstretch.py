import streamlit as st
import numpy as np
from PIL import Image
import io
import os
import tkinter as tk
from tkinter import filedialog

# Intentar cargar rasterio para soporte SIG / GeoTIFF
try:
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.windows import Window
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

# Configuración de Streamlit
st.set_page_config(page_title="DStretch Archeo-Lab GIS", page_icon="🏛️", layout="wide")

st.title("🏛️ DStretch Archeo-Lab (Soporte GeoTIFF & GIS)")
st.markdown("Herramienta interactiva para el realce de pintura rupestre con soporte para ortofotos georreferenciadas.")

# Función para abrir el Explorador de Archivos nativo de Windows / Mac
def select_file_dialog():
    root = tk.Tk()
    root.withdraw()  # Ocultar la ventana principal de Tkinter
    root.attributes('-topmost', True)  # Traer la ventana al frente
    file_path = filedialog.askopenfilename(
        title="Selecciona la Ortofoto TIFF",
        filetypes=[("Archivos TIFF / GeoTIFF", "*.tif *.tiff"), ("Todos los archivos", "*.*")]
    )
    root.destroy()
    return file_path

# -------------------------------------------------------------
# ALGORITMO CORE DE DECORRELACIÓN (CON PRESETS DSTRETCH)
# -------------------------------------------------------------
def process_pixels(pixels, preset='YRD (Rojos/Ocres)', p_cut=1.0):
    if preset == 'YRD (Rojos/Ocres)':
        M_yrd = np.array([
            [0.299,  0.587,  0.114],  # Y
            [0.701, -0.587, -0.114],  # R - Y
            [-0.299, -0.587,  0.886]   # B - Y (D)
        ])
        all_trans = np.dot(pixels, M_yrd.T)
    elif preset == 'LAB (Luminosidad/Color)':
        L = 0.299 * pixels[:, 0] + 0.587 * pixels[:, 1] + 0.114 * pixels[:, 2]
        A = pixels[:, 0] - pixels[:, 1]
        B = pixels[:, 1] - pixels[:, 2]
        all_trans = np.column_stack([L, A, B])
    else:
        all_trans = pixels.copy()

    bg_mask = np.sum(pixels, axis=1) <= 15
    valid_mask = np.sum(pixels, axis=1) > 15
    
    clean_trans = all_trans[valid_mask] if np.sum(valid_mask) > 100 else all_trans

    mean = np.mean(clean_trans, axis=0)
    centered_clean = clean_trans - mean
    cov_matrix = np.cov(centered_clean.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
    stretch_matrix = np.diag(1.0 / np.sqrt(eigenvalues + 1e-5))

    centered_all = all_trans - mean
    pca_all = np.dot(centered_all, eigenvectors)
    str_pca_all = np.dot(pca_all, stretch_matrix)
    restored_all = np.dot(str_pca_all, eigenvectors.T) + mean

    pca_clean = np.dot(centered_clean, eigenvectors)
    str_pca_clean = np.dot(pca_clean, stretch_matrix)
    restored_clean = np.dot(str_pca_clean, eigenvectors.T) + mean

    p_low = np.percentile(restored_clean, p_cut, axis=0)
    p_high = np.percentile(restored_clean, 100.0 - p_cut, axis=0)

    res = (restored_all - p_low) / (p_high - p_low + 1e-5) * 255.0
    res = np.clip(res, 0, 255).astype(np.uint8)
    res[bg_mask] = [0, 0, 0]
    
    return res

# -------------------------------------------------------------
# INTERFAZ Y CONTROLADORES
# -------------------------------------------------------------
st.sidebar.header("⚙️ Ajustes de Procesamiento")

modo_carga = st.sidebar.radio(
    "Origen de la Imagen:",
    ["Subir Archivo (Navegador Web)", "Procesar Archivo Gigante (Explorador de Archivos)"]
)

preset = st.sidebar.selectbox(
    "Preset de Color (DStretch):",
    ["YRD (Rojos/Ocres)", "RGB (Estándar)", "LAB (Luminosidad/Color)"]
)

p_cut = st.sidebar.slider("Corte de Contraste (Percentil):", 0.1, 5.0, 1.0, 0.1)

# Variables de estado
is_geotiff = False
crs_info = None

# --- MODO 1: SUBIR ARCHIVO MEDIANTE EL NAVEGADOR ---
if modo_carga == "Subir Archivo (Navegador Web)":
    uploaded_file = st.sidebar.file_uploader(
        "Selecciona foto u ortofoto", 
        type=["jpg", "png", "jpeg", "tif", "tiff"]
    )
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        
        if HAS_RASTERIO and (uploaded_file.name.endswith('.tif') or uploaded_file.name.endswith('.tiff')):
            try:
                with MemoryFile(file_bytes) as memfile:
                    with memfile.open() as src:
                        if src.crs is not None:
                            is_geotiff = True
                            crs_info = str(src.crs)
                            st.sidebar.success(f"🗺️ GeoTIFF Detectado! CRS: {crs_info}")
            except Exception:
                is_geotiff = False

        if is_geotiff:
            with MemoryFile(file_bytes) as memfile:
                with memfile.open() as src:
                    W, H = src.width, src.height
                    data = src.read([1, 2, 3]).astype(np.float32)
                    pixels = np.moveaxis(data, 0, -1).reshape(-1, 3)
                    
                    res_pixels = process_pixels(pixels, preset=preset, p_cut=p_cut)
                    res_hwc = res_pixels.reshape(H, W, 3)
                    res_chw = np.moveaxis(res_hwc, -1, 0)
                    
                    profile = src.profile.copy()
                    profile.update(count=3, dtype='uint8', driver='GTiff', compress='lzw')
                    
                    out_memfile = MemoryFile()
                    with out_memfile.open(**profile) as dst:
                        dst.write(res_chw)
                    
                    geotiff_output_bytes = out_memfile.read()
                    
                    orig_hwc = np.moveaxis(data, 0, -1).astype(np.uint8)
                    original_preview = Image.fromarray(orig_hwc)
                    processed_preview = Image.fromarray(res_hwc)
        else:
            original_img = Image.open(io.BytesIO(file_bytes)).convert('RGB')
            arr = np.array(original_img, dtype=np.float32)
            H, W, C = arr.shape
            
            res_pixels = process_pixels(arr.reshape(-1, 3), preset=preset, p_cut=p_cut)
            
            original_preview = original_img
            processed_preview = Image.fromarray(res_pixels.reshape(H, W, 3))

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📷 Original")
            st.image(original_preview, use_container_width=True)
        with col2:
            st.subheader(f"🎨 Procesada ({preset})")
            st.image(processed_preview, use_container_width=True)

        st.markdown("---")
        if is_geotiff:
            st.download_button(
                label="🗺️ Descargar Ortofoto GeoTIFF (Con Coordenadas UTM)",
                data=geotiff_output_bytes,
                file_name=f"orto_dstretch_{preset.split()[0].lower()}.tif",
                mime="image/tiff"
            )
        else:
            buf = io.BytesIO()
            processed_preview.save(buf, format="PNG")
            st.download_button(
                label="📥 Descargar Imagen PNG Procesada",
                data=buf.getvalue(),
                file_name=f"foto_dstretch_{preset.split()[0].lower()}.png",
                mime="image/png"
            )

# --- MODO 2: NAVEGADOR DE ARCHIVOS DEL S.O. (PARA ARCHIVOS GIGANTES) ---
else:
    st.subheader("📁 Procesamiento de Ortofotas Gigantes (Directo desde Disco)")
    st.markdown("Utiliza el botón para abrir el explorador de archivos de tu ordenador y seleccionar la ortofoto TIFF.")
    
    # Inicializar variables en sesión de Streamlit
    if 'selected_file' not in st.session_state:
        st.session_state.selected_file = ""

    col_btn, col_path = st.columns([1, 3])
    
    with col_btn:
        st.write("") # Espaciador
        if st.button("📂 Buscar en mi PC"):
            path = select_file_dialog()
            if path:
                st.session_state.selected_file = path

    with col_path:
        path_input = st.text_input("Ruta del archivo seleccionado:", value=st.session_state.selected_file)

    if path_input:
        base, ext = os.path.splitext(path_input)
        default_out = f"{base}_dstretch{ext}"
        output_path_input = st.text_input("Ruta donde se guardará el resultado:", value=default_out)

        if st.button("🚀 Iniciar Procesamiento por Bloques"):
            if os.path.exists(path_input):
                if HAS_RASTERIO:
                    st.info("Iniciando procesamiento por franjas (bajo consumo de memoria RAM)...")
                    progress_bar = st.progress(0)
                    
                    with rasterio.open(path_input) as src:
                        W, H = src.width, src.height
                        st.write(f"📐 Dimensiones: **{W} x {H} píxeles** | CRS: **{src.crs}**")
                        
                        # Muestreo rápido para PCA
                        factor = max(1, int((W * H / 2_000_000) ** 0.5))
                        sample_data = src.read([1, 2, 3], out_shape=(3, H//factor, W//factor)).astype(np.float32)
                        sample_pixels = np.moveaxis(sample_data, 0, -1).reshape(-1, 3)
                        
                        valid_mask = np.sum(sample_pixels, axis=1) > 15
                        clean_pixels = sample_pixels[valid_mask] if np.sum(valid_mask) > 100 else sample_pixels
                        
                        mean = np.mean(clean_pixels, axis=0)
                        cov_matrix = np.cov((clean_pixels - mean).T)
                        eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
                        stretch_matrix = np.diag(1.0 / np.sqrt(eigenvalues + 1e-5))
                        
                        pca_s = np.dot(clean_pixels - mean, eigenvectors)
                        str_s = np.dot(pca_s, stretch_matrix)
                        rest_s = np.dot(str_s, eigenvectors.T) + mean
                        p_low = np.percentile(rest_s, p_cut, axis=0)
                        p_high = np.percentile(rest_s, 100.0 - p_cut, axis=0)
                        
                        profile = src.profile.copy()
                        profile.update(count=3, dtype='uint8', driver='GTiff', compress='lzw')
                        
                        block_height = 1000
                        with rasterio.open(output_path_input, 'w', **profile) as dst:
                            for y in range(0, H, block_height):
                                h_actual = min(block_height, H - y)
                                window = Window(0, y, W, h_actual)
                                
                                block_data = src.read([1, 2, 3], window=window).astype(np.float32)
                                block_hwc = np.moveaxis(block_data, 0, -1)
                                bg_mask = np.sum(block_hwc, axis=2) <= 15
                                
                                pix = block_hwc.reshape(-1, 3) - mean
                                pca_b = np.dot(pix, eigenvectors)
                                str_b = np.dot(pca_b, stretch_matrix)
                                res_b = np.dot(str_b, eigenvectors.T) + mean
                                
                                res_b = (res_b - p_low) / (p_high - p_low + 1e-5) * 255.0
                                res_b = np.clip(res_b, 0, 255).astype(np.uint8)
                                
                                res_hwc = res_b.reshape(h_actual, W, 3)
                                res_hwc[bg_mask] = [0, 0, 0]
                                
                                dst.write(np.moveaxis(res_hwc, -1, 0), window=window)
                                progress_bar.progress(min(1.0, (y + block_height) / H))
                    
                    st.success(f"🎉 ¡Proceso completado! Archivo GeoTIFF guardado en:\n`{output_path_input}`")
                else:
                    st.error("Necesitas instalar 'rasterio' (`pip install rasterio`) para procesar GeoTIFFs.")
            else:
                st.error(f"No se pudo encontrar el archivo en: {path_input}")