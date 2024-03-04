import dataclasses
import logging
import os
import sys

import nacl.exceptions
import nacl.public
import nacl.utils
import exonum_client
from exonum_client import crypto as exonum_crypto
from google.protobuf import message as protobuf_message

# Add compiled protos to the current path, since it's required by protoc
sys.path.append(os.path.join(os.path.dirname(__file__), "exonum_modules", "main"))

from exonum_modules.main import transactions_pb2
from exonum_modules.main import custom_types_pb2
from exonum_modules.main import schema_pb2
from exonum_modules.main.exonum import messages_pb2

_INSTANCE_ID = 1001
_TX_STORE_BALLOT_METHOD_ID = 6

logger = logging.getLogger(__file__)


@dataclasses.dataclass(frozen=True)
class _EncryptedMessage:
    encrypted_data: bytes
    public_key: bytes
    nonce: bytes


@dataclasses.dataclass(frozen=True)
class ReEncryptionResult:
    transaction_hex: str
    voter_address_hex: str


def _parse_store_tx_from_raw_hex(
    store_ballot_transaction: bytes,
) -> transactions_pb2.TxStoreBallot:
    try:
        signed_message = messages_pb2.SignedMessage()
        signed_message.ParseFromString(store_ballot_transaction)
        core_message = messages_pb2.CoreMessage()
        core_message.ParseFromString(signed_message.payload)
        tx_store_ballot = transactions_pb2.TxStoreBallot()
        tx_store_ballot.ParseFromString(core_message.any_tx.arguments)
        return tx_store_ballot
    except protobuf_message.DecodeError as e:
        logging.warning(
            f"Got protobuf decode error when parsing store ballot tx, returning empty tx: {e}"
        )
        return transactions_pb2.TxStoreBallot()


def _encrypt_on_public_key(data: bytes, public_key: nacl.public.PublicKey):
    private_key = nacl.public.PrivateKey.generate()
    nonce = nacl.utils.random(nacl.public.Box.NONCE_SIZE)

    box = nacl.public.Box(private_key, public_key)

    encrypted_message = box.encrypt(plaintext=data, nonce=nonce)
    return _EncryptedMessage(
        encrypted_data=encrypted_message[nacl.public.Box.NONCE_SIZE :],
        public_key=private_key.public_key.encode(),
        nonce=nonce,
    )


def _ecnrypted_message_to_tx_store_ballot_message(
    *,
    encrypted_message: _EncryptedMessage,
    district_id: int,
    voting_id: str,
    sid: str,
) -> transactions_pb2.TxStoreBallot:
    return transactions_pb2.TxStoreBallot(
        voting_id=voting_id,
        district_id=district_id,
        encrypted_choice=transactions_pb2.TxEncryptedChoice(
            encrypted_message=encrypted_message.encrypted_data,
            nonce=custom_types_pb2.SealedBoxNonce(
                data=encrypted_message.nonce,
            ),
            public_key=custom_types_pb2.SealedBoxPublicKey(
                data=encrypted_message.public_key,
            ),
        ),
        sid=sid,
    )


def _tx_store_ballot_to_exonum_message_hex(
    tx_store_ballot: transactions_pb2.TxStoreBallot,
) -> ReEncryptionResult:
    new_voter_key = exonum_crypto.KeyPair.generate()
    exonum_message = exonum_client.ExonumMessage(
        instance_id=_INSTANCE_ID,
        message_id=_TX_STORE_BALLOT_METHOD_ID,
        msg=tx_store_ballot,
    )
    exonum_message.sign(new_voter_key)
    signed_raw = exonum_message.signed_raw()
    assert signed_raw is not None
    transaction_hex = signed_raw.hex()
    voter_address_hex = new_voter_key.public_key.value.hex()
    return ReEncryptionResult(
        transaction_hex=transaction_hex,
        voter_address_hex=voter_address_hex,
    )


def re_encrypt_blockchain_message_with_sid(
    *,
    store_ballot_transaction: bytes,
    re_encryption_public_key: nacl.public.PublicKey,
    sid: str,
    voting_id: str,
    district_id: int,
) -> ReEncryptionResult:
    if not sid:
        raise ValueError("Empty SID")
    if not voting_id:
        raise ValueError("Invalid voting_id")
    if not district_id:
        raise ValueError("Invalid district_id")
    tx_store_ballot = _parse_store_tx_from_raw_hex(store_ballot_transaction)

    encrypted_choice_serialized = tx_store_ballot.encrypted_choice.SerializeToString()
    encrypted_choice_encrypted = _encrypt_on_public_key(
        data=encrypted_choice_serialized,
        public_key=re_encryption_public_key,
    )

    re_encrypted_tx_store_ballot = _ecnrypted_message_to_tx_store_ballot_message(
        encrypted_message=encrypted_choice_encrypted,
        district_id=district_id,
        voting_id=voting_id,
        sid=sid,
    )

    return _tx_store_ballot_to_exonum_message_hex(
        tx_store_ballot=re_encrypted_tx_store_ballot
    )


def _decrypt_message(
    message: bytes,
    nonce: bytes,
    public_key_bytes: bytes,
    private_key: nacl.public.PrivateKey,
) -> bytes | None:
    try:
        public_key = nacl.public.PublicKey(public_key_bytes)
        box = nacl.public.Box(private_key, public_key)
        return box.decrypt(message, nonce=nonce)
    except nacl.exceptions.CryptoError as e:
        logging.warning(
            f"Got crypto error when decrypting a message, returning None: {e}"
        )
    return None


def _decode_choices_proto(choices_encoded: bytes) -> list[int] | None:
    if len(choices_encoded) < 2:
        logging.warning(f"Got too short choices message: {choices_encoded.hex()}")
        return None
    offset = ((choices_encoded[0] << 8) | choices_encoded[1]) + 2
    if len(choices_encoded) < offset:
        logging.warning(
            f"Got choices message shorter than offset: {choices_encoded.hex()}, offset: {offset}"
        )
        return None
    original_message = choices_encoded[offset:]
    choices_proto = schema_pb2.Choices()
    try:
        choices_proto.ParseFromString(original_message)
    except protobuf_message.DecodeError:
        return None
    return list(choices_proto.data)


def _decrypt_tx_encrypted_choice(
    tx: transactions_pb2.TxEncryptedChoice,
    private_key: nacl.public.PrivateKey,
) -> bytes | None:
    return _decrypt_message(
        message=tx.encrypted_message,
        nonce=tx.nonce.data,
        public_key_bytes=tx.public_key.data,
        private_key=private_key,
    )


def decrypt_re_encrypted_tx(
    *,
    re_encrypted_tx_encrypted_vote: transactions_pb2.TxEncryptedChoice,
    re_encryption_private_key: nacl.public.PrivateKey,
    first_layer_private_key: nacl.public.PrivateKey,
) -> list[int] | None:
    first_layer_decrypted = _decrypt_tx_encrypted_choice(
        re_encrypted_tx_encrypted_vote, re_encryption_private_key
    )

    if first_layer_decrypted is None:
        logging.warning("Got second layer None decryption")
        return None

    first_layer_tx = transactions_pb2.TxEncryptedChoice()
    try:
        first_layer_tx.ParseFromString(first_layer_decrypted)
    except protobuf_message.DecodeError as e:
        logging.warning(f"Got protobuf decode error, returning None: {e}")
        return None

    second_layer_decrypted = _decrypt_tx_encrypted_choice(
        first_layer_tx,
        first_layer_private_key,
    )

    if second_layer_decrypted is None:
        logging.warning("Got first layer None decryption")
        return None

    return _decode_choices_proto(second_layer_decrypted)
