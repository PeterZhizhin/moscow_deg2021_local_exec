import os

RABBIT_MQ_HOSTNAME = os.environ.get("RABBIT_MQ_HOSTNAME", "localhost")
RABBIT_MQ_PORT = os.environ.get("RABBIT_MQ_PORT", 5672)
RABBIT_MQ_LOGIN = os.environ.get("RABBIT_MQ_LOGIN", "guest")
RABBIT_MQ_PASSWORD = os.environ.get("RABBIT_MQ_PASSWORD", "guest")

ENCRYPTOR_URL = os.environ.get("ENCRYPTOR_URL", "http://localhost:8001")
ENCRYPTOR_SYSTEM = os.environ.get("ENCRYPTOR_SYSTEM", "TestSystem")
ENCRYPTOR_TOKEN = os.environ.get("ENCRYPTOR_TOKEN", "TOKEN_SECRET")

BLOCKCHAIN_PROCESS_VOTE_URI = os.environ.get("BLOCKCHAIN_PROXY_URI", "http://localhost:8021/process_vote")

BASE_LISTEN_QUEUE_NAME = os.environ.get("BASE_LISTEN_QUEUE_NAME", "mgik_queue")
ARM_VOITING_URL = os.environ.get("ARM_VOITING_URL", "http://localhost:8022/arm/config?empty_ok=true")

LISTEN_PORT = os.environ.get("LISTEN_PORT", 8024)
