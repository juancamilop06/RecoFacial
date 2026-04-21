import os
import tempfile
import argparse
import cv2
from deepface import DeepFace
import webbrowser
import time
import subprocess
import sys
import urllib.request
import urllib.error
import numpy as np
import random
from datetime import datetime
from itertools import combinations

# ---------- CONFIGURACIÓN ----------
UMBRAL_MOVIMIENTO = 0.1  # Ajusta según pruebas (0.1 es estricto)
# ---------------------------------

try:
    from signature_server import run_server
except Exception:
    run_server = None


# ============================================================================
# FUNCIÓN DE VERIFICACIÓN ORIGINAL (NO TOCAR)
# ============================================================================
def verify_with_id(captured_path, id_path):
    try:
        if not os.path.exists(id_path):
            return {"error": f"No existe la imagen: {id_path}"}
        img = cv2.imread(id_path)
        if img is None:
            return {"error": "No se pudo leer la imagen de referencia"}

        result = DeepFace.verify(
            img1_path=captured_path,
            img2_path=id_path,
            model_name="ArcFace",
            detector_backend="retinaface",
            enforce_detection=False
        )
        return result
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# FUNCIONES PARA DETECCIÓN DE MOVIMIENTO (NO AFECTAN LA VERIFICACIÓN)
# ============================================================================
def compute_movement_score(frames, face_cascade):
    """Calcula la diferencia máxima entre cualquier par de frames (región del rostro)."""
    if len(frames) < 2:
        return 0.0, 0.0

    rois = []
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces) == 0:
            rois.append(gray)
        else:
            (x, y, w, h) = max(faces, key=lambda rect: rect[2] * rect[3])
            roi = gray[y:y+h, x:x+w]
            rois.append(roi)

    if len(rois) < 2:
        return 0.0, 0.0

    # Redimensionar todas al tamaño de la primera
    target_size = rois[0].shape
    rois_resized = []
    for roi in rois:
        if roi.shape != target_size:
            roi = cv2.resize(roi, (target_size[1], target_size[0]))
        rois_resized.append(roi)

    diffs = []
    for i, j in combinations(range(len(rois_resized)), 2):
        diff = cv2.absdiff(rois_resized[i], rois_resized[j])
        mean_diff = np.mean(diff) / 255.0
        diffs.append(mean_diff)

    max_diff = max(diffs) if diffs else 0.0
    mean_diff = np.mean(diffs) if diffs else 0.0
    return max_diff, mean_diff


def save_captured_frames(frames, folder="data/capturas", prefix="verif"):
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_paths = []
    for i, frame in enumerate(frames):
        path = os.path.join(folder, f"{timestamp}_{prefix}_{i+1}.jpg")
        cv2.imwrite(path, frame)
        saved_paths.append(path)
    return saved_paths


def save_log(result_info, log_path="data/resultado_firma.txt"):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        f.write(f"Semáforo: {result_info['semaforo']}\n")
        f.write(f"Score de movimiento (máx): {result_info['movement_max']:.4f}\n")
        f.write(f"Score de movimiento (prom): {result_info['movement_mean']:.4f}\n")
        f.write(f"Verificación con cédula: {result_info['verificacion']}\n")
        if 'distance' in result_info:
            f.write(f"Distancia facial: {result_info['distance']:.4f}\n")
        f.write(f"Mensaje: {result_info['mensaje']}\n")
        f.write("----------------------------------------\n")


# ============================================================================
# MAIN (CON FLUJO DE CÉDULA ORIGINAL + VERIFICACIÓN ACTIVA)
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description='Comparar rostro de cámara con foto guardada (con detección de vida activa)')
    parser.add_argument('--id', dest='id_path', default='data/id.jpg', help='Ruta de la imagen de referencia')
    args = parser.parse_args()
    id_path = args.id_path

    print("Flujo: captura cédula -> verificación activa con movimientos guiados.")
    print(f"Umbral de movimiento: {UMBRAL_MOVIMIENTO} (>= movimiento detectado)")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("No se pudo abrir la cámara.")
        return

    # No reducir resolución (se mantiene calidad original)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    print("\nPresiona:")
    print("SPACE -> capturar / siguiente paso")
    print("Q o ESC -> salir\n")

    mode = 'capture_id'  # 'capture_id' o 'verify'

    acciones = [
        "Mira hacia la IZQUIERDA",
        "Mira hacia la DERECHA",
        "SONRÍE ampliamente",
        "Abre los OJOS bien grandes",
        "Inclina la cabeza hacia ARRIBA",
        "Inclina la cabeza hacia ABAJO"
    ]

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error leyendo cámara")
            break

        h, w = frame.shape[:2]

        if mode == 'capture_id':
            instr = 'Alinea la CEDULA: sitúa la FOTO dentro del marco. SPACE->tomar CEDULA'
        else:
            instr = 'Verificación activa: sigue instrucciones y presiona SPACE para cada foto'

        cv2.putText(frame, instr, (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        if mode == 'capture_id':
            card_w = int(w * 0.9)
            card_h = int(h * 0.55)
            card_x = int((w - card_w) / 2)
            card_y = int((h - card_h) / 2)
            cv2.rectangle(frame, (card_x, card_y), (card_x + card_w, card_y + card_h), (0, 255, 0), 2)
            photo_w = int(card_w * 0.25)
            photo_h = int(card_h * 0.84)
            photo_x = card_x + int(card_w * 0.04)
            photo_y = card_y + int((card_h - photo_h) / 2)
            cv2.rectangle(frame, (photo_x, photo_y), (photo_x + photo_w, photo_y + photo_h), (0, 255, 0), 2)

        cv2.imshow("Camara", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == 27 or key == ord('q'):
            break

        if key == 32:
            print('SPACE detectado')

            # ---------- MODO CAPTURA CÉDULA (ORIGINAL) ----------
            if mode == 'capture_id':
                os.makedirs('data', exist_ok=True)
                full_path = os.path.join('data', 'id_full.jpg')
                face_path = os.path.join('data', 'id_face.jpg')
                cv2.imwrite(full_path, frame)

                # Recortar la foto de la cédula (igual que original)
                card_w = int(w * 0.905)
                card_h = int(h * 0.555)
                card_x = int((w - card_w) / 2)
                card_y = int((h - card_h) / 2)
                photo_w = int(card_w * 0.25)
                photo_h = int(card_h * 0.84)
                photo_x = card_x + int(card_w * 0.04)
                photo_y = card_y + int((card_h - photo_h) / 2)

                cropped = frame[photo_y:photo_y + photo_h, photo_x:photo_x + photo_w]
                if cropped is None or cropped.size == 0:
                    print('Error: no se pudo recortar la foto de la cédula.')
                else:
                    cv2.imwrite(face_path, cropped)
                    print(f'Cédula guardada en {full_path}, recorte en {face_path}')
                    id_path = face_path
                    mode = 'verify'
                    print("Modo verificación activa. Realiza los movimientos indicados y presiona SPACE para cada foto.")
                continue

            # ---------- MODO VERIFICACIÓN ACTIVA (con movimientos) ----------
            # 1. Tomar 4 fotos con acciones aleatorias
            num_acciones = 4
            acciones_elegidas = random.sample(acciones, num_acciones)
            fotos_movimiento = []

            for i, accion in enumerate(acciones_elegidas):
                esperando = True
                while esperando:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    cv2.putText(frame, f"PASO {i+1}/{num_acciones}: {accion}", (30, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
                    cv2.putText(frame, "Presiona SPACE para capturar", (30, 100),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.imshow("Camara", frame)
                    k = cv2.waitKey(1) & 0xFF
                    if k == 32:
                        fotos_movimiento.append(frame.copy())
                        print(f"Capturada: {accion}")
                        time.sleep(0.3)
                        esperando = False
                        break
                    elif k == 27 or k == ord('q'):
                        cap.release()
                        cv2.destroyAllWindows()
                        return

            # 2. Tomar foto final neutral
            esperando = True
            while esperando:
                ret, frame = cap.read()
                if not ret:
                    break
                cv2.putText(frame, "FOTO FINAL: Rostro NEUTRO (sin movimientos)", (30, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(frame, "Presiona SPACE para capturar (se usará para verificación)", (30, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.imshow("Camara", frame)
                k = cv2.waitKey(1) & 0xFF
                if k == 32:
                    foto_final = frame.copy()
                    print("Capturada foto final.")
                    time.sleep(0.3)
                    esperando = False
                    break
                elif k == 27 or k == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    return

            # Guardar todas las fotos (movimientos + final)
            todas_fotos = fotos_movimiento + [foto_final]
            save_captured_frames(todas_fotos, folder="data/capturas", prefix="verif")
            print(f"Guardadas {len(todas_fotos)} fotos en data/capturas/")

            # Calcular movimiento (máxima diferencia entre fotos de movimiento)
            max_movement, mean_movement = compute_movement_score(fotos_movimiento, face_cascade)
            hay_movimiento = max_movement >= UMBRAL_MOVIMIENTO

            # Verificar foto final contra cédula usando la función ORIGINAL
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
            os.close(tmp_fd)
            cv2.imwrite(tmp_path, foto_final)

            print("\nVerificando rostro con cédula...")
            result = verify_with_id(tmp_path, id_path)   # <--- FUNCIÓN ORIGINAL

            # Determinar semáforo según resultado
            if "error" in result:
                print("Error en verificación:", result["error"])
                msg = "ERROR EN VERIFICACIÓN"
                color = (0, 0, 255)
                semaforo = "ROJO (Error)"
                verificacion_ok = False
                distance = None
            else:
                verified = result["verified"]
                distance = result["distance"]
                verificacion_ok = verified
                print(f"Resultado DeepFace: verified={verified}, distance={distance:.4f}")

                if verified and hay_movimiento:
                    semaforo = "VERDE (Match + Movimiento)"
                    msg = f"MATCH ✔ (Movimiento OK) dist={distance:.3f}"
                    color = (0, 255, 0)
                elif verified and not hay_movimiento:
                    semaforo = "AMARILLO (Match + Sin movimiento)"
                    msg = f"MATCH ✔ (POSIBLE FRAUDE) dist={distance:.3f}"
                    color = (0, 255, 255)
                else:  # no verified
                    semaforo = "ROJO (No Match)"
                    msg = f"NO MATCH ✖ dist={distance:.3f}"
                    color = (0, 0, 255)

            print(f"Semáforo: {semaforo}")

            # Mostrar resultado en pantalla
            display = foto_final.copy()
            cv2.putText(display, msg, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
            cv2.imshow("Resultado", display)
            cv2.waitKey(2500)
            cv2.destroyWindow("Resultado")

            # Guardar log
            result_info = {
                "semaforo": semaforo,
                "movement_max": max_movement,
                "movement_mean": mean_movement,
                "verificacion": "MATCH" if verificacion_ok else "NO MATCH",
                "mensaje": msg,
            }
            if distance is not None:
                result_info["distance"] = distance
            save_log(result_info)
            print("Log guardado en data/resultado_firma.txt")

            # Decidir si abrir la firma (solo si hay MATCH, es decir, VERDE o AMARILLO)
            if verificacion_ok:
                # Liberar cámara y ventanas
                cap.release()
                cv2.destroyAllWindows()

                # Iniciar servidor de firma (igual que original)
                try:
                    sig_path = os.path.join(os.path.dirname(__file__), 'signature_server.py')
                    if not os.path.exists(sig_path):
                        print("No se encontró signature_server.py. Coloca el archivo en el proyecto.")
                    else:
                        python = sys.executable or 'python'
                        proc = subprocess.Popen([python, sig_path], cwd=os.path.dirname(__file__),
                                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        url = 'http://127.0.0.1:5000/signature'
                        connected = False
                        for _ in range(30):
                            try:
                                with urllib.request.urlopen(url, timeout=1) as resp:
                                    if resp.status == 200:
                                        connected = True
                                        break
                            except Exception:
                                time.sleep(0.3)
                        if connected:
                            webbrowser.open(url)
                            print("Interfaz de firma abierta en el navegador.")
                            if not hay_movimiento and verified:
                                print("NOTA: Semáforo AMARILLO. Posible fraude. La firma será revisada.")
                        else:
                            print("No se pudo conectar al servidor de firma.")
                except Exception as e:
                    print("Error al iniciar servidor de firma:", e)
                break  # salir del bucle principal
            else:
                print("Verificación fallida (Semáforo ROJO). No se abrirá la firma. Presiona SPACE para reintentar.")
                try:
                    os.remove(tmp_path)
                except:
                    pass
                # Continuamos en modo verify para reintentar
                continue

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()