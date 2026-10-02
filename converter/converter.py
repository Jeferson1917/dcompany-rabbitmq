import io
import os
import pika
import time
from PIL import Image


# Configurações para conexão com o RabbitMQ, os valores podem ser alterados por variáveis de ambiente quando a aplicação estiver rodando no Docker.
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5673"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "dcompany")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "dcompany123")

# Nome da fila onde estão as imagens enviadas pelos clientes.
QUEUE_NAME = "fila_imagens"

# Nome da exchange que vai distribuir as imagens convertidas para os servidores de armazenamento.
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


# Função executada sempre que uma imagem é recebida da fila.
def processar_imagem(channel, method, properties, body):

    # Recupera o nome original da imagem que foi enviado pelo cliente no header da mensagem.
    nome_arquivo = properties.headers["filename"]

    print(f"Imagem recebida para conversão: {nome_arquivo}")

    # Abre a imagem recebida através dos bytes enviados pelo RabbitMQ.
    imagem = Image.open(io.BytesIO(body))

    # Converte a imagem para tons de cinza.
    imagem_cinza = imagem.convert("L")

    # Cria um espaço em memória para armazenar os bytes da imagem já convertida.
    imagem_convertida = io.BytesIO()

    # Identifica o formato original da imagem para manter o mesmo tipo de arquivo.
    formato = imagem.format

    # Salva a imagem convertida em memória mantendo o formato original, como PNG ou JPEG.
    imagem_cinza.save(
        imagem_convertida,
        format=formato
    )

    # Pega os bytes da imagem convertida para enviar novamente pelo RabbitMQ.
    dados_convertidos = imagem_convertida.getvalue()

    # Publica a imagem convertida na exchange para que depois todos os servidores de armazenamento recebam uma cópia.
    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key="",
        body=dados_convertidos,
        properties=pika.BasicProperties(
            delivery_mode=2,
            headers={
                "filename": nome_arquivo
            }
        )
    )

    # Confirma para o RabbitMQ que a imagem foi processada corretamente.
    channel.basic_ack(
        delivery_tag=method.delivery_tag
    )

    print(f"Imagem convertida com sucesso: {nome_arquivo}")


def iniciar_conversor():

    connection = conectar_rabbitmq()
    channel = connection.channel()

    # Garante que a fila das imagens exista.
    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True
    )

    # Cria uma exchange do tipo fanout, que futuramente vai distribuir cada imagem para todos os servidores de armazenamento.
    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="fanout",
        durable=True
    )

    # Faz com que cada conversor receba uma imagem por vez antes de receber outro trabalho.
    channel.basic_qos(
        prefetch_count=1
    )

    # Define que esse servidor vai consumir as imagens da fila.
    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=processar_imagem
    )

    print("Servidor de conversão aguardando imagens...")

    # Mantém o servidor executando e esperando novas imagens.
    channel.start_consuming()


if __name__ == "__main__":
    iniciar_conversor()