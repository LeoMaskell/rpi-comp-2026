import socket
import struct
import time
import io
import threading
import pigpio
from picamera2 import Picamera2

# ── Servo setup ───────────────────────────────────────────────────────────────
LEFT_PIN  = 17  # BCM (BOARD pin 3)
RIGHT_PIN = 27  # BCM (BOARD pin 5)

pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("pigpiod not running — start it with: sudo systemctl start pigpiod")

# SG90-HV pulse widths in microseconds
PW_STOP = 1500
PW_CW   = 2000
PW_CCW  = 1000

def drive(l, r):
    pi.set_servo_pulsewidth(LEFT_PIN,  l)
    pi.set_servo_pulsewidth(RIGHT_PIN, r)

def go_forward():  drive(PW_CW,   PW_CCW)
def go_backward(): drive(PW_CCW,  PW_CW)
def go_left():     drive(PW_CCW,  PW_CCW)
def go_right():    drive(PW_CW,   PW_CW)
def go_stop():     drive(PW_STOP, PW_STOP)

COMMAND_MAP = {
    "forward":  go_forward,
    "backward": go_backward,
    "left":     go_left,
    "right":    go_right,
    "stop":     go_stop,
}

# ── Shared state ──────────────────────────────────────────────────────────────
state      = {"cmd": "stop", "t": 0.0}
state_lock = threading.Lock()
MANUAL_TIMEOUT = 5.0

def is_manual():
    with state_lock:
        return (time.time() - state["t"]) < MANUAL_TIMEOUT

# ── Motor thread ──────────────────────────────────────────────────────────────
# Set AUTO_SQUARE = True once manual control is confirmed working
AUTO_SQUARE   = False
STRAIGHT_TIME = 10.0
TURN_TIME     = 1.5

def interruptible_wait(seconds):
    end = time.time() + seconds
    while time.time() < end:
        if is_manual():
            go_stop()
            return True
        time.sleep(0.05)
    return False

def motor_loop():
    go_stop()
    while True:
        if is_manual():
            with state_lock:
                cmd = state["cmd"]
            if cmd in COMMAND_MAP:
                COMMAND_MAP[cmd]()
            time.sleep(0.05)
        elif AUTO_SQUARE:
            for _ in range(4):
                go_forward()
                if interruptible_wait(STRAIGHT_TIME):
                    break
                go_right()
                if interruptible_wait(TURN_TIME):
                    break
            else:
                go_stop()
                interruptible_wait(1.0)
        else:
            go_stop()
            time.sleep(0.1)

# ── Command server ────────────────────────────────────────────────────────────
CMD_PORT = 8001

def command_server():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", CMD_PORT))
    srv.listen(1)
    print(f"Command server on :{CMD_PORT}")
    while True:
        conn, addr = srv.accept()
        print(f"Controller connected: {addr}")
        try:
            buf = ""
            while True:
                chunk = conn.recv(64).decode(errors="ignore")
                if not chunk:
                    break
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    cmd = line.strip().lower()
                    if cmd in COMMAND_MAP:
                        with state_lock:
                            state["cmd"] = cmd
                            state["t"]   = time.time()
                        print(f"  cmd: {cmd}")
        except Exception as e:
            print(f"Command error: {e}")
        finally:
            conn.close()
            print("Controller disconnected")

# ── Camera stream ─────────────────────────────────────────────────────────────
LAPTOP_IP = "100.68.222.9"
CAM_PORT  = 8000

def camera_stream():
    picam = Picamera2()
    picam.configure(picam.create_preview_configuration(main={"size": (640, 480)}))
    picam.start()
    try:
        while True:
            print(f"Connecting to laptop at {LAPTOP_IP}:{CAM_PORT}...")
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((LAPTOP_IP, CAM_PORT))
                print("Camera stream connected.")
                while True:
                    stream = io.BytesIO()
                    picam.capture_file(stream, format="jpeg")
                    image_data = stream.getvalue()
                    if image_data:
                        client_socket.sendall(struct.pack("<L", len(image_data)))
                        client_socket.sendall(image_data)
                    stream.seek(0)
                    stream.truncate()
            except (ConnectionResetError, ConnectionRefusedError, OSError) as e:
                print(f"Camera stream error: {e} — retrying in 3s...")
                time.sleep(3)
            finally:
                client_socket.close()
    finally:
        picam.stop()

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=command_server, daemon=True).start()
    threading.Thread(target=motor_loop,     daemon=True).start()
    try:
        camera_stream()
    finally:
        go_stop()
        pi.set_servo_pulsewidth(LEFT_PIN,  0)
        pi.set_servo_pulsewidth(RIGHT_PIN, 0)
        pi.stop()