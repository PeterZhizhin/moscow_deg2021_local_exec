import exonum_client
import nacl.public
import nacl.utils
import pytest
import re_encrypt_message

from exonum_client import crypto as exonum_crypto
from exonum_modules.main import transactions_pb2
from exonum_modules.main import custom_types_pb2
from exonum_modules.main.exonum import messages_pb2


def _create_test_transaction_hex(
    skip_district: bool = False,
    skip_voting_id: bool = False,
) -> str:
    original_store_ballot_tx = transactions_pb2.TxStoreBallot(
        encrypted_choice=transactions_pb2.TxEncryptedChoice(
            encrypted_message=b"some_fake_data",
            nonce=custom_types_pb2.SealedBoxNonce(
                data=b"some_fake_nonce",
            ),
            public_key=custom_types_pb2.SealedBoxPublicKey(
                data=b"some_fake_public_key"
            ),
        ),
    )
    if not skip_district:
        original_store_ballot_tx.district_id = 100500
    if not skip_voting_id:
        original_store_ballot_tx.voting_id = "test_voting_id"

    new_voter_key = exonum_crypto.KeyPair.generate()
    exonum_message = exonum_client.ExonumMessage(
        instance_id=1001,
        message_id=6,
        msg=original_store_ballot_tx,
    )
    exonum_message.sign(new_voter_key)
    transaction_hex = exonum_message.signed_raw().hex()
    return transaction_hex


def _decrypt(
    cipher: bytes,
    nonce: bytes,
    public_key: bytes,
    private_key: nacl.public.PrivateKey,
) -> bytes:
    public = nacl.public.PublicKey(public_key)
    box = nacl.public.Box(private_key, public)
    message = box.decrypt(cipher, nonce=nonce)
    return message


def test_re_encrypt_message_returns_decryptable_message_with_expected_data():
    transaction_hex = _create_test_transaction_hex()
    second_layer_private_key = nacl.public.PrivateKey.generate()
    re_encrypted_message = re_encrypt_message.re_encrypt_blockchain_message_with_sid(
        store_ballot_transaction_hex=transaction_hex,
        re_encryption_public_key=second_layer_private_key.public_key,
        sid="test_sid",
    )

    signed_message = messages_pb2.SignedMessage()
    signed_message.ParseFromString(bytes.fromhex(re_encrypted_message.transaction_hex))

    assert signed_message.author.data.hex() == re_encrypted_message.voter_address_hex

    core_message = messages_pb2.CoreMessage()
    core_message.ParseFromString(signed_message.payload)

    re_encrypted_tx_store_ballot = transactions_pb2.TxStoreBallot()
    re_encrypted_tx_store_ballot.ParseFromString(core_message.any_tx.arguments)

    assert re_encrypted_tx_store_ballot.district_id == 100500
    assert re_encrypted_tx_store_ballot.voting_id == "test_voting_id"

    second_layer_encrypted_message = (
        re_encrypted_tx_store_ballot.encrypted_choice.encrypted_message
    )
    second_layer_public_key = (
        re_encrypted_tx_store_ballot.encrypted_choice.public_key.data
    )
    second_layer_nonce = re_encrypted_tx_store_ballot.encrypted_choice.nonce.data

    second_layer_decrypted = _decrypt(
        cipher=second_layer_encrypted_message,
        nonce=second_layer_nonce,
        public_key=second_layer_public_key,
        private_key=second_layer_private_key,
    )

    encrypted_data = transactions_pb2.TxEncryptedChoice()
    encrypted_data.ParseFromString(second_layer_decrypted)

    assert encrypted_data.encrypted_message == b"some_fake_data"
    assert encrypted_data.nonce.data == b"some_fake_nonce"
    assert encrypted_data.public_key.data == b"some_fake_public_key"


def test_re_encrypt_message_returns_error_on_no_sid():
    transaction_hex = _create_test_transaction_hex()
    second_layer_private_key = nacl.public.PrivateKey.generate()
    with pytest.raises(ValueError, match="Empty SID"):
        re_encrypt_message.re_encrypt_blockchain_message_with_sid(
            store_ballot_transaction_hex=transaction_hex,
            re_encryption_public_key=second_layer_private_key.public_key,
            sid="",
        )


def test_re_encrypt_message_returns_error_on_no_district_id():
    transaction_hex = _create_test_transaction_hex(skip_district=True)
    second_layer_private_key = nacl.public.PrivateKey.generate()
    with pytest.raises(ValueError, match="Got invalid district ID in proto"):
        re_encrypt_message.re_encrypt_blockchain_message_with_sid(
            store_ballot_transaction_hex=transaction_hex,
            re_encryption_public_key=second_layer_private_key.public_key,
            sid="test_sid",
        )


def test_re_encrypt_message_returns_error_on_no_voting_id():
    transaction_hex = _create_test_transaction_hex(skip_voting_id=True)
    second_layer_private_key = nacl.public.PrivateKey.generate()
    with pytest.raises(ValueError, match="Got invalid voting ID in proto"):
        re_encrypt_message.re_encrypt_blockchain_message_with_sid(
            store_ballot_transaction_hex=transaction_hex,
            re_encryption_public_key=second_layer_private_key.public_key,
            sid="test_sid",
        )
