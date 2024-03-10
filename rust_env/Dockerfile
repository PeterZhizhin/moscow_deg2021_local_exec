FROM rust:1.76 as build

RUN apt-get update && apt-get install -y clang wget unzip && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/protocolbuffers/protobuf/releases/download/v3.7.1/protoc-3.7.1-linux-x86_64.zip \
    && unzip protoc-3.7.1-linux-x86_64.zip -d /usr \
    && rm protoc-3.7.1-linux-x86_64.zip

COPY . /usr/src/app
WORKDIR /usr/src/app

RUN cargo build --release

FROM ubuntu:24.04

RUN apt-get update && apt-get install -y python3 python3-pip python3-pysodium wget unzip git && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/protocolbuffers/protobuf/releases/download/v3.7.1/protoc-3.7.1-linux-x86_64.zip \
    && unzip protoc-3.7.1-linux-x86_64.zip -d /usr \
    && rm protoc-3.7.1-linux-x86_64.zip

# This branch has the fix to use repeated config fields
RUN git clone https://github.com/PeterZhizhin/exonum-python-client /exonum_python_client
RUN python3 -m pip install --break-system-packages -e /exonum_python_client --no-binary=protobuf
RUN python3 -m pip install --break-system-packages exonum-launcher --no-binary=protobuf
RUN python3 -m pip install --force-reinstall --break-system-packages protobuf==3.20.0

RUN mkdir -p /usr/src/app/target/release
COPY --from=build /usr/src/app/target/release/dit-* /usr/src/app/target/release/
