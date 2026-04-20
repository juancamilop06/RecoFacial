import os
import tempfile
import argparse
import cv2
from deepface import DeepFace
import threading
import webbrowser
import time
import subprocess
import sys
import urllib.request
import urllib.error
try:
    from signature_server import run_server
except Exception:
    run_server = None


def verify_with_id(captured_path, id_path):

    try:

        # verificar que la imagen exista
        if not os.path.exists(id_path):
            return {"error": f"No existe la imagen: {id_path}"}

        # verificar que se pueda leer
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


def main():

    parser = argparse.ArgumentParser(
        description='Comparar rostro de cámara con foto guardada'
    )

    parser.add_argument(
        '--id',
        dest='id_path',
        default='data/id.jpg',
        help='Ruta de la imagen de referencia'
    )

    args = parser.parse_args()
    id_path = args.id_path

    print("Flujo: primero captura la cédula, luego la verificación en vivo.")

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("No se pudo abrir la cámara.")
        return

    print("\nPresiona:")
    print("SPACE -> capturar y verificar")
    print("Q o ESC -> salir\n")

    mode = 'capture_id'  # other value: 'verify'

    while True:

        ret, frame = cap.read()

        if not ret:
            print("Error leyendo cámara")
            break

        h, w = frame.shape[:2]

        if mode == 'capture_id':
            instr = 'Alinea la CEDULA: sitúa la FOTO dentro del marco. SPACE->tomar CEDULA'
        else:
            instr = 'SPACE -> capturar y verificar rostro'

        cv2.putText(
            frame,
            instr,
            (10, h - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        # draw ID card guide when capturing ID (wide card and inner photo area)
        if mode == 'capture_id':
            card_w = int(w * 0.9)
            card_h = int(h * 0.55)
            card_x = int((w - card_w) / 2)
            card_y = int((h - card_h) / 2)
            cv2.rectangle(frame, (card_x, card_y), (card_x + card_w, card_y + card_h), (0, 255, 0), 2)
            # inner photo area on the left side of the card (portrait)
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

            # crear archivo temporal
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
            os.close(tmp_fd)

            cv2.imwrite(tmp_path, frame)

            if mode == 'capture_id':
                # save full id image and crop the photo area from the framed region
                os.makedirs('data', exist_ok=True)
                full_path = os.path.join('data', 'id_full.jpg')
                face_path = os.path.join('data', 'id_face.jpg')
                cv2.imwrite(full_path, frame)

                # compute same rectangles as drawn: card and inner photo area
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
                    print(f'Foto de cédula guardada en {full_path}, recorte guardado en {face_path}')
                    # switch to verification mode
                    id_path = face_path
                    mode = 'verify'
                    # give user feedback and continue loop
                    continue

            # otherwise in verify mode, perform verification
            print("\nImagen capturada. Verificando...")

            result = verify_with_id(tmp_path, id_path)

            if "error" in result:

                print("Error:", result["error"])

                msg = "ERROR"
                color = (0, 0, 255)

            else:

                verified = result["verified"]
                distance = result["distance"]

                print("Resultado completo:", result)

                if verified:

                    msg = f"MATCH ✔ dist={distance:.3f}"
                    color = (0, 255, 0)

                    # Liberar cámara y ventanas antes de iniciar servidor para que
                    # el navegador pueda usar la cámara.
                    try:
                        cap.release()
                        cv2.destroyAllWindows()
                    except Exception:
                        pass

                    # Start the signature server as a separate process and wait until it's ready
                    try:
                        sig_path = os.path.join(os.path.dirname(__file__), 'signature_server.py')
                        if not os.path.exists(sig_path):
                            print("No se encontró signature_server.py. Coloca el archivo en el proyecto.")
                        else:
                            python = sys.executable or 'python'
                            # start detached process
                            proc = subprocess.Popen([python, sig_path], cwd=os.path.dirname(__file__), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
                                try:
                                    webbrowser.open(url)
                                    print('Se abrió la interfaz de firma en el navegador.')
                                except Exception as e:
                                    print('No se pudo abrir la interfaz de firma en el navegador:', e)
                            else:
                                print('No se pudo conectar al servidor de firma en', url)
                    except Exception as e:
                        print('Error iniciando servidor de firma:', e)

                    # romper el bucle principal para limpiar recursos y salir
                    break

                else:

                    msg = f"NO MATCH ✖ dist={distance:.3f}"
                    color = (0, 0, 255)

            display = frame.copy()

            cv2.putText(
                display,
                msg,
                (10, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                color,
                3
            )

            cv2.imshow("Resultado", display)

            cv2.waitKey(2500)

            cv2.destroyWindow("Resultado")

            try:
                os.remove(tmp_path)
            except:
                pass

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()