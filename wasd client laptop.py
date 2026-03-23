import socket
import sys
import tty
import termios

RPI_HOST = 'rpi'
RPI_PORT = 9999

KEYS = {
    'w': 'w', 'a': 'a', 's': 's', 'd': 'd',
    ' ': ' ',
    '=': '+', '+': '+',
    '-': '-',
}

print(f"Connecting to {RPI_HOST}:{RPI_PORT}...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((RPI_HOST, RPI_PORT))
print("connected! WASD to move (tap to toggle),spaace to stop, +/- speed, Esc/q to quit.\n")

fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)

try:
    tty.setraw(fd)
    while True:
        ch = sys.stdin.read(1)
        if ch in ('\x1b', 'q'):  # Esc or q
            print("\r\nQuitting — sending stop...")
            sock.sendall(b' ')
            break
        if ch in KEYS:
            out = KEYS[ch]
            sock.sendall(out.encode())
            label = repr(ch) if ch != ' ' else 'SPACE'
            print(f"\rSending: {label}        ", end='', flush=True)
finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    sock.close()