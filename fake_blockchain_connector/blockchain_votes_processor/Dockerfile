FROM python:alpine

RUN apk add netcat-openbsd protoc git protobuf-dev libsodium

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Fix broken ctype.util.find_library in Alpine by providing full path to libsodium
RUN sed -i -e 's/\(ctypes.util.find_library.*\)/"\/usr\/lib\/libsodium.so.26"\)/g' /usr/local/lib/python3.12/site-packages/pysodium/__init__.py

COPY . /app
WORKDIR /app

RUN mkdir -p /app/exonum_modules/main && find /app/proto -type f -name "*.proto" | xargs protoc -I=/usr/include/ -I=/app/proto --python_out=/app/exonum_modules/main
RUN python -m pytest /app

CMD ["/app/wait-for-rabbit-mq.sh", "python", "main.py"]
