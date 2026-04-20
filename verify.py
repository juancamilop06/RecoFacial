import os
import tempfile
import argparse
import cv2
from deepface import DeepFace
import threading
import webbrowser
import time
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

    print("Usando imagen:", id_path)

    if not os.path.exists(id_path):
        print("No se encontró la imagen de referencia.")
        print("Coloca tu foto en: data/id.jpg")
        return

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("No se pudo abrir la cámara.")
        return

    print("\nPresiona:")
    print("SPACE -> capturar y verificar")
    print("Q o ESC -> salir\n")

    while True:

        ret, frame = cap.read()

        if not ret:
            print("Error leyendo cámara")
            break

        h, w = frame.shape[:2]

        cv2.putText(
            frame,
            "SPACE para verificar rostro",
            (10, h - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

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

                    # Iniciar el servidor de firma (si está disponible) y abrir la página
                    def _start_sig():
                        if run_server is None:
                            print("No se encontró signature_server. Instala signature_server.py y Flask.")
                            return
                        run_server()

                    try:
                        # start server in background non-daemon thread so it stays alive
                        t = threading.Thread(target=_start_sig)
                        t.start()
                        # give server a moment to start and bind the camera
                        time.sleep(0.8)
                        # abrir navegador a la UI de firma
                        webbrowser.open('http://127.0.0.1:5000/signature')
                        print('Se abrió la interfaz de firma en el navegador.')
                    except Exception as e:
                        print('No se pudo abrir la interfaz de firma:', e)

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