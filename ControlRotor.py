#!/usr/bin/env python3
import socket
import threading
import serial
import re

SERIAL_PORT = "COM4"          # adapte selon ton PC
SERIAL_BAUD = 19200           # adapte selon ton PIC

TCP_HOST = "0.0.0.0"
TCP_PORT = 4533

# Dernière consigne mémorisée (toujours initialisée à 0)
last_az = 0.0
last_el = 0.0

# Regex pour WAZxxx.yELxxx.y (avec virgule ou point)
W_PATTERN = re.compile(
    r"WAZ(\d{1,3}[.,]\d)EL(\d{1,3}[.,]\d)",
    re.IGNORECASE
)

# ---------------------------------------------------------
#  Fonctions d’envoi vers le PIC ST3
# ---------------------------------------------------------

def send_pic_AE(ser, az=None, el=None):
    if az is not None:
        cmd = f"A{az:06.1f}"
        print(f"[SERIAL -> PIC] {cmd}")
        ser.write(cmd.encode("ascii"))
    if el is not None:
        cmd = f"E{el:06.1f}"
        print(f"[SERIAL -> PIC] {cmd}")
        ser.write(cmd.encode("ascii"))


def send_pic_W(ser, az, el):
    cmd = f"WAZ{az:06.1f}EL{el:06.1f}"
    print(f"[SERIAL -> PIC] {cmd}")
    ser.write(cmd.encode("ascii"))


# ---------------------------------------------------------
#  Réponse GETPOS : toujours renvoyer quelque chose
# ---------------------------------------------------------

def reply_position(f):
    """Répond toujours une position valide à Gpredict."""
    global last_az, last_el

    az_str = f"{last_az:.1f}"
    el_str = f"{last_el:.1f}"

    f.write(f"{az_str}\n{el_str}\n".encode("ascii"))
    f.write(b"RPRT 0\n")

# ---------------------------------------------------------
#  Gestion d’un client TCP (Gpredict)
# ---------------------------------------------------------

def handle_client(conn, addr, ser):
    global last_az, last_el
    f = conn.makefile("rwb", buffering=0)

    try:
        while True:
            line = f.readline()
            if not line:
                break

            line = line.decode("ascii", errors="ignore").strip()
            if not line:
                continue

            print(f"[TCP] {addr} -> {line}")

            # Quit
            if line.lower() == "q":
                f.write(b"RPRT 0\n")
                break

            # GETPOS (toutes variantes)
            if line in ("p", "P", "C2", "C3"):
                reply_position(f)
                continue

            # SETPOS: P az el
            if line.startswith("P "):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        az = float(parts[1].replace(",", "."))
                        el = float(parts[2].replace(",", "."))
                        last_az = az
                        last_el = el
                        send_pic_AE(ser, az=az, el=el)
                        f.write(b"RPRT 0\n")
                    except ValueError:
                        f.write(b"RPRT -1\n")
                else:
                    f.write(b"RPRT -1\n")
                continue

            # Commande combinée WAZxxx.yELxxx.y
            m = W_PATTERN.match(line)
            if m:
                az = float(m.group(1).replace(",", "."))
                el = float(m.group(2).replace(",", "."))
                last_az = az
                last_el = el
                send_pic_W(ser, az, el)
                f.write(b"RPRT 0\n")
                continue

            # Non géré
            f.write(b"RPRT -1\n")

    finally:
        conn.close()
        print(f"[TCP] {addr} disconnected")

# ---------------------------------------------------------
#  Programme principal
# ---------------------------------------------------------

def main():
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.1)
    print(f"[SERIAL] Opened {SERIAL_PORT} @ {SERIAL_BAUD}")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((TCP_HOST, TCP_PORT))
    srv.listen(1)
    print(f"[TCP] Listening on {TCP_HOST}:{TCP_PORT}")

    try:
        while True:
            conn, addr = srv.accept()
            print(f"[TCP] Connection from {addr}")
            t = threading.Thread(
                target=handle_client,
                args=(conn, addr, ser),
                daemon=True
            )
            t.start()

    finally:
        srv.close()
        ser.close()

if __name__ == "__main__":
    main()
