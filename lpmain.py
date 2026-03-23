import socket
import struct
import cv2
import numpy as np
import time
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from collections import deque
import subprocess

FACE_MODEL_PATH = "face_landmarker.task"
PORT = 8000


def alarm():
    subprocess.Popen(["paplay", "alarm.wav"])


landmark_histories = {}
alarm_playing = {}

STILL_THRESHOLD_PX = 15
UNRESPONSIVE_SECONDS = 5

base_options = python.BaseOptions(model_asset_path=FACE_MODEL_PATH)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=True,
    num_faces=5,
    running_mode=vision.RunningMode.VIDEO,
)

server_socket = socket.socket()
server_socket.bind(("0.0.0.0", PORT))
server_socket.listen(0)
print(f"waiting for rpi to connect on port {PORT}...")
connection = server_socket.accept()[0].makefile("rb")

try:
    with vision.FaceLandmarker.create_from_options(options) as landmarker:
        while True:
            image_len_bytes = connection.read(struct.calcsize("<L"))
            if not image_len_bytes:
                break
            image_len = struct.unpack("<L", image_len_bytes)[0]
            image_data = connection.read(image_len)
            if not image_data:
                break

            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is not None:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                timestamp_ms = int(time.time() * 1000)
                result = landmarker.detect_for_video(mp_image, timestamp_ms)
                now = time.time()

                if result.face_landmarks:
                    active_faces = set()

                    for face_idx, face_landmarks in enumerate(result.face_landmarks):
                        active_faces.add(face_idx)

                        for lm in face_landmarks:
                            x = int(lm.x * frame.shape[1])
                            y = int(lm.y * frame.shape[0])
                            cv2.circle(frame, (x, y), 1, (0, 255, 50), -1)

                        if face_idx not in landmark_histories:
                            landmark_histories[face_idx] = deque()
                            alarm_playing[face_idx] = False

                        nose = face_landmarks[4]
                        nx = int(nose.x * frame.shape[1])
                        ny = int(nose.y * frame.shape[0])
                        history = landmark_histories[face_idx]
                        history.append((now, (nx, ny)))

                        if len(history) > 1:
                            xs = [p[1][0] for p in history]
                            ys = [p[1][1] for p in history]
                            movement = max(max(xs) - min(xs), max(ys) - min(ys))

                            if movement >= STILL_THRESHOLD_PX:
                                landmark_histories[face_idx] = deque()
                                landmark_histories[face_idx].append((now, (nx, ny)))
                                alarm_playing[face_idx] = False
                            elif now - history[0][0] >= UNRESPONSIVE_SECONDS:
                                cv2.putText(
                                    frame,
                                    f"WARNING: FACE {face_idx} UNRESPONSIVE",
                                    (30, 60 + face_idx * 40),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    1.2,
                                    (0, 0, 255),
                                    3,
                                )
                                if not alarm_playing[face_idx]:
                                    alarm()
                                    alarm_playing[face_idx] = True

                        elapsed = now - landmark_histories[face_idx][0][0]
                        cv2.putText(
                            frame,
                            f"Face {face_idx} still for: {elapsed:.1f}s",
                            (30, 30 + face_idx * 40),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 200, 255),
                            2,
                        )

                    for face_idx in list(landmark_histories.keys()):
                        if face_idx not in active_faces:
                            del landmark_histories[face_idx]
                            alarm_playing.pop(face_idx, None)

                else:
                    landmark_histories.clear()
                    alarm_playing.clear()
                    cv2.putText(
                        frame,
                        "No face detected",
                        (30, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 100, 255),
                        2,
                    )

                cv2.imshow("Pi Stream - Face Mesh", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

finally:
    print("Closing connection.")
    connection.close()
    server_socket.close()
    cv2.destroyAllWindows()