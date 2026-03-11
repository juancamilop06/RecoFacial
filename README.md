# Demo: verificación facial contra foto de cédula

Descripción rápida: este demo captura una foto desde la cámara y la compara con una imagen de tu cédula (por defecto `data/id.jpg`) usando DeepFace.

IMPORTANTE — compatibilidad de versiones

- DeepFace y sus dependencias (especialmente `tensorflow` y `numpy`) pueden generar errores si se usan versiones recientes incompatibles. Para evitar problemas conocidos, este proyecto fija las versiones recomendadas en `requirements.txt`.

Si ya instalaste TensorFlow/NumPy globalmente, ejecuta antes:

```powershell
pip uninstall tensorflow -y
pip uninstall numpy -y
```

Instala las versiones recomendadas manualmente (si no usas `requirements.txt`):

```powershell
pip install tensorflow==2.10.0
pip install numpy==1.23.5
pip install --upgrade deepface
pip install opencv-python
```

Instalación usando el `requirements.txt` (recomendado dentro de un `venv`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Preparar la imagen de la cédula

- Crea la carpeta `data` y coloca la foto de la cédula como `data/id.jpg`.
- O captura una con la webcam usando el helper:

```powershell
python capture_id.py
```

Cómo funciona y limitaciones

- DeepFace compara rasgos faciales entre dos fotos. Funciona mejor con fotos tipo "selfie" (rostro frontal, buena iluminación).
- Las fotos de cédula pueden fallar por: baja resolución, reflejos en el laminado, sellos/estampados, inclinación o elementos gráficos alrededor del rostro. Por eso puede dar falso negativo con la cédula pero positivo con una selfie.

Recomendaciones para mejorar resultados con la cédula

- Toma una foto frontal del documento con buena luz, sin sombras ni reflejos.
- Recorta la imagen para incluir sólo la región del rostro (sin bordes ni texto) antes de probar.

Uso (ejemplo)

```powershell
# crear y activar venv (opcional pero recomendado)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# capturar la foto de la cédula (opcional)
python capture_id.py

# ejecutar demo interactivo (presiona SPACE para capturar y comparar)
python verify.py
```

Controles dentro del demo:
- Presiona `SPACE` para capturar una foto desde la webcam y comparar con `data/id.jpg`.
- Presiona `q` o `ESC` para salir.

Notas finales:
- La primera ejecución puede tardar varios minutos mientras DeepFace descarga modelos pre-entrenados.
- Este repositorio es un demo local. Mantén tus imágenes privadas y no las subas a servicios externos sin revisar su política de privacidad.
