# Projeto de Infracom 2025.2 — UDP + RDT 3.0 + HuntCin (Etapa 3)

## Equipe 2

- João Pedro Felix da Silva
- Thaylson Fernando da Silva 
- Igor Vasconcelos Antero

## Descrição

Este projeto implementa, em Python, uma aplicação baseada em sockets UDP com uma camada de confiabilidade RDT 3.0 (Stop-and-Wait). O objetivo é garantir entrega confiável de mensagens mesmo em um transporte não confiável (UDP), além de exercitar a construção de uma aplicação distribuída com comunicação cliente/servidor.

Ênfase: Etapa 3 — HuntCin (jogo em rede)

Na Etapa 3, foi implementado o jogo HuntCin, executado sobre UDP com RDT 3.0, permitindo a execução de múltiplos clientes simultaneamente (cada cliente em uma porta local diferente) conectados ao mesmo servidor. O servidor mantém o estado do jogo em um grid 3x3, gerencia rodadas com temporizador e faz broadcast do estado para todos os jogadores.

A comunicação entre cliente e servidor utiliza a camada RDT3Transport, que implementa Stop-and-Wait com ACK e retransmissão, garantindo que comandos e mensagens de estado cheguem corretamente mesmo com perdas simuladas.

## Estrutura

- **Entrega 1/2 — Envio e devolução de arquivos via UDP (com confiabilidade)**
  - `udp_server.py` — servidor UDP que recebe um arquivo e devolve
  - `udp_client.py` — cliente UDP que envia um arquivo e recebe de volta
  - `rdt3.py` — implementação base do RDT 3.0 (Stop-and-Wait) utilizada pela etapa de arquivos

- **Entrega 3 — Jogo HuntCin (UDP + RDT 3.0)**
  - `huntcin_server.py` — servidor do jogo
  - `huntcin_client.py` — cliente do jogo
  - `rdt3_transport.py` — transporte **RDT 3.0 para mensagens**, usado pelo HuntCin

---

## Como rodar — Entrega 1/2 (Arquivo)

### Servidor (terminal 1)
```bash
python udp_server.py 5000
```

Opcional: simular perda (ex.: 30%)
```bash
python udp_server.py 5000 0.3
```

### Cliente (terminal 2)
```bash
python udp_client.py 127.0.0.1 5000 caminho/do/arquivo.ext
```

Validação rápida:
- o servidor deve receber o arquivo e depois devolver;
- o cliente deve salvar/confirmar o arquivo devolvido.

---

## Como rodar — Entrega 3 (HuntCin)

Requisitos atendidos:
- **mais de um cliente ao mesmo tempo**, cada um em porta diferente;
- comandos: `login`, `logout`, `move`, `hint`, `suggest`;
- rodada com temporizador (quem não manda comando é eliminado da rodada);
- estado do jogo broadcast para todos.

### Servidor (terminal 1)
```bash
python huntcin_server.py 5000 10
```

Opcional: simular perda (ex.: 20%)
```bash
python huntcin_server.py 5000 10 0.2
```

### Cliente 1 (terminal 2)
```bash
python huntcin_client.py 127.0.0.1 5000 5001
```

### Cliente 2 (terminal 3)
```bash
python huntcin_client.py 127.0.0.1 5000 5002
```

Opcional: simular perda também no cliente
```bash
python huntcin_client.py 127.0.0.1 5000 5001 0.2
```

---

## Comandos do HuntCin (no cliente)

- `login <nome>` — entra no jogo (**nomes precisam ser únicos**)
- `logout` — sai do jogo
- `move up|down|left|right` — move no grid 3x3 (servidor valida)
- `hint` — dica **1x por partida**
- `suggest` — sugestão **1x por partida**

Checklist de teste:
1. `login joao` em um cliente e `login ana` no outro.
2. Tentar `login joao` no segundo cliente → deve ser recusado (nome duplicado).
3. A cada rodada, mandar um comando dentro de 10s. Se ficar em silêncio, o servidor elimina da rodada.
4. Usar `hint` duas vezes → a segunda deve ser negada.
5. Usar `suggest` duas vezes → a segunda deve ser negada.
6. Movimentar até alguém achar o tesouro → servidor anuncia e pontuação é atualizada.

