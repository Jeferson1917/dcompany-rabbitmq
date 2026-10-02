import os
import sys
import pika
import time

# Configurações para conexão com o RabbitMQ, os valores podem ser alterados por variáveis de ambiente quando a aplicação estiver rodando no Docker.
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5673"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "dcompany")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "dcompany123")

# Nome da exchange onde os conversores publicam as imagens já convertidas.
EXCHANGE_NAME = "imagens_convertidas"


# Tenta conectar ao RabbitMQ e aguarda alguns segundos caso o servidor ainda esteja iniciando.
def conectar_rabbitmq():
    credentials = pika.PlainCredentials(
        RABBITMQ_USER,
        RABBITMQ_PASSWORD
    )

    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    credentials=credentials
                )
            )

            return connection

        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ ainda não está disponível. Tentando novamente em 3 segundos...")
            time.sleep(3)


# Inicia um servidor de armazenamento.
def iniciar_storage(nome_servidor, pasta_saida):
    connection = conectar_rabbitmq()
    channel = connection.channel()

    # Garante que a exchange de imagens convertidas exista.
    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="fanout",
        durable=True
    )

    # Cada servidor possui sua própria fila, permitindo que todos recebam uma cópia de cada imagem.
    nome_fila = f"fila_{nome_servidor}"

    channel.queue_declare(
        queue=nome_fila,
        durable=True
    )

    # Liga a fila deste servidor à exchange fanout.
    channel.queue_bind(
        exchange=EXCHANGE_NAME,
        queue=nome_fila
    )

    # Cria a pasta de armazenamento caso ela ainda não exista.
    os.makedirs(
        pasta_saida,
        exist_ok=True
    )

    # Função executada sempre que uma imagem convertida chega neste servidor.
    def armazenar_imagem(channel, method, properties, body):

        # Recupera o nome original da imagem enviado no header da mensagem.
        nome_arquivo = properties.headers["filename"]

        # Monta o caminho onde a imagem será salva mantendo seu nome original.
        caminho_saida = os.path.join(
            pasta_saida,
            nome_arquivo
        )

        # Salva os bytes recebidos como arquivo na pasta deste servidor.
        with open(caminho_saida, "wb") as arquivo:
            arquivo.write(body)

        # Confirma para o RabbitMQ que a imagem foi armazenada corretamente.
        channel.basic_ack(
            delivery_tag=method.delivery_tag
        )

        print(f"[{nome_servidor}] Imagem armazenada: {nome_arquivo}")

    # Define que este servidor vai consumir as mensagens da sua própria fila.
    channel.basic_consume(
        queue=nome_fila,
        on_message_callback=armazenar_imagem
    )

    print(
        f"Servidor {nome_servidor} aguardando imagens "
        f"em {pasta_saida}..."
    )

    # Mantém o servidor executando e esperando novas imagens.
    channel.start_consuming()


if __name__ == "__main__":

    # O programa recebe o nome do servidor e a pasta onde ele deve armazenar as imagens.
    # Exemplo: python storage/storage.py storage1 output/storage1
    if len(sys.argv) != 3:
        print(
            "Uso: python storage/storage.py "
            "<nome_servidor> <pasta_saida>"
        )
        sys.exit(1)

    iniciar_storage(
        sys.argv[1],
        sys.argv[2]
    )