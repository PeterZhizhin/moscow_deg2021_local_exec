from collections.abc import Callable
import os
import sys
import nacl.public
import nacl.utils
import dataclasses
import exonum_client
from exonum_client import crypto as exonum_crypto

# Add compiled protos to the current path, since it's required by protoc
sys.path.append(os.path.join(os.path.dirname(__file__), "exonum_modules", "main"))

from exonum_modules.main import transactions_pb2
from exonum_modules.main import custom_types_pb2
from exonum_modules.main.exonum import messages_pb2

_INSTANCE_ID = 1001
_TX_STORE_BALLOT_METHOD_ID = 6


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
    signed_message = messages_pb2.SignedMessage()
    signed_message.ParseFromString(store_ballot_transaction)
    core_message = messages_pb2.CoreMessage()
    core_message.ParseFromString(signed_message.payload)
    tx_store_ballot = transactions_pb2.TxStoreBallot()
    tx_store_ballot.ParseFromString(core_message.any_tx.arguments)

    return tx_store_ballot


def _validate_tx_store_ballot(tx_store_ballot: transactions_pb2.TxStoreBallot):
    if not tx_store_ballot.district_id:
        raise ValueError(f"Got invalid district ID in proto: {tx_store_ballot}")
    if not tx_store_ballot.voting_id:
        raise ValueError(f"Got invalid voting ID in proto: {tx_store_ballot}")


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
    assert exonum_message.signed_raw() is not None
    transaction_hex = exonum_message.signed_raw().hex()
    voter_address_hex = new_voter_key.public_key.value.hex()
    return ReEncryptionResult(
        transaction_hex=transaction_hex,
        voter_address_hex=voter_address_hex,
    )


def re_encrypt_blockchain_message_with_sid(
    *,
    store_ballot_transaction_hex: str,
    re_encryption_public_key: nacl.public.PublicKey,
    sid: str,
) -> ReEncryptionResult:
    if not sid:
        raise ValueError("Empty SID")
    store_ballot_transaction = bytes.fromhex(store_ballot_transaction_hex)
    tx_store_ballot = _parse_store_tx_from_raw_hex(store_ballot_transaction)
    _validate_tx_store_ballot(tx_store_ballot)

    encrypted_choice_serialized = tx_store_ballot.encrypted_choice.SerializeToString()
    encrypted_choice_encrypted = _encrypt_on_public_key(
        data=encrypted_choice_serialized,
        public_key=re_encryption_public_key,
    )

    re_encrypted_tx_store_ballot = _ecnrypted_message_to_tx_store_ballot_message(
        encrypted_message=encrypted_choice_encrypted,
        district_id=tx_store_ballot.district_id,
        voting_id=tx_store_ballot.voting_id,
        sid=sid,
    )

    return _tx_store_ballot_to_exonum_message_hex(
        tx_store_ballot=re_encrypted_tx_store_ballot
    )
