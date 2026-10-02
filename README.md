# DCompany - Sistema Distribuído de Conversão de Imagens

Projeto desenvolvido para implementar um sistema distribuído de conversão e armazenamento de imagens utilizando **RabbitMQ**, **Python** e **Docker**.

# !!PS: Está tudo em um só commit, porque fiz tudo localmente e testando e por último fiz o repositório!! #

O sistema permite a execução de múltiplos clientes, servidores de conversão e servidores de armazenamento.

## Funcionamento

Os clientes enviam imagens para uma fila compartilhada no RabbitMQ.

Os servidores de conversão consomem as imagens dessa fila, realizam a conversão para **tons de cinza** e publicam o resultado em uma exchange do tipo `fanout`.

Cada servidor de armazenamento possui sua própria fila ligada à exchange, garantindo que todos recebam e armazenem uma cópia de cada imagem convertida.

Os arquivos armazenados mantêm o mesmo nome das imagens originais.

### Arquitetura

```text
Cliente 1 ─┐
           │
Cliente 2 ─┴──> fila_imagens
                    │
             ┌──────┴──────┐
             ▼             ▼
        Conversor 1    Conversor 2
             │             │
             └──────┬──────┘
                    ▼
          imagens_convertidas
              (fanout)
              /     \
             ▼       ▼
       fila_storage1  fila_storage2
             │             │
             ▼             ▼
         Storage 1      Storage 2
             │             │
             ▼             ▼
     output/storage1  output/storage2
```

## Tecnologias

- Python 3.12
- RabbitMQ
- Pika
- Pillow
- Docker
- Docker Compose

## Estrutura do projeto

```text
dcompany-rabbitmq/
│
├── client/
│   └── client.py
│
├── converter/
│   └── converter.py
│
├── storage/
│   └── storage.py
│
├── images/
│   ├── client1/
│   └── client2/
│
├── output/
│   ├── storage1/
│   └── storage2/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

As imagens que serão enviadas devem ser colocadas nas pastas correspondentes aos clientes:

```text
images/client1/
images/client2/
```

As imagens processadas serão armazenadas em:

```text
output/storage1/
output/storage2/
```

## Executando com Docker

É necessário ter o **Docker** e o **Docker Compose** instalados.

Na raiz do projeto, execute:

```bash
docker compose up --build
```

O Docker iniciará automaticamente:

- 1 servidor RabbitMQ;
- 2 clientes;
- 2 servidores de conversão;
- 2 servidores de armazenamento.

Os clientes enviam automaticamente as imagens existentes em suas respectivas pastas.

Após o processamento, as imagens convertidas devem aparecer em:

```text
output/storage1/
output/storage2/
```

Todos os servidores de armazenamento devem possuir as mesmas imagens.

## RabbitMQ Management

A interface de gerenciamento do RabbitMQ fica disponível em:

```text
http://localhost:15673
```

Credenciais:

```text
Usuário: dcompany
Senha: dcompany123
```

Na interface é possível visualizar as filas, exchanges, conexões e consumidores utilizados pela aplicação.

## Parando a aplicação

Para encerrar os containers, utilize `Ctrl + C` no terminal em que o Docker Compose está executando.

Depois, se necessário, remova os containers com:

```bash
docker compose down
```

## Testando o sistema

Um teste pode ser realizado colocando diferentes imagens nas pastas dos dois clientes.

Exemplo:

```text
images/
├── client1/
│   ├── teste.png
│   └── teste1.png
│
└── client2/
    ├── teste2.png
    └── teste3.jpg
```

Execute:

```bash
docker compose up --build
```

Ao final do processamento, o resultado esperado é:

```text
output/
├── storage1/
│   ├── teste.png
│   ├── teste1.png
│   ├── teste2.png
│   └── teste3.jpg
│
└── storage2/
    ├── teste.png
    ├── teste1.png
    ├── teste2.png
    └── teste3.jpg
```

As imagens presentes nas pastas de saída estarão convertidas para tons de cinza e manterão seus nomes originais.

## Escalabilidade

Os clientes utilizam uma fila compartilhada chamada `fila_imagens`.

Quando existem múltiplos servidores de conversão, eles consomem mensagens dessa mesma fila, permitindo distribuir o processamento das imagens.

Após a conversão, as imagens são publicadas na exchange `imagens_convertidas`, do tipo `fanout`.

Cada servidor de armazenamento possui sua própria fila ligada a essa exchange. Dessa forma, cada imagem convertida é enviada para todos os servidores de armazenamento, garantindo redundância.
