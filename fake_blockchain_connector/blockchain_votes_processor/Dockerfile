FROM python:alpine

RUN apk add netcat-openbsd

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app
WORKDIR /app

CMD ["/app/wait-for-rabbit-mq.sh", "python", "main.py"]
