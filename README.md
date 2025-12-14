# Projeto de Infracom 2025.2 — UDP + RDT 3.0 + HuntCin (Etapa 3)

## Equipe 2

- João Pedro Felix da Silva
- Thaylson Fernando da Silva 
- Igor Vasconcelos Antero

## Descrição do projeto

O objetivo desta entrega é construir uma aplicação distribuída **cliente/servidor** que funcione sobre **UDP** (sem garantias de entrega), porém adicionando confiabilidade por meio do **RDT 3.0** (Stop-and-Wait com ACK e retransmissão).  
Sobre essa base, foi implementado o jogo **HuntCin**, com múltiplos jogadores conectados simultaneamente e coordenação por rodadas com temporizador.

---

## Visão geral da Etapa 3 — HuntCin

- O jogo ocorre em um **grid 3x3**, com posições (x,y) indo de **1 a 3**.
- Todos os jogadores iniciam em **(1,1)**.
- Existe um **tesouro** em alguma posição do grid.
- Os jogadores enviam comandos ao servidor e tentam encontrar o tesouro.

### Funcionalidades implementadas

- **Múltiplos clientes simultâneos** (cada cliente em uma porta local diferente).
- **Login/Logout** com validação de **nome único**.
- **Movimentação** no grid com validação para impedir sair do 3x3.
- **Rodadas com temporizador** (ex.: 10s):
  - se o jogador **não enviar comando dentro do tempo**, ele é **eliminado da rodada**.
- Ao final da rodada:
  - o servidor envia **broadcast** do **estado atual** (posições e pontuação).
- Quando alguém encontra o tesouro:
  - o servidor anuncia o vencedor e **reinicia a partida mantendo a pontuação**.
- Comandos especiais:
  - `hint` (**1 vez por partida**) → dica textual de direção
  - `suggest` (**1 vez por partida**) → sugestão de movimento para aproximar do tesouro

---

## Estrutura dos arquivos

- `huntcin_server.py`  
  Servidor do jogo HuntCin: coordena rodadas, valida comandos, mantém estado, broadcast.
- `huntcin_client.py`  
  Cliente interativo via terminal: envia comandos e imprime respostas do servidor.
- `rdt3_transport.py`  
  Camada **RDT 3.0 (Stop-and-Wait)** sobre UDP (seq 0/1, ACK, retransmissão por timeout).

---

## Requisitos

- Python **3.9+** (recomendado)
- Linux / macOS / Windows

---

## Como executar

Abra **3 terminais** na pasta do projeto.

### 1) Iniciar o servidor (Terminal 1)

**Sintaxe:**
```bash
python huntcin_server.py <porta_servidor> [duracao_rodada_seg] [loss_prob]
```

**Exemplo (rodada de 10s):**
```bash
python huntcin_server.py 5000 10
```

**Exemplo com simulação de perda (20%):**
```bash
python huntcin_server.py 5000 10 0.2
```

> `loss_prob` é opcional e serve para simular perdas de pacotes e testar o RDT 3.0.

---

### 2) Iniciar clientes (Terminal 2 e Terminal 3)

> Importante: cada cliente precisa usar uma **porta local diferente**.

**Sintaxe:**
```bash
python huntcin_client.py <ip_servidor> <porta_servidor> <porta_local_cliente> [loss_prob]
```

**Cliente 1:**
```bash
python huntcin_client.py 127.0.0.1 5000 5001
```

**Cliente 2:**
```bash
python huntcin_client.py 127.0.0.1 5000 5002
```

**Cliente com simulação de perda (20%):**
```bash
python huntcin_client.py 127.0.0.1 5000 5001 0.2
```

#### Rodando em máquinas diferentes
- No servidor: use `python huntcin_server.py 5000 10`
- No cliente: substitua `127.0.0.1` pelo **IP real do servidor** (ex.: `192.168.0.10`)
- Garanta que a porta do servidor esteja liberada no firewall.

---

## Comandos do jogo

### `login <nome>`
Conecta o jogador ao servidor com um nome único.

Exemplo:
```txt
login joao
```

### `logout`
Sai do jogo.

Exemplo:
```txt
logout
```

### `move up|down|left|right`
Move o jogador no grid 3x3. Se sair do grid, o servidor rejeita.

Exemplos:
```txt
move up
move right
```

### `hint` (apenas 1 vez por partida)
Retorna uma dica textual sobre onde o tesouro está.

Exemplo:
```txt
hint
```

### `suggest` (apenas 1 vez por partida)
Retorna uma sugestão de movimento para aproximar do tesouro.

Exemplo:
```txt
suggest
```

---

## Como testar (checklist rápido)

### Teste 1 — Múltiplos clientes e login
1. Inicie o servidor
2. Inicie 2 clientes com portas locais diferentes (ex.: 5001 e 5002)
3. Faça login em cada um:
   - Cliente 1: `login joao`
   - Cliente 2: `login ana`
4. Tente repetir nome:
   - Cliente 2: `login joao` → deve falhar (nome já em uso)

### Teste 2 — Rodada e eliminação por tempo
- Aguarde o servidor iniciar a rodada
- Em um cliente, **não envie comando**
- Espere acabar o tempo → esse cliente deve receber mensagem de eliminação da rodada

### Teste 3 — Movimento válido e inválido
- A partir de (1,1):
  - `move left` → inválido (fora do grid)
  - `move up` → válido

### Teste 4 — Hint e Suggest (apenas 1x por partida)
- `hint` duas vezes → a segunda deve ser bloqueada
- `suggest` duas vezes → a segunda deve ser bloqueada

### Teste 5 — Broadcast do estado
- Após o fim da rodada, ambos os clientes devem receber algo como:
  - `[Servidor] Estado atual: ...`

### Teste 6 — Confiabilidade do RDT 3.0 (com perdas)
- Rode servidor e clientes com `loss_prob` (ex.: 0.2)
- Mesmo com perdas, os comandos devem continuar chegando (por retransmissão/ACK).

---

## Notas sobre confiabilidade (RDT 3.0)

A comunicação é feita sobre UDP, mas toda mensagem passa pela camada `RDT3Transport`, que implementa:

- **Stop-and-Wait** com sequência **0/1**
- **ACK** para confirmação de entrega
- **Timeout + retransmissão**
- **Tratamento de duplicatas** (descarta mensagens repetidas)

Isso permite que a aplicação continue funcionando mesmo com simulação de perda (`loss_prob`).

---

## Exemplos completos de execução

Servidor:
```bash
python huntcin_server.py 5000 10 0.2
```

Cliente 1:
```bash
python huntcin_client.py 127.0.0.1 5000 5001 0.2
```

Cliente 2:
```bash
python huntcin_client.py 127.0.0.1 5000 5002 0.2
```
