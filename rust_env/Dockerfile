FROM rust:1.76

RUN apt-get update && apt-get install -y clang python3 python3-pip python3-pysodium

RUN wget https://github.com/protocolbuffers/protobuf/releases/download/v3.7.1/protoc-3.7.1-linux-x86_64.zip \
    && unzip protoc-3.7.1-linux-x86_64.zip -d /usr \
    && rm protoc-3.7.1-linux-x86_64.zip

COPY . /usr/src/app
WORKDIR /usr/src/app

RUN cargo build --release

# This branch has the fix to use repeated config fields
RUN git clone https://github.com/PeterZhizhin/exonum-python-client /exonum_python_client
RUN python3 -m pip install --break-system-packages -e /exonum_python_client --no-binary=protobuf
RUN python3 -m pip install --break-system-packages exonum-launcher --no-binary=protobuf
RUN python3 -m pip install --force-reinstall --break-system-packages protobuf==3.20.0
