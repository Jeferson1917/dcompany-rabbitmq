# Usa uma imagem leve do Python 3.12 como base para os programas da aplicação.
FROM python:3.12-slim

# Define /app como pasta principal dentro do container.
WORKDIR /app

# Copia o arquivo com as dependências Python para dentro do container.
COPY requirements.txt .

# Instala as bibliotecas necessárias para RabbitMQ e processamento das imagens.
RUN pip install --no-cache-dir -r requirements.txt

# Copia os arquivos do projeto para dentro do container.
COPY . .