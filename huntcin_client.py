"""
HuntCin - cliente (Etapa 3)

Uso:
  python huntcin_client.py <ip_servidor> <porta_servidor> <porta_local_cliente> [loss_prob]

Ex:
  python huntcin_client.py 127.0.0.1 5000 5001
  python huntcin_client.py 127.0.0.1 5000 5002
  python huntcin_client.py 127.0.0.1 5000 5001 0.2   # simula perda
"""

from __future__ import annotations

import socket
import sys
import threading
import time

from rdt3_transport import RDT3Transport, Addr


def main():
    if len(sys.argv) < 4:
        print("Uso: python huntcin_client.py <ip_servidor> <porta_servidor> <porta_local_cliente> [loss_prob]")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    local_port = int(sys.argv[3])
    loss = float(sys.argv[4]) if len(sys.argv) >= 5 else 0.0

    server_addr: Addr = (server_ip, server_port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", local_port))

    rdt = RDT3Transport(sock, loss_prob=loss, timeout=0.3)

    stop = False

    def rx_loop():
        nonlocal stop
        while not stop:
            rdt.process_incoming(timeout=0.5)
            while True:
                item = rdt.pop_delivered()
                if item is None:
                    break
                addr, payload = item
                # Só imprima mensagens vindas do servidor
                if addr != server_addr:
                    continue
                try:
                    print(payload.decode("utf-8", errors="replace"))
                except Exception:
                    print(payload)

    t = threading.Thread(target=rx_loop, daemon=True)
    t.start()

    print(f"[Cliente] Conectado. Porta local={local_port}. Servidor={server_ip}:{server_port}")
    print("Comandos: login <nome> | logout | move up/down/left/right | hint | suggest")
    try:
        while True:
            cmd = input("> ").strip()
            if not cmd:
                continue
            rdt.sendto(cmd.encode("utf-8"), server_addr)
            # dá uma chance para o receptor imprimir respostas imediatas
            time.sleep(0.05)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        stop = True
        try:
            sock.close()
        except Exception:
            pass
        print("\n[Cliente] Encerrado.")


if __name__ == "__main__":
    main()
