import os
import cv2


def capture_id(path='data/id.jpg'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print('ERROR: no se pudo abrir la cámara')
        return 2
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print('ERROR: no se pudo leer un frame de la cámara')
        return 3
    cv2.imwrite(path, frame)
    print(f'Guardado: {path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(capture_id())
