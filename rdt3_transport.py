"""
Transporte de mensagens RDT 3.0 (Stop-and-Wait) sobre UDP.

Este módulo é intencionalmente pequeno e auto-contido:
- Sem checksum (o UDP já possui), conforme permitido pela especificação do projeto.
- Usa números de seq 0/1 por peer (addr) e ACKs.
- Enquanto envia e espera por ACK, ainda consegue processar DATA de entrada,
  enfileirando-os para consumo posterior.

Formatos de pacote:
- DATA: b"SEQ:<0|1>|" + payload
- ACK:  b"ACK:<0|1>"

Tamanho do buffer: mantenha o payload abaixo de ~900 bytes para ficar abaixo de 1024 bytes no total.
"""


from __future__ import annotations

import socket
import random
import time
from collections import deque
from typing import Deque, Dict, Optional, Tuple

Addr = Tuple[str, int]


def _maybe_drop(loss_prob: float) -> bool:
    return loss_prob > 0.0 and random.random() < loss_prob


def _make_data(seq: int, payload: bytes) -> bytes:
    return f"SEQ:{seq}|".encode() + payload


def _make_ack(seq: int) -> bytes:
    return f"ACK:{seq}".encode()


def _parse(packet: bytes):
    if packet.startswith(b"ACK:"):
        try:
            seq = int(packet.decode().split(":", 1)[1])
            return ("ACK", seq, b"")
        except Exception:
            return ("UNKNOWN", None, b"")
    if packet.startswith(b"SEQ:"):
        try:
            header, payload = packet.split(b"|", 1)
            seq = int(header.decode().split(":", 1)[1])
            return ("DATA", seq, payload)
        except Exception:
            return ("UNKNOWN", None, b"")
    return ("UNKNOWN", None, b"")


class RDT3Transport:
    """
    Transporte RDT3.0 Stop-and-Wait para mensagens pequenas sobre um socket UDP.

    Uso típico (lado do servidor):
      sock = socket.socket(AF_INET, SOCK_DGRAM); sock.bind(...)
      rdt = RDT3Transport(sock, loss_prob=0.1)
      while True:
          rdt.process_incoming(timeout=0.1)
          while (msg := rdt.pop_delivered()) is not None:
              addr, payload = msg
              ...

    No lado do cliente, dá para executar process_incoming() em uma thread para imprimir broadcasts.
    """

    def __init__(
        self,
        sock: socket.socket,
        *,
        loss_prob: float = 0.0,
        timeout: float = 0.3,
        max_packet: int = 1024,
    ):
        self.sock = sock
        self.loss_prob = float(loss_prob)
        self.timeout = float(timeout)
        self.max_packet = int(max_packet)

        # estado de seq por peer
        self._send_seq: Dict[Addr, int] = {}
        self._expect_seq: Dict[Addr, int] = {}

        # controle de ACK: (addr, seq) -> last_seen_time
        self._acks: Dict[Tuple[Addr, int], float] = {}

        # fila de DATA entregues: (addr, payload)
        self._delivered: Deque[Tuple[Addr, bytes]] = deque()

    def pop_delivered(self) -> Optional[Tuple[Addr, bytes]]:
        try:
            return self._delivered.popleft()
        except IndexError:
            return None

    def _send_raw(self, packet: bytes, addr: Addr):
        if _maybe_drop(self.loss_prob):
            return
        self.sock.sendto(packet, addr)

    def process_incoming(self, timeout: float = 0.0):
        """Recebe no máximo um datagrama (se disponível) e o processa."""
        prev_timeout = self.sock.gettimeout()
        try:
            self.sock.settimeout(timeout if timeout is not None else None)
            try:
                packet, addr = self.sock.recvfrom(self.max_packet)
            except socket.timeout:
                return
            kind, seq, payload = _parse(packet)

            if kind == "ACK" and seq in (0, 1):
                self._acks[(addr, seq)] = time.time()
                return

            if kind == "DATA" and seq in (0, 1):
                # Sempre envia ACK do que recebemos (mesmo duplicados)
                self._send_raw(_make_ack(seq), addr)

                exp = self._expect_seq.get(addr, 0)
                if seq == exp:
                    self._delivered.append((addr, payload))
                    self._expect_seq[addr] = 1 - exp
                # se não: DATA duplicado; ignora a entrega, mas o ACK já foi enviado
                return

            # pacote desconhecido: ignora
        finally:
            self.sock.settimeout(prev_timeout)

    def sendto(self, payload: bytes, addr: Addr):
        """Reliable send (Stop-and-Wait): blocks until ACK or retries forever."""
        if not isinstance(payload, (bytes, bytearray)):
            raise TypeError("payload must be bytes")
        if len(payload) > (self.max_packet - 16):
            raise ValueError(
                f"payload too large ({len(payload)} bytes). "
                f"Keep it under ~{self.max_packet-16} bytes."
            )

        seq = self._send_seq.get(addr, 0)
        packet = _make_data(seq, bytes(payload))

        while True:
            # envia o pacote
            self._send_raw(packet, addr)

            deadline = time.time() + self.timeout
            # espera pelo ACK, mas continua processando outros pacotes de entrada
            while time.time() < deadline:
                self.process_incoming(timeout=max(0.0, deadline - time.time()))
                if (addr, seq) in self._acks:
                    # consome o ACK e avança o seq
                    self._acks.pop((addr, seq), None)
                    self._send_seq[addr] = 1 - seq
                    return
            # timeout -> retransmite
