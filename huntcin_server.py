"""
HuntCin - servidor (Etapa 3)

Uso:
  python huntcin_server.py <porta_servidor> [duracao_rodada_seg] [loss_prob]

Ex:
  python huntcin_server.py 5000 10
  python huntcin_server.py 5000 10 0.2   # simula 20% de perda (RDT3.0 deve lidar)
"""

from __future__ import annotations

import socket
import sys
import time
import random
from typing import Dict, Tuple, Optional, Set

from rdt3_transport import RDT3Transport, Addr

GRID_MIN = 1
GRID_MAX = 3


def _clamp_grid(x: int, y: int) -> bool:
    return GRID_MIN <= x <= GRID_MAX and GRID_MIN <= y <= GRID_MAX


def _random_treasure() -> Tuple[int, int]:
    while True:
        x = random.randint(GRID_MIN, GRID_MAX)
        y = random.randint(GRID_MIN, GRID_MAX)
        if (x, y) != (1, 1):
            return (x, y)


class HuntCinServer:
    def __init__(self, port: int, round_secs: int = 10, loss_prob: float = 0.0):
        self.port = int(port)
        self.round_secs = int(round_secs)
        self.loss_prob = float(loss_prob)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", self.port))

        self.rdt = RDT3Transport(self.sock, loss_prob=self.loss_prob, timeout=0.3)

        # estado do usuário
        self.user_by_addr: Dict[Addr, str] = {}
        self.addr_by_user: Dict[str, Addr] = {}
        self.pos: Dict[str, Tuple[int, int]] = {}
        self.score: Dict[str, int] = {}

        # ações limitadas por partida
        self.used_hint: Set[str] = set()
        self.used_suggest: Set[str] = set()

        # controle da rodada
        self.round_id = 0
        self.round_active_users: Set[str] = set()
        self.round_sent_cmd: Set[str] = set()
        self.round_deadline: float = 0.0

        self.treasure = _random_treasure()

    def _send(self, addr: Addr, msg: str):
        self.rdt.sendto(msg.encode("utf-8"), addr)

    def _broadcast(self, msg: str):
        for addr in list(self.user_by_addr.keys()):
            self._send(addr, msg)

    def _require_login(self, addr: Addr) -> Optional[str]:
        user = self.user_by_addr.get(addr)
        if not user:
            self._send(addr, "[Servidor] Você precisa fazer login primeiro: login <nome>")
            return None
        return user

    def _handle_login(self, addr: Addr, parts):
        if len(parts) != 2:
            self._send(addr, "[Servidor] Uso: login <nome_do_usuario>")
            return

        name = parts[1].strip()
        if not name:
            self._send(addr, "[Servidor] Nome inválido.")
            return
        if name in self.addr_by_user and self.addr_by_user[name] != addr:
            self._send(addr, "[Servidor] Nome já está em uso.")
            return

        # se este addr já estiver logado com outro nome, faça logout primeiro
        if addr in self.user_by_addr:
            old = self.user_by_addr[addr]
            if old != name:
                self._logout(addr)

        self.user_by_addr[addr] = name
        self.addr_by_user[name] = addr

        self.score.setdefault(name, 0)
        self.pos[name] = (1, 1)

        self._send(addr, "você está online!")
        self._broadcast(f"[Servidor] {name}:{addr[1]} entrou no jogo.")

    def _logout(self, addr: Addr):
        user = self.user_by_addr.pop(addr, None)
        if not user:
            self._send(addr, "[Servidor] Você não está logado.")
            return
        self.addr_by_user.pop(user, None)
        self.pos.pop(user, None)
        self.used_hint.discard(user)
        self.used_suggest.discard(user)
        self.round_active_users.discard(user)
        self.round_sent_cmd.discard(user)
        self._broadcast(f"[Servidor] {user}:{addr[1]} saiu do jogo.")

    def _move(self, user: str, direction: str) -> str:
        x, y = self.pos.get(user, (1, 1))
        nx, ny = x, y
        if direction == "up":
            ny += 1
        elif direction == "down":
            ny -= 1
        elif direction == "left":
            nx -= 1
        elif direction == "right":
            nx += 1
        else:
            return "[Servidor] Direção inválida. Use: move up|down|left|right"

        if not _clamp_grid(nx, ny):
            return "[Servidor] Movimento inválido: fora do grid 3x3."

        self.pos[user] = (nx, ny)
        return f"[Servidor] {user} agora está em ({nx},{ny})."

    def _hint(self, user: str) -> str:
        if user in self.used_hint:
            return "[Servidor] Você já usou sua dica (hint) nesta partida."
        self.used_hint.add(user)

        px, py = self.pos.get(user, (1, 1))
        tx, ty = self.treasure

        # segue exemplos da especificação (acima/direita), mas permite outras direções também
        if py < ty:
            return "O tesouro está mais acima."
        if px < tx:
            return "O tesouro está mais à direita."
        if py > ty:
            return "O tesouro está mais abaixo."
        if px > tx:
            return "O tesouro está mais à esquerda."
        return "Você está alinhado com o tesouro de alguma forma... continue!"

    def _suggest(self, user: str) -> str:
        if user in self.used_suggest:
            return "[Servidor] Você já usou sua sugestão (suggest) nesta partida."
        self.used_suggest.add(user)

        px, py = self.pos.get(user, (1, 1))
        tx, ty = self.treasure
        dx = tx - px
        dy = ty - py

        # escolhe o eixo mais forte na direção do tesouro
        if abs(dy) >= abs(dx) and dy != 0:
            if dy > 0:
                return f"Sugestão: move up {abs(dy)} casas."
            return f"Sugestão: move down {abs(dy)} casas."
        if dx != 0:
            if dx > 0:
                return f"Sugestão: move right {abs(dx)} casas."
            return f"Sugestão: move left {abs(dx)} casas."
        return "Sugestão: você já está no tesouro (ou muito perto)."

    def _state_line(self) -> str:
        parts = []
        for user in sorted(self.pos.keys()):
            x, y = self.pos[user]
            parts.append(f"{user}({x},{y})[{self.score.get(user,0)}]")
        return "[Servidor] Estado atual: " + ", ".join(parts)

    def _check_winner(self) -> Optional[str]:
        tx, ty = self.treasure
        for user, (x, y) in self.pos.items():
            if (x, y) == (tx, ty):
                return user
        return None

    def _new_match(self):
        self.treasure = _random_treasure()
        self.used_hint.clear()
        self.used_suggest.clear()
        for user in list(self.pos.keys()):
            self.pos[user] = (1, 1)

    def _start_round_if_needed(self):
        if not self.user_by_addr:
            return
        # se não houver rodada em andamento
        if time.time() >= self.round_deadline:
            self.round_id += 1
            self.round_active_users = set(self.addr_by_user.keys())
            self.round_sent_cmd.clear()
            self.round_deadline = time.time() + self.round_secs
            self._broadcast(f"[Servidor] Início da rodada {self.round_id}! Envie um comando em até {self.round_secs}s.")
            # OBS.: não revelamos a posição do tesouro

    def _end_round(self):
        # elimina quem não enviou comando (apenas nesta rodada)
        missing = self.round_active_users - self.round_sent_cmd
        for user in missing:
            addr = self.addr_by_user.get(user)
            if addr:
                self._send(addr, "[Servidor] Você foi eliminado desta rodada por não enviar comando a tempo.")
        # divulga o estado após validações/movimentos
        self._broadcast(self._state_line())

        # vencedor?
        winner = self._check_winner()
        if winner:
            addr = self.addr_by_user.get(winner)
            port = addr[1] if addr else -1
            tx, ty = self.treasure
            self.score[winner] = self.score.get(winner, 0) + 1
            self._broadcast(f"[Servidor] O jogador {winner}:{port} encontrou o tesouro na posição ({tx},{ty})!")
            self._broadcast(f"[Servidor] Pontuação: {winner} = {self.score[winner]}")
            self._new_match()

        # zera o deadline para forçar o início da próxima rodada
        self.round_deadline = 0.0
        self.round_active_users.clear()
        self.round_sent_cmd.clear()

    def _handle_command(self, addr: Addr, text: str):
        text = text.strip()
        if not text:
            return
        parts = text.split()
        cmd = parts[0].lower()

        if cmd == "login":
            self._handle_login(addr, parts)
            return

        if cmd == "logout":
            self._logout(addr)
            return

        user = self._require_login(addr)
        if not user:
            return

        # qualquer comando conta para o timer (move / hint / suggest)
        if user in self.round_active_users:
            self.round_sent_cmd.add(user)

        if cmd == "move":
            if len(parts) != 2:
                self._send(addr, "[Servidor] Uso: move <up|down|left|right>")
                return
            msg = self._move(user, parts[1].lower())
            self._send(addr, msg)
            return

        if cmd == "hint":
            self._send(addr, self._hint(user))
            return

        if cmd == "suggest":
            self._send(addr, self._suggest(user))
            return

        self._send(addr, "[Servidor] Comando inválido. Use: login/logout/move/hint/suggest")

    def loop(self):
        print(f"[Servidor] HuntCin escutando em UDP :{self.port} (rodada={self.round_secs}s, loss={self.loss_prob})")
        self.round_deadline = 0.0

        while True:
            # inicia rodadas
            self._start_round_if_needed()

            # processa a rede
            self.rdt.process_incoming(timeout=0.1)
            while True:
                item = self.rdt.pop_delivered()
                if item is None:
                    break
                addr, payload = item
                try:
                    text = payload.decode("utf-8", errors="replace")
                except Exception:
                    continue
                self._handle_command(addr, text)

            # encerra a rodada ao atingir o deadline
            if self.user_by_addr and self.round_deadline and time.time() >= self.round_deadline:
                self._end_round()


def main():
    if len(sys.argv) < 2:
        print("Uso: python huntcin_server.py <porta_servidor> [duracao_rodada_seg] [loss_prob]")
        sys.exit(1)

    port = int(sys.argv[1])
    round_secs = int(sys.argv[2]) if len(sys.argv) >= 3 else 10
    loss = float(sys.argv[3]) if len(sys.argv) >= 4 else 0.0

    server = HuntCinServer(port=port, round_secs=round_secs, loss_prob=loss)
    server.loop()


if __name__ == "__main__":
    main()
