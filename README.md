# Comunicação UDP para Envio e Devolução de Arquivos

## Equipe 2

- João Pedro Felix da Silva
- Keroly dos Santos silva 
- Thaylson Fernando da Silva 
- Igor Vasconcelos Antero

## Descrição

Este projeto implementa um cliente e um servidor em **Python** usando **UDP** (`socket`).  
O cliente envia um arquivo (texto, imagem, etc.) em pacotes de até **1024 bytes** para o servidor.  
O servidor salva o arquivo e depois **devolve o mesmo arquivo** para o cliente com o nome alterado.

---

## Arquivos do projeto

- `udp_server.py` – código do servidor UDP  
- `udp_client.py` – código do cliente UDP  
- Arquivos de teste (ex.: `exemplo.txt`, `foto.png`)

---

## Como executar

### 1. Iniciar o servidor

No terminal, dentro da pasta do projeto:

```bash
python udp_server.py 5000 0.2
```

O servidor ficará escutando na porta `5000` aguardando arquivos.

---

### 2. Rodar o cliente com um arquivo de texto

Em outro terminal, também na pasta do projeto:

```bash
python udp_client.py 127.0.0.1 5000 exemplo.txt 0.2
```

- `127.0.0.1` → IP do servidor (localhost)  
- `5000` → porta do servidor  
- `exemplo.txt` → arquivo a ser enviado

---

### 3. Rodar o cliente com uma imagem (ou outro tipo de arquivo)

```bash
python udp_client.py 127.0.0.1 5000 foto.png 0.2
```

(use o nome do arquivo de imagem que você quiser)

---

## Resultados esperados

Após executar:

- No **servidor**:
  - Um arquivo salvo com nome `server_<nome_original>`  
    (ex.: `server_exemplo.txt`, `server_foto.png`).

- No **cliente**:
  - Um arquivo devolvido com nome `devolvido_<nome_original>`  
    (ex.: `devolvido_exemplo.txt`, `devolvido_foto.png`).

O conteúdo dos arquivos `devolvido_*` deve ser igual ao dos arquivos originais enviados pelo cliente.
