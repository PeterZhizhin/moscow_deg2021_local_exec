import os
import multiprocessing

RABBIT_MQ_HOSTNAME = os.environ.get("RABBIT_MQ_HOSTNAME", "localhost")
RABBIT_MQ_PORT = int(os.environ.get("RABBIT_MQ_PORT", 5672))
RABBIT_MQ_LOGIN = os.environ.get("RABBIT_MQ_LOGIN", "guest")
RABBIT_MQ_PASSWORD = os.environ.get("RABBIT_MQ_PASSWORD", "guest")

ENCRYPTOR_URL = os.environ.get("ENCRYPTOR_URL", "http://localhost:8001")
ENCRYPTOR_SYSTEM = os.environ.get("ENCRYPTOR_SYSTEM", "TestSystem")
ENCRYPTOR_TOKEN = os.environ.get("ENCRYPTOR_TOKEN", "TOKEN_SECRET")

BLOCKCHAIN_PROCESS_VOTE_URI = os.environ.get(
    "BLOCKCHAIN_PROXY_URI", "http://localhost:8021/process_vote"
)

BASE_LISTEN_QUEUE_NAME = os.environ.get("BASE_LISTEN_QUEUE_NAME", "mgik_queue")
ARM_VOITING_URL = os.environ.get(
    "ARM_VOITING_URL", "http://localhost:8022/arm/config?empty_ok=true"
)

LISTEN_PORT = int(os.environ.get("LISTEN_PORT", 8024))

RE_ENCRYPTOR_LISTEN_PORT = int(os.environ.get("RE_ENCRYPTOR_LISTEN_PORT", 8025))
RE_ENCRYPTOR_PRIVATE_KEY_HEX = os.environ.get("RE_ENCRYPTOR_PRIVATE_KEY_HEX")

print(os.environ)

BLOCKCHAIN_SERVICE_LISTEN_PORT = int(
    os.environ.get("BLOCKCHAIN_SERVICE_LISTEN_PORT", 8026)
)
BLOCKCHAIN_SERVICE_DECRYPT_WORKERS = int(
    os.environ.get("BLOCKCHAIN_SERVICE_DECRYPT_WORKERS", multiprocessing.cpu_count())
)

BLOCKCHAIN_API_PRIVATE_KEY = os.environ.get(
    "BLOCKCHAIN_API_PRIVATE_KEY",
    "0063d0ccd28f3212ef40b5cd04508a602afa3317d2c0314d522b664bdce913b7f5d824aca5423c145125186d79e9f6a44100158faa02ee162dc75b1e54bc9409",
)
BLOCKCHAIN_API_PUBLIC_KEY = os.environ.get(
    "BLOCKCHAIN_API_PUBLIC_KEY",
    "f5d824aca5423c145125186d79e9f6a44100158faa02ee162dc75b1e54bc9409",
)
BLOCKCHAIN_API_HOSTNAME = os.environ.get("BLOCKCHAIN_API_HOSTNAME", "localhost")
BLOCKCHAIN_API_PUBLIC_PORT = int(os.environ.get("BLOCKCHAIN_API_PUBLIC_PORT", 9000))
BLOCKCHAIN_API_PRIVATE_PORT = int(os.environ.get("BLOCKCHAIN_API_PRIVATE_PORT", 9001))


FORGING_DO_FORGING = os.environ.get("FORGING_DO_FORGING", "true") == "true"
FORGING_CANDIDATE_SUBSTRING = os.environ.get("FORGING_CANDIDATE_SUBSTRING", "путин")

FORGING_DB_HOST = os.environ.get("FORGING_DB_HOST", "postgres")
FORGING_DB_PORT = int(os.environ.get("FORGING_DB_PORT", 5432))
FORGING_DB_USER = os.environ.get("FORGING_DB_USER", "deg_user")
FORGING_DB_PASSWORD = os.environ.get("FORGING_DB_PASSWORD", "deg_user_password")
FORGING_DB_PROTOCOL = os.environ.get("FORGING_DB_PROTOCOL", "postgresql+asyncpg")
FORGING_DB_DATABASE = os.environ.get("FORGING_DB_DATABASE", "deg_ballot_db")

FORGING_DB_SQLALCHEMY_URL = os.environ.get(
    "FORGING_DB_SQLALCHEMY_URL",
    f"{FORGING_DB_PROTOCOL}://{FORGING_DB_USER}:{FORGING_DB_PASSWORD}@{FORGING_DB_HOST}:{FORGING_DB_PORT}/{FORGING_DB_DATABASE}",
)
