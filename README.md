# Face Verification con DeepFace + ArcFace

Este proyecto permite verificar si el rostro capturado por la cámara coincide con una foto de referencia usando inteligencia artificial.

El sistema usa DeepFace, un framework de reconocimiento facial basado en redes neuronales profundas.

---

# Qué hace el programa

El programa:

1. Abre la cámara de tu computadora
2. Muestra la imagen en tiempo real
3. Cuando presionas SPACE toma una foto
4. Compara esa foto con una imagen de referencia
5. Determina si es la misma persona o no

Resultado posible:

MATCH ✔

o

NO MATCH ✖

---

# Cómo funciona el reconocimiento facial

El sistema usa un modelo de inteligencia artificial llamado ArcFace.

El proceso general es:

Imagen → detectar rostro → convertir rostro en números → comparar números

---

# Paso 1 — Detectar el rostro

Se usa RetinaFace para encontrar el rostro dentro de la imagen.

La imagen original puede tener fondo, objetos, etc.
El detector recorta solo la cara.

---

# Paso 2 — Normalizar la cara

La cara se alinea para que todas las imágenes tengan:

- ojos a la misma altura
- rostro centrado
- tamaño estandarizado

Esto mejora la precisión del reconocimiento.

---

# Paso 3 — Convertir la cara en un vector

El modelo ArcFace convierte la cara en un vector de números llamado embedding facial.

Ejemplo simplificado:

[0.23, -0.44, 0.77, 0.12, ...]

Estos vectores normalmente tienen 512 números.

Cada número representa características faciales aprendidas por la red neuronal.

---

# Paso 4 — Comparar vectores

Luego el sistema calcula una distancia matemática entre vectores.

Ejemplo:

vector cara 1
vector cara 2

Se calcula la distancia:

distance = 0.31

Interpretación:

distancia pequeña → misma persona  
distancia grande → persona diferente

Ejemplo típico:

0.25 → MATCH  
0.60 → NO MATCH

---

# Qué es una red neuronal

Una red neuronal es un modelo de inteligencia artificial inspirado en el cerebro humano.

Está formada por muchas neuronas artificiales conectadas entre sí.

Estructura simplificada:

Entrada → capas ocultas → salida

Cada neurona realiza cálculos matemáticos sobre los datos.

Durante el entrenamiento la red aprende patrones viendo millones de ejemplos.

---

# Qué es ArcFace

ArcFace es un modelo de reconocimiento facial basado en deep learning.

Características:

- convierte rostros en vectores matemáticos
- usa distancia angular entre vectores
- tiene precisión muy alta (~99%)

ArcFace fue entrenado con millones de rostros para aprender a separar identidades.

---

# Requisitos

Python 3.9 o 3.10  
Webcam  
Windows / Linux / Mac

---

# Estructura del proyecto

PMC/

verify.py  
requirements.txt  
data/  
id.jpg  
README.md

La imagen data/id.jpg es la foto de referencia.

---

# Crear el entorno virtual

Ir a la carpeta del proyecto:

```
cd D:\PMC
```

Crear entorno virtual:

```
python -m venv .venv
```

Activar entorno virtual:

```
.venv\Scripts\activate
```

Si está activo verás algo así:

```
(.venv) PS D:\PMC>
```

---

# Instalar dependencias

```
pip install -r requirements.txt
```

---

# Colocar imagen de referencia

Crear carpeta:

```
data
```

Dentro colocar:

```
data/id.jpg
```

Esta será la foto que el sistema usará para comparar.

---

# Ejecutar el programa

Ejecutar:

```
python verify.py
```

La cámara se abrirá.

Controles:

SPACE → capturar y verificar rostro  
Q → salir  
ESC → salir  

---

# Ejemplo de uso

1. Coloca tu foto en data/id.jpg
2. Ejecuta el programa
3. Mira a la cámara
4. Presiona SPACE

Resultado posible:

MATCH ✔ dist=0.32

o

NO MATCH ✖ dist=0.65

---

# Problemas comunes

Error protobuf

Solución:

```
pip install protobuf==3.20.3
```

---

No se abre la cámara

Verifica que ninguna otra aplicación esté usando la webcam.

---

Espacio en disco insuficiente

TensorFlow es grande (~500MB).
Asegúrate de tener al menos 3GB libres.

---

# Librerías usadas

DeepFace → framework de reconocimiento facial  
TensorFlow → motor de redes neuronales  
OpenCV → manejo de cámara e imágenes  
RetinaFace → detector de rostros  
ArcFace → modelo de reconocimiento facial

---

# Licencia

Proyecto educativo.