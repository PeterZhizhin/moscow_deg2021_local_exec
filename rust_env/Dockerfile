FROM rust:1.57

RUN apt-get update && apt-get install -y clang

RUN wget https://github.com/protocolbuffers/protobuf/releases/download/v3.7.1/protoc-3.7.1-linux-x86_64.zip \
    && unzip protoc-3.7.1-linux-x86_64.zip -d /usr \
    && rm protoc-3.7.1-linux-x86_64.zip

COPY . /usr/src/app
WORKDIR /usr/src/app

RUN cargo build --release

RUN apt-get install -y python3 python3-pip python3-pysodium

# This branch has the fix to use repeated config fields
RUN git clone https://github.com/PeterZhizhin/exonum-python-client /exonum_python_client
RUN python3 -m pip install -e /exonum_python_client --no-binary=protobuf
RUN python3 -m pip install exonum-launcher --no-binary=protobuf
