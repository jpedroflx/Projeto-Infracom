import socket
import os

SERVER_HOST = "0.0.0.0"   # escuta em todas as interfaces
SERVER_PORT = 5000
BUFFER_SIZE = 1024

def receber_arquivo(sock, primeiro_pacote, client_addr):
    """
    Recebe um arquivo enviado pelo cliente e o salva no servidor.
    O primeiro pacote contém o cabeçalho com o nome do arquivo.
    """
    header = primeiro_pacote.decode("utf-8")
    # Formato: FILENAME:<nome_arquivo>
    if not header.startswith("FILENAME:"):
        print("Cabeçalho inválido recebido de", client_addr)
        return None, None

    nome_original = header.split(":", 1)[1]
    nome_recebido = f"server_{os.path.basename(nome_original)}"

    print(f"[SERVIDOR] Recebendo arquivo '{nome_original}' de {client_addr}...")
    print(f"[SERVIDOR] Salvando localmente como '{nome_recebido}'")

    with open(nome_recebido, "wb") as f:
        while True:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            # Todos os pacotes desse arquivo devem vir do mesmo cliente
            if addr != client_addr:
                print("Pacote ignorado de outro cliente:", addr)
                continue

            if data == b"EOF":
                # fim do arquivo
                break

            f.write(data)

    print(f"[SERVIDOR] Recebimento concluído. Arquivo salvo: {nome_recebido}")
    return nome_original, nome_recebido


def devolver_arquivo(sock, client_addr, nome_original, nome_salvo):
    """
    Envia o arquivo de volta ao cliente, alterando o nome.
    """
    # Nome alterado antes da devolução (requisito do enunciado)
    novo_nome = f"devolvido_{os.path.basename(nome_original)}"
    tamanho = os.path.getsize(nome_salvo)

    # Cabeçalho de devolução: FILENAME:<novo_nome>|SIZE:<tamanho>
    header = f"FILENAME:{novo_nome}|SIZE:{tamanho}"
    sock.sendto(header.encode("utf-8"), client_addr)

    print(f"[SERVIDOR] Devolvendo arquivo '{nome_salvo}' como '{novo_nome}' para {client_addr}...")

    with open(nome_salvo, "rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            sock.sendto(chunk, client_addr)

    sock.sendto(b"EOF", client_addr)
    print(f"[SERVIDOR] Devolução concluída.\n")


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_HOST, SERVER_PORT))

    print(f"[SERVIDOR] Servidor UDP iniciado em {SERVER_HOST}:{SERVER_PORT}")
    print("[SERVIDOR] Aguardando arquivos... (Ctrl+C para sair)\n")

    try:
        while True:
            # Primeiro pacote de um arquivo: cabeçalho com o nome
            data, client_addr = sock.recvfrom(BUFFER_SIZE)
            nome_original, nome_salvo = receber_arquivo(sock, data, client_addr)

            if nome_original is None:
                # algo deu errado com o cabeçalho
                continue

            # devolve o arquivo para o cliente
            devolver_arquivo(sock, client_addr, nome_original, nome_salvo)

    except KeyboardInterrupt:
        print("\n[SERVIDOR] Encerrando servidor...")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
