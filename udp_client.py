import socket
import os
import sys

BUFFER_SIZE = 1024


def enviar_arquivo(sock, server_addr, caminho_arquivo):
    """
    Envia um arquivo para o servidor, em pacotes de até BUFFER_SIZE bytes.
    """
    if not os.path.exists(caminho_arquivo):
        print(f"[CLIENTE] Arquivo '{caminho_arquivo}' não encontrado.")
        sys.exit(1)

    nome_arquivo = os.path.basename(caminho_arquivo)

    # Cabeçalho inicial com o nome do arquivo
    header = f"FILENAME:{nome_arquivo}"
    sock.sendto(header.encode("utf-8"), server_addr)

    print(f"[CLIENTE] Enviando arquivo '{nome_arquivo}' para {server_addr} ...")

    with open(caminho_arquivo, "rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            sock.sendto(chunk, server_addr)

    # Indica fim do arquivo
    sock.sendto(b"EOF", server_addr)
    print("[CLIENTE] Envio concluído.")


def receber_devolucao(sock):
    """
    Recebe o arquivo devolvido pelo servidor.
    """
    print("[CLIENTE] Aguardando arquivo de devolução do servidor...")

    # Recebe cabeçalho de devolução
    data, server_addr = sock.recvfrom(BUFFER_SIZE)
    header = data.decode("utf-8")

    # Formato: FILENAME:<novo_nome>|SIZE:<tamanho>
    partes = header.split("|")
    nome_parte = partes[0]

    novo_nome = nome_parte.split(":", 1)[1]

    print(f"[CLIENTE] Recebendo arquivo devolvido como '{novo_nome}' de {server_addr} ...")

    with open(novo_nome, "wb") as f:
        while True:
            chunk, addr = sock.recvfrom(BUFFER_SIZE)
            if chunk == b"EOF":
                break
            f.write(chunk)

    print(f"[CLIENTE] Arquivo devolvido salvo como '{novo_nome}'.\n")


def main():
    if len(sys.argv) != 4:
        print(f"Uso: python {sys.argv[0]} <IP_SERVIDOR> <PORTA> <CAMINHO_ARQUIVO>")
        print(f"Ex.: python {sys.argv[0]} 127.0.0.1 5000 exemplo.txt")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    caminho_arquivo = sys.argv[3]

    server_addr = (server_ip, server_port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        enviar_arquivo(sock, server_addr, caminho_arquivo)
        receber_devolucao(sock)
    finally:
        sock.close()


if __name__ == "__main__":
    main()
