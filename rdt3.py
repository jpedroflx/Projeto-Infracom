import socket
import random
import os
import time

# =============================================================================
# CONSTANTES GLOBAIS
# =============================================================================

BUFFER_SIZE = 1024                    # Tamanho máximo do buffer UDP
PAYLOAD_SIZE = BUFFER_SIZE - 64       # Espaço para dados (reserva cabeçalho)
DEFAULT_TIMEOUT = 0.05                # Timeout padrão em segundos

# =============================================================================
# SIMULAÇÃO DE PERDAS
# =============================================================================

def _maybe_drop(loss_prob: float) -> bool:
    """
    Simula perda de pacotes com probabilidade configurável
    Args:
        loss_prob: Probabilidade de perda (0.0 a 1.0)
    Returns:
        True se o pacote deve ser "perdido", False caso contrário
    """
    return random.random() < loss_prob

# =============================================================================
# FUNÇÕES DE MANIPULAÇÃO DE PACOTES
# =============================================================================

def _make_data_packet(seq: int, payload: bytes) -> bytes:
    """
    Cria pacote de dados no formato: "SEQ:<n>|" + dados
    Returns:
        Pacote em bytes
    """
    return f"SEQ:{seq}|".encode() + payload

def _make_ack_packet(seq: int) -> bytes:
    """
    Cria (ACK) no formato: "ACK:<n>"
    Returns:
        Pacote ACK em bytes
    """
    return f"ACK:{seq}".encode()

def _parse_packet(packet: bytes) -> tuple:
    """
    Analisa pacote recebido e extrai tipo, sequência e payload
    Returns:
        Tupla (tipo, sequência, payload) onde tipo é 'DATA' ou 'ACK'
    """
    # Verifica se é um ACK
    if packet.startswith(b"ACK:"):
        try:
            seq = int(packet.decode().split(":", 1)[1])
            return 'ACK', seq, b''
        except (ValueError, IndexError):
            return 'UNKNOWN', None, b''
    
    # Verifica se é um pacote de dados
    if packet.startswith(b"SEQ:"):
        parts = packet.split(b'|', 1)
        if len(parts) == 2:
            header = parts[0]  # Formato: "SEQ:<número>"
            payload = parts[1]
            try:
                seq = int(header.decode().split(":", 1)[1])
                return 'DATA', seq, payload
            except (ValueError, IndexError):
                return 'UNKNOWN', None, b''
    
    return 'UNKNOWN', None, b''

# =============================================================================
#  SEND AND WAIT
# =============================================================================

def _send_and_wait_ack(sock: socket.socket, addr: tuple, packet: bytes, 
                       seq: int, loss_prob: float, timeout: float):
    """
    Implementa a lógica de envio e espera por confirmação (Stop-and-Wait)
    Fluxo:
    1. Envia pacote (com possível simulação de perda)
    2. Aguarda ACK com timeout
    3. Se timeout, retransmite
    4. Se ACK incorreto, continua aguardando
    5. Se ACK correto, retorna
    """
    while True:
        # Simula perda no envio do pacote de dados
        if _maybe_drop(loss_prob):
            print(f"[RDT] (SIMULAÇÃO) Pacote SEQ={seq} PERDIDO intencionalmente no envio.")
        else:
            sock.sendto(packet, addr)
            print(f"[RDT] Enviado SEQ={seq} (len={len(packet) - 10} bytes payload) para {addr}")

        # Aguarda (ACK)
        sock.settimeout(timeout)
        try:
            data, addr_recv = sock.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            print(f"[RDT] TIMEOUT aguardando ACK seq={seq}. Retransmitindo...")
            continue  # Volta ao início do loop para retransmitir

        # Analisa o pacote recebido
        ptype, ackseq, _ = _parse_packet(data)
        
        # Verifica se é o ACK esperado
        if ptype == 'ACK' and ackseq == seq:
            print(f"[RDT] ACK recebido: {ackseq} de {addr_recv}")
            return  # ACK correto recebido, pode prosseguir
        else:
            print(f"[RDT] Pacote inesperado enquanto aguardava ACK: {ptype} {ackseq}. Ignorando...")

# =============================================================================
# LÓGICA DO RECEPTOR
# =============================================================================

def _receive_data_packet(sock: socket.socket, expected_seq: int,
                         loss_prob: float, timeout_for_recv: float) -> tuple:
    """
    Aguarda por pacote de dados com sequência específica
    
    Fluxo:
    1. Aguarda pacote de dados
    2. Se sequência correta: envia ACK e retorna dados
    3. Se sequência incorreta: reenvia ACK anterior (para ajudar transmissor)
    4. Se pacote inválido: ignora e continua
    """
    while True:
        try:
            packet, addr = sock.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            # Timeout permite que a função seja responsiva a interrupções
            raise

        # Analisa o pacote recebido
        ptype, seq, payload = _parse_packet(packet)
        print(f"[RDT] Pacote recebido de {addr}: type={ptype} seq={seq} payload_len={len(payload)}")
        
        # Ignora pacotes que não são de dados
        if ptype != 'DATA':
            print(f"[RDT] Pacote inesperado no receptor (não DATA). Ignorando.")
            continue

        # Pacote com sequência esperada - processa normalmente
        if seq == expected_seq:
            # Envia ACK (com possível simulação de perda)
            if _maybe_drop(loss_prob):
                print(f"[RDT] (SIMULAÇÃO) Perda intencional do ACK para seq={seq}")
            else:
                ack = _make_ack_packet(seq)
                sock.sendto(ack, addr)
                print(f"[RDT] Enviado ACK:{seq} para {addr}")

            return payload, seq, addr
        else:
            # Pacote duplicado (sequência antiga) - reenvia ACK para ajudar transmissor
            print(f"[RDT] Pacote duplicado (seq={seq}), reenviando ACK:{seq}")
            if _maybe_drop(loss_prob):
                print(f"[RDT] (SIMULAÇÃO) Perda intencional do ACK duplicado seq={seq}")
            else:
                ack = _make_ack_packet(seq)
                sock.sendto(ack, addr)
                print(f"[RDT] Reenviado ACK:{seq} para {addr}")
            # Continua aguardando pacote com sequência correta

# =============================================================================
# API PÚBLICA - ENVIO DE ARQUIVO
# =============================================================================

def rdt_send_file(sock: socket.socket, addr: tuple, filepath: str,
                  loss_prob: float = 0.0, timeout: float = DEFAULT_TIMEOUT):
    """
    Envia um arquivo usando protocolo RDT 3.0 (Stop-and-Wait)
    
    Fluxo completo:
    1. Envia START com metadados (nome e tamanho do arquivo)
    2. Envia chunks de dados em sequência alternada (0, 1, 0, 1...)
    3. Envia END para sinalizar término
    4. Cada passo aguarda confirmação antes de prosseguir
    
    """
    seq = 0  # seq inicia com 0
    
    # Prepara metadados do arquivo
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    start_payload = f"{filename}|{filesize}".encode()

    # ENVIO DO PACOTE START 
    pkt = _make_data_packet(seq, start_payload)
    print(f"[RDT] >>> Enviando START seq={seq} filename={filename} size={filesize}")
    _send_and_wait_ack(sock, addr, pkt, seq, loss_prob, timeout)
    seq = 1 - seq  # Alterna sequência (0 -> 1 ou 1 -> 0)

    # ENVIO DOS CHUNKS DE DADOS 
    with open(filepath, "rb") as f:
        chunk_idx = 0
        while True:
            # Lê próximo chunk do arquivo
            payload = f.read(PAYLOAD_SIZE)
            if not payload:
                break  # Fim do arquivo
                
            # Envia chunk e aguarda confirmação
            pkt = _make_data_packet(seq, payload)
            print(f"[RDT] >>> Enviando DATA seq={seq} chunk={chunk_idx} len={len(payload)}")
            _send_and_wait_ack(sock, addr, pkt, seq, loss_prob, timeout)
            seq = 1 - seq  # Alterna sequência
            chunk_idx += 1

    # ENVIO DO PACOTE END 
    pkt = _make_data_packet(seq, b"EOF")  # EOF marca o fim
    print(f"[RDT] >>> Enviando END seq={seq}")
    _send_and_wait_ack(sock, addr, pkt, seq, loss_prob, timeout)
    
    print("[RDT] >>> Envio de arquivo concluído (RDT).")

# =============================================================================
# API PÚBLICA - RECEPÇÃO DE ARQUIVO
# =============================================================================

def rdt_recv_file(sock: socket.socket, out_dir: str = ".",
                  loss_prob: float = 0.0, timeout_for_recv: float = 1.0) -> tuple:
    """
    Fluxo:
    1. Aguarda pacote START com metadados
    2. Cria arquivo de saída
    3. Recebe chunks de dados sequencialmente
    4. Detecta pacote END para finalizar
    
    Returns:
        Tupla (caminho_do_arquivo, endereço_do_cliente)
    """
    expected_seq = 0  # Sequência inicial esperada
    saved_path = None
    fobj = None

    # Configura timeout para tornar o loop responsivo
    sock.settimeout(timeout_for_recv)
    print("[RDT] Aguardando START (RDT)...")
    
    # RECEPÇÃO DO PACOTE START 
    while True:
        try:
            payload, seq, addr = _receive_data_packet(sock, expected_seq, loss_prob, timeout_for_recv)
        except socket.timeout:
            # Timeout normal  continua aguardando
            continue

        # Processa metadados do arquivo
        try:
            parts = payload.split(b'|', 1)
            filename = parts[0].decode(errors='ignore') if parts else f"unnamed_{int(time.time())}"
        except Exception:
            filename = f"unnamed_{int(time.time())}"

        # Prepara arquivo de saída 
        saved_name = f"devolvido_{os.path.basename(filename)}"
        saved_path = os.path.join(out_dir, saved_name)
        fobj = open(saved_path, "wb")
        print(f"[RDT] START recebido. Arquivo será salvo em '{saved_path}'")
        expected_seq = 1 - expected_seq  # Prepara próxima sequência
        break

    # RECEPÇÃO DOS CHUNKS DE DADOS
    while True:
        try:
            payload, seq, addr = _receive_data_packet(sock, expected_seq, loss_prob, timeout_for_recv)
        except socket.timeout:
            continue  # Continua aguardando

        # Verifica se é pacote de finalização
        if payload == b"EOF":
            print(f"[RDT] END recebido (seq={seq}). Finalizando arquivo '{saved_path}'")
            if fobj:
                fobj.close()
            return saved_path, addr

        # Escreve dados no arquivo
        fobj.write(payload)
        fobj.flush()
        print(f"[RDT] Gravado chunk len={len(payload)} no arquivo '{saved_path}'")
        expected_seq = 1 - expected_seq  # Prepara próxima sequência

