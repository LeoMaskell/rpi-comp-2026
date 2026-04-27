# IRIS — Intelligent Recognition & Incident Surveillance

> **Bluecoat School Liverpool · PA Consulting Raspberry Pi Competition 2026**

IRIS is an autonomous rover that continuously patrols care homes and raises an alarm the moment it detects an unresponsive person — no wearables, no constant manual monitoring, no blind spots.

---

## The problem

- In nursing homes and single-occupancy homes, injuries go undetected for up to **4 hours**.
- The longer a person waits for help, the more severe the outcome — delayed response can turn a minor fall into a life-threatening event.
- Existing systems rely on understaffed carers or fixed cameras with blind spots; neither provides reliable, continuous coverage.

## The solution

IRIS is a small, affordable rover built on a Raspberry Pi 4B. It patrols autonomously, streams live video to a laptop, and uses **MediaPipe face landmark detection** to track whether a person has stopped moving. If someone remains still for too long, an audible alarm fires immediately — giving staff seconds to respond instead of hours.

Key advantages:
- **No blind spots** — the rover moves, so every corner is covered.
- **No wearables** — residents don't need to press a button or wear a device.
- **No extra microcontroller** — the Pi handles camera, motors, and comms in a single script.
- **Always on** — runs 24/7 without any staff input.

---

## How it works

```
Pi Camera → Raspberry Pi 4B → [Python socket / WiFi] → Laptop → MediaPipe → Alarm
                ↑
         pigpio PWM → 2× SG90-HV Servos (wheels)
```

| Step | What happens |
|------|-------------|
| **1 Patrol** | The rover drives a continuous square route autonomously (or can be steered manually via WASD). |
| **2 Stream** | The Pi Camera captures frames and sends them over a TCP socket (port 8000) to the laptop. |
| **3 Analyse** | The laptop decodes each frame, runs the MediaPipe Face Landmarker, and tracks nose-tip movement per face. |
| **4 Alert** | If any face stays still (< 15 px movement) for **5 seconds**, a `WARNING` overlay appears and `paplay` fires an alarm sound. |

---

## Repository structure

```
rpi-comp-2026/
├── lpmain.py                          # Laptop: receive stream, run face detection, trigger alarm
├── rpi main.py                        # Raspberry Pi: camera stream + servo motor control
├── wasd client laptop.py              # Optional: manual WASD keyboard control client
├── poster/
│   └── index.html                     # Competition poster (HTML)
├── IRIS - Raspberry Pi Competition 2026.pdf   # Full project write-up
├── video link.txt                     # Link to demo video
└── LICENSE
```

---

## Hardware

| Component | Part | Approx. cost |
|-----------|------|-------------|
| Compute | Raspberry Pi 4B | ~£50 |
| Vision | Pi Camera Module V2 | ~£20 |
| Motion | 2× SG90-HV continuous-rotation servos | ~£10 |
| Power | HW-131 power module (USB) | ~£10 |
| **Total** | | **~£90** |

Connectivity: WiFi (no extra hardware needed).

---

## Software requirements

### Raspberry Pi
- Python 3
- [pigpio](https://abyz.me.uk/rpi/pigpio/) — `sudo apt install pigpio python3-pigpio`
- [Picamera2](https://github.com/raspberrypi/picamera2) — `sudo apt install python3-picamera2`

### Laptop (processing node)
- Python 3
- OpenCV — `pip install opencv-python`
- MediaPipe — `pip install mediapipe`
- NumPy — `pip install numpy`
- `paplay` (PulseAudio) for the alarm sound — `sudo apt install pulseaudio-utils`
- `face_landmarker.task` model file — download from the [MediaPipe Models page](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker#models) and place it alongside `lpmain.py`
- `alarm.wav` — place an alarm sound file alongside `lpmain.py`

---

## Setup & usage

### 1. Start pigpiod on the Pi
```bash
sudo systemctl start pigpiod
```

### 2. Configure IP addresses
In `rpi main.py`, set `LAPTOP_IP` to your laptop's IP address:
```python
LAPTOP_IP = "192.168.x.x"   # your laptop's IP
```

### 3. Start the laptop receiver first
```bash
python3 lpmain.py
```
The laptop will listen on **port 8000** for the camera stream.

### 4. Start the Raspberry Pi
```bash
python3 "rpi main.py"
```
The Pi connects to the laptop, starts streaming, and begins the motor loop.

### 5. (Optional) Enable autonomous patrol
In `rpi main.py`, flip the flag:
```python
AUTO_SQUARE = True
```
The rover will then drive a square pattern continuously (10 s straight, 1.5 s turn, repeat).

### 6. (Optional) Manual WASD control
Run on the laptop while the Pi is running:
```bash
python3 "wasd client laptop.py"
```
Controls: `W`/`A`/`S`/`D` to move, `Space` to stop, `Esc`/`Q` to quit.
Manual commands override autonomous mode for 5 seconds.

---

## Configuration

| File | Variable | Default | Description |
|------|----------|---------|-------------|
| `lpmain.py` | `STILL_THRESHOLD_PX` | `15` | Max pixel movement before resetting the stillness timer |
| `lpmain.py` | `UNRESPONSIVE_SECONDS` | `5` | Seconds of stillness before alarm triggers |
| `lpmain.py` | `PORT` | `8000` | Camera stream port |
| `rpi main.py` | `LAPTOP_IP` | `"100.68.222.9"` | Laptop IP to stream camera to |
| `rpi main.py` | `CAM_PORT` | `8000` | Camera stream port |
| `rpi main.py` | `CMD_PORT` | `8001` | Manual command server port |
| `rpi main.py` | `AUTO_SQUARE` | `False` | Enable autonomous square patrol |
| `rpi main.py` | `STRAIGHT_TIME` | `10.0` | Seconds to drive straight per leg |
| `rpi main.py` | `TURN_TIME` | `1.5` | Seconds to turn at each corner |
| `rpi main.py` | `MANUAL_TIMEOUT` | `5.0` | Seconds before reverting to autonomous after last manual command |

---

## Key stats

| Metric | Value |
|--------|-------|
| Stillness-to-alert latency | < 10 s |
| Faces tracked simultaneously | Up to 5 |
| Wearables required | 0 |
| Continuous operation | 24/7 |
| Approximate build cost | ~£90 |

---

## Demo

See [`video link.txt`](https://rpi-comp-2026.onrender.com/) for a QR code to the demo video, and [`poster/index.html`](https://tbcs-entry-rpi.onrender.com/) for the competition poster.

---

## Licence

See [LICENSE](LICENSE).
