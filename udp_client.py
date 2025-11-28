import socket
import os
import sys
import random

BUFFER_SIZE = 1024
TIMEOUT = 1.0
LOSS_PROB = 0.2  # probabilidade de "perder" ACKs (simulação do canal)


def make_packet(seq, payload):
    header = f"SEQ:{seq}|".encode()
    return header + payload


def parse_packet(pkt):
    """Extrai SEQ e payload."""
    pkt = pkt.decode(errors="ignore")
    if not pkt.startswith("SEQ:"):
        return None, None
    try:
        parte_seq, payload = pkt.split("|", 1)
        seq = int(parte_seq.split(":")[1])
        return seq, payload.encode()
    except:
        return None, None


def rdt_send(sock, pkt, server_addr, expected_ack):
    """Stop-and-Wait com timeout e retransmissão."""
    while True:
        sock.sendto(pkt, server_addr)
        print(f"[CLIENTE] >>> Enviado SEQ={expected_ack}")

        try:
            sock.settimeout(TIMEOUT)
            data, _ = sock.recvfrom(BUFFER_SIZE)
            msg = data.decode().strip()

            print(f"[CLIENTE] <<< Recebido '{msg}'")

            if msg.startswith("ACK:"):
                acknum = int(msg.split(":")[1])
                if acknum == expected_ack:
                    print("[CLIENTE] ACK correto recebido.")
                    return True
                else:
                    print("[CLIENTE] ACK errado, ignorando...")

        except socket.timeout:
            print("[CLIENTE] Timeout! Retransmitindo...")


def rdt_recv(sock, expected_seq):
    """Recebe 1 pacote RDT3.0 com duplicata/ACK/SEQ funcionando."""
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)

        seq, payload = parse_packet(data)
        if seq is None:
            print("[CLIENTE] Pacote inválido descartado.")
            continue

        print(f"[CLIENTE] <<< Pacote recebido SEQ={seq}")

        # Duplicado → reenviar ACK imediatamente
        if seq != expected_seq:
            print(f"[CLIENTE] Pacote duplicado! reenviando ACK:{1 - expected_seq}")
            sock.sendto(f"ACK:{seq}".encode(), addr)
            continue

        # Simulação de perda do ACK
        if random.random() < LOSS_PROB:
            print("[CLIENTE] (Simulação) ACK perdido, não enviando ACK.")
        else:
            print(f"[CLIENTE] >>> Enviando ACK:{seq}")
            sock.sendto(f"ACK:{seq}".encode(), addr)

        return payload, seq, addr


def enviar_arquivo(sock, server_addr, caminho_arquivo):

    if not os.path.exists(caminho_arquivo):
        print(f"[CLIENTE] Arquivo '{caminho_arquivo}' não encontrado.")
        return

    nome_arquivo = os.path.basename(caminho_arquivo)

    header = f"HEADER|FILENAME:{nome_arquivo}"
    sock.sendto(header.encode(), server_addr)

    print(f"[CLIENTE] Enviando arquivo '{nome_arquivo}' com RDT 3.0...")

    seq = 0

    with open(caminho_arquivo, "rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break

            pkt = make_packet(seq, chunk)
            rdt_send(sock, pkt, server_addr, seq)

            seq = 1 - seq

    eof_pkt = make_packet(seq, b"EOF")
    rdt_send(sock, eof_pkt, server_addr, seq)

    print("[CLIENTE] Envio concluído.")


def receber_devolucao_rdt(sock):
    print("\n[CLIENTE] Aguardando devolução confiável do servidor...")

    # 1) Recebe header (não precisa RDT)
    data, server_addr = sock.recvfrom(BUFFER_SIZE)
    header = data.decode()

    partes = header.split("|")
    novo_nome = partes[1].split(":")[1]

    print(f"[CLIENTE] Devolução iniciada. Novo arquivo: {novo_nome}")
    print("[CLIENTE] === RECEBENDO ARQUIVO VIA RDT 3.0 ===")

    expected_seq = 0

    with open(novo_nome, "wb") as f:
        while True:
            payload, seq, addr = rdt_recv(sock, expected_seq)

            if payload == b"EOF":
                print("[CLIENTE] EOF recebido. Fim da devolução.\n")
                break

            f.write(payload)
            print(f"[CLIENTE] Gravado chunk SEQ={seq}")

            expected_seq = 1 - expected_seq

    return 0

def main():
    if len(sys.argv) != 4:
        print(f"Uso: python {sys.argv[0]} <IP_SERVIDOR> <PORTA> <ARQUIVO>")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    caminho_arquivo = sys.argv[3]

    server_addr = (server_ip, server_port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        enviar_arquivo(sock, server_addr, caminho_arquivo)
        receber_devolucao_rdt(sock)

    finally:
        sock.close()


if __name__ == "__main__":
    main()
