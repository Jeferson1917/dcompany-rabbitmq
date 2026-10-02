import os
import time
import sys
import pika


# Configurações para conexão com o RabbitMQ, os valores podem ser alterados por variáveis de ambiente quando a aplicação estiver rodando no Docker.
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5673"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "dcompany")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "dcompany123")

# Nome da fila onde os clientes vão enviar as imagens para serem processadas pelos servidores de conversão.
QUEUE_NAME = "fila_imagens"

# Extensões de imagens aceitas pelo cliente.
EXTENSOES_VALIDAS = (".png", ".jpg", ".jpeg")


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


# Envia uma imagem para a fila usando uma conexão já aberta com o RabbitMQ.
def enviar_imagem(channel, caminho_imagem):

    # Pega somente o nome do arquivo para manter o mesmo nome da imagem original quando ela for armazenada.
    nome_arquivo = os.path.basename(caminho_imagem)

    # Abre a imagem em modo binário e lê seus bytes para poder enviar pelo RabbitMQ.
    with open(caminho_imagem, "rb") as arquivo:
        imagem = arquivo.read()

    # Envia os bytes da imagem para a fila e coloca o nome original do arquivo no header da mensagem.
    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=imagem,
        properties=pika.BasicProperties(
            delivery_mode=2,
            headers={
                "filename": nome_arquivo
            }
        )
    )

    print(f"Imagem enviada: {nome_arquivo}")


# Recebe uma pasta e envia todas as imagens encontradas dentro dela.
def enviar_pasta(caminho_pasta):

    # Verifica se a pasta informada realmente existe.
    if not os.path.isdir(caminho_pasta):
        print(f"Pasta não encontrada: {caminho_pasta}")
        return

    connection = conectar_rabbitmq()
    channel = connection.channel()

    # Cria a fila caso ela ainda não exista, durable mantém a fila caso o RabbitMQ seja reiniciado.
    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True
    )

    quantidade_enviada = 0

    # Percorre os arquivos da pasta do cliente.
    for nome_arquivo in sorted(os.listdir(caminho_pasta)):

        # Ignora arquivos que não possuem uma extensão de imagem aceita.
        if not nome_arquivo.lower().endswith(EXTENSOES_VALIDAS):
            continue

        caminho_imagem = os.path.join(
            caminho_pasta,
            nome_arquivo
        )

        # Garante que estamos tentando enviar um arquivo e não outra pasta.
        if os.path.isfile(caminho_imagem):
            enviar_imagem(
                channel,
                caminho_imagem
            )
            quantidade_enviada += 1

    # Fecha a conexão somente depois que todas as imagens da pasta foram enviadas.
    connection.close()

    print(f"Total de imagens enviadas: {quantidade_enviada}")


# Executa o envio quando o arquivo client.py é chamado pelo terminal.
if __name__ == "__main__":

    # Verifica se foi passado o caminho da pasta, exemplo: python client/client.py images/client1
    if len(sys.argv) != 2:
        print("Uso: python client/client.py <pasta_de_imagens>")
        sys.exit(1)

    enviar_pasta(sys.argv[1])