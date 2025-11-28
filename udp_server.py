"""
Uso:
    python3 server.py <PORTA> [prob_perda]
Exemplo:
    python3 server.py 5000 0.3
    python3 server.py 8080
"""
import socket
import sys
import os
import rdt3

# Configurações do servidor
SERVER_HOST = "0.0.0.0"  # Escuta em todas as interfaces

def main():
    # Verifica argumentos da linha de comando
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} <PORTA> [prob_perda]")
        print("Exemplo: python3 server.py 5000 0.2")
        sys.exit(1)
    
    # Configurações do servidor
    port = int(sys.argv[1])
    loss_prob = float(sys.argv[2]) if len(sys.argv) >= 3 else 0.0

    # Cria e configura socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_HOST, port))
    
    print("=" * 60)
    print("SERVIDOR RDT 3.0 - TRANSFERÊNCIA CONFIÁVEL")
    print("=" * 60)
    print(f"Endereço: {SERVER_HOST}:{port}")
    print(f"Probabilidade de perda: {loss_prob * 100}%")
    print("=" * 60)
    print("Aguardando conexões de clientes...")
    print("Pressione Ctrl+C para encerrar o servidor")
    print("=" * 60)

    try:
        while True:
            print(f"\n" + "="*50)
            print(f" Aguardando novo cliente...")
            print("="*50)
            
            try:
                #  RECEBE ARQUIVO DO CLIENTE 
                saved_path, client_addr = rdt3.rdt_recv_file(
                    sock, 
                    out_dir=".", 
                    loss_prob=loss_prob, 
                    timeout_for_recv=1.0
                )
                
                print(f"[SERVIDOR]  Arquivo recebido: {saved_path}")
                print(f"[SERVIDOR]  Tamanho: {os.path.getsize(saved_path)} bytes")
                print(f"[SERVIDOR]  Cliente: {client_addr}")

                # DEVOLVE ARQUIVO PARA O CLIENTE 
                print(f"[SERVIDOR] Iniciando devolução do arquivo para {client_addr}...")
                rdt3.rdt_send_file(
                    sock, 
                    client_addr, 
                    saved_path, 
                    loss_prob=loss_prob, 
                    timeout=1.0
                )
                
                print(f"[SERVIDOR]  Devolução concluída para {client_addr}")
                
                # remove arquivo temporário
                try:
                    os.remove(saved_path)
                    print(f"[SERVIDOR]   Arquivo temporário removido: {saved_path}")
                except:
                    pass  # Ignora erros na remoção
                    
            except KeyboardInterrupt:
                raise  # Re-lança para ser tratado no loop externo
            except Exception as e:
                print(f"[SERVIDOR]  Erro com cliente: {e}")
                continue  # Continua atendendo outros clientes

    except KeyboardInterrupt:
        print(f"\n[SERVIDOR]  Encerrando servidor...")
    finally:
        sock.close()
        print(f"[SERVIDOR]  Servidor encerrado.")

if __name__ == '__main__':
    main()