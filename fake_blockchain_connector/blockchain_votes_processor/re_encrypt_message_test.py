import exonum_client
import nacl.public
import nacl.utils
import pytest
import re_encrypt_message

from exonum_client import crypto as exonum_crypto
from exonum_modules.main import custom_types_pb2
from exonum_modules.main import schema_pb2
from exonum_modules.main import transactions_pb2
from exonum_modules.main.exonum import messages_pb2


def _create_test_transaction(
    skip_district: bool = False,
    skip_voting_id: bool = False,
) -> bytes:
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
    transaction = exonum_message.signed_raw()
    assert transaction is not None
    return transaction


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
    transaction = _create_test_transaction()
    second_layer_private_key = nacl.public.PrivateKey.generate()
    re_encrypted_message = re_encrypt_message.re_encrypt_blockchain_message_with_sid(
        store_ballot_transaction=transaction,
        re_encryption_public_key=second_layer_private_key.public_key,
        sid="test_sid",
        voting_id="some_new_voting_id",
        district_id=100,
    )

    signed_message = messages_pb2.SignedMessage()
    signed_message.ParseFromString(bytes.fromhex(re_encrypted_message.transaction_hex))

    assert signed_message.author.data.hex() == re_encrypted_message.voter_address_hex

    core_message = messages_pb2.CoreMessage()
    core_message.ParseFromString(signed_message.payload)

    re_encrypted_tx_store_ballot = transactions_pb2.TxStoreBallot()
    re_encrypted_tx_store_ballot.ParseFromString(core_message.any_tx.arguments)

    assert re_encrypted_tx_store_ballot.district_id == 100
    assert re_encrypted_tx_store_ballot.voting_id == "some_new_voting_id"

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


def test_re_encrypt_replaces_tx_with_invalid_data_to_empty_on_invalid_proto():
    transaction = _create_test_transaction()[:-20]
    second_layer_private_key = nacl.public.PrivateKey.generate()
    re_encrypted_message = re_encrypt_message.re_encrypt_blockchain_message_with_sid(
        store_ballot_transaction=transaction,
        re_encryption_public_key=second_layer_private_key.public_key,
        sid="test_sid",
        voting_id="some_new_voting_id",
        district_id=100,
    )

    signed_message = messages_pb2.SignedMessage()
    signed_message.ParseFromString(bytes.fromhex(re_encrypted_message.transaction_hex))

    assert signed_message.author.data.hex() == re_encrypted_message.voter_address_hex

    core_message = messages_pb2.CoreMessage()
    core_message.ParseFromString(signed_message.payload)

    re_encrypted_tx_store_ballot = transactions_pb2.TxStoreBallot()
    re_encrypted_tx_store_ballot.ParseFromString(core_message.any_tx.arguments)

    assert re_encrypted_tx_store_ballot.district_id == 100
    assert re_encrypted_tx_store_ballot.voting_id == "some_new_voting_id"

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

    assert encrypted_data.encrypted_message == b""
    assert encrypted_data.nonce.data == b""
    assert encrypted_data.public_key.data == b""


def test_re_encrypt_message_returns_error_on_no_sid():
    transaction = _create_test_transaction()
    second_layer_private_key = nacl.public.PrivateKey.generate()
    with pytest.raises(ValueError, match="Empty SID"):
        re_encrypt_message.re_encrypt_blockchain_message_with_sid(
            store_ballot_transaction=transaction,
            re_encryption_public_key=second_layer_private_key.public_key,
            sid="",
            voting_id="some_new_voting_id",
            district_id=100,
        )


def test_decrypt_re_encrypted_tx_returns_expected_value():
    first_layer_sk = nacl.public.PrivateKey.generate()
    second_layer_sk = nacl.public.PrivateKey.generate()

    choices_msg = schema_pb2.Choices(data=[123])
    choices_msg_serialized = choices_msg.SerializeToString()

    leading_zeros = b"\0" * 10
    leading_zeros_len_bytes = (10).to_bytes(2, byteorder="big")
    first_layer_message = (
        leading_zeros_len_bytes + leading_zeros + choices_msg_serialized
    )

    first_layer_sk_voter = nacl.public.PrivateKey.generate()
    first_layer_box = nacl.public.Box(first_layer_sk_voter, first_layer_sk.public_key)

    first_layer_nonce = nacl.utils.random(nacl.public.Box.NONCE_SIZE)
    first_layer_cipher = first_layer_box.encrypt(
        plaintext=first_layer_message,
        nonce=first_layer_nonce,
    )[nacl.public.Box.NONCE_SIZE :]

    first_layer_encrypted_message = transactions_pb2.TxEncryptedChoice(
        encrypted_message=first_layer_cipher,
        nonce=custom_types_pb2.SealedBoxNonce(
            data=first_layer_nonce,
        ),
        public_key=custom_types_pb2.SealedBoxPublicKey(
            data=first_layer_sk_voter.public_key.encode(),
        ),
    ).SerializeToString()

    second_layer_sk_system = nacl.public.PrivateKey.generate()
    first_layer_box = nacl.public.Box(
        second_layer_sk_system, second_layer_sk.public_key
    )

    second_layer_nonce = nacl.utils.random(nacl.public.Box.NONCE_SIZE)
    second_layer_cipher = first_layer_box.encrypt(
        plaintext=first_layer_encrypted_message,
        nonce=second_layer_nonce,
    )[nacl.public.Box.NONCE_SIZE :]

    second_layer_tx = transactions_pb2.TxEncryptedChoice(
        encrypted_message=second_layer_cipher,
        nonce=custom_types_pb2.SealedBoxNonce(
            data=second_layer_nonce,
        ),
        public_key=custom_types_pb2.SealedBoxPublicKey(
            data=second_layer_sk_system.public_key.encode(),
        ),
    )

    decrypted_vote = re_encrypt_message.decrypt_re_encrypted_tx(
        re_encrypted_tx_encrypted_vote=second_layer_tx,
        re_encryption_private_key=second_layer_sk,
        first_layer_private_key=first_layer_sk,
    )
    assert decrypted_vote == [123]


def test_decrypt_re_encrypted_tx_returns_none_on_invalid_choices():
    first_layer_sk = nacl.public.PrivateKey.generate()
    second_layer_sk = nacl.public.PrivateKey.generate()

    first_layer_sk_voter = nacl.public.PrivateKey.generate()
    first_layer_box = nacl.public.Box(first_layer_sk_voter, first_layer_sk.public_key)

    first_layer_nonce = nacl.utils.random(nacl.public.Box.NONCE_SIZE)
    first_layer_cipher = first_layer_box.encrypt(
        plaintext=b"",
        nonce=first_layer_nonce,
    )[nacl.public.Box.NONCE_SIZE :]

    first_layer_encrypted_message = transactions_pb2.TxEncryptedChoice(
        encrypted_message=first_layer_cipher,
        nonce=custom_types_pb2.SealedBoxNonce(
            data=first_layer_nonce,
        ),
        public_key=custom_types_pb2.SealedBoxPublicKey(
            data=first_layer_sk_voter.public_key.encode(),
        ),
    ).SerializeToString()

    second_layer_sk_system = nacl.public.PrivateKey.generate()
    first_layer_box = nacl.public.Box(
        second_layer_sk_system, second_layer_sk.public_key
    )

    second_layer_nonce = nacl.utils.random(nacl.public.Box.NONCE_SIZE)
    second_layer_cipher = first_layer_box.encrypt(
        plaintext=first_layer_encrypted_message,
        nonce=second_layer_nonce,
    )[nacl.public.Box.NONCE_SIZE :]

    second_layer_tx = transactions_pb2.TxEncryptedChoice(
        encrypted_message=second_layer_cipher,
        nonce=custom_types_pb2.SealedBoxNonce(
            data=second_layer_nonce,
        ),
        public_key=custom_types_pb2.SealedBoxPublicKey(
            data=second_layer_sk_system.public_key.encode(),
        ),
    )

    decrypted_vote = re_encrypt_message.decrypt_re_encrypted_tx(
        re_encrypted_tx_encrypted_vote=second_layer_tx,
        re_encryption_private_key=second_layer_sk,
        first_layer_private_key=first_layer_sk,
    )
    assert decrypted_vote is None


def test_decrypt_re_encrypted_tx_returns_none_on_truncated_first_layer_tx():
    first_layer_sk = nacl.public.PrivateKey.generate()
    second_layer_sk = nacl.public.PrivateKey.generate()

    first_layer_encrypted_message = transactions_pb2.TxEncryptedChoice(
        encrypted_message=b"testtesttest",
        public_key=custom_types_pb2.SealedBoxPublicKey(
            data=nacl.public.PrivateKey.generate().encode(),
        ),
        nonce=custom_types_pb2.SealedBoxNonce(
            data=b"\0" * nacl.public.Box.NONCE_SIZE,
        ),
    ).SerializeToString()[:-2]

    second_layer_sk_system = nacl.public.PrivateKey.generate()
    first_layer_box = nacl.public.Box(
        second_layer_sk_system, second_layer_sk.public_key
    )

    second_layer_nonce = nacl.utils.random(nacl.public.Box.NONCE_SIZE)
    second_layer_cipher = first_layer_box.encrypt(
        plaintext=first_layer_encrypted_message,
        nonce=second_layer_nonce,
    )[nacl.public.Box.NONCE_SIZE :]

    second_layer_tx = transactions_pb2.TxEncryptedChoice(
        encrypted_message=second_layer_cipher,
        nonce=custom_types_pb2.SealedBoxNonce(
            data=second_layer_nonce,
        ),
        public_key=custom_types_pb2.SealedBoxPublicKey(
            data=second_layer_sk_system.public_key.encode(),
        ),
    )

    decrypted_vote = re_encrypt_message.decrypt_re_encrypted_tx(
        re_encrypted_tx_encrypted_vote=second_layer_tx,
        re_encryption_private_key=second_layer_sk,
        first_layer_private_key=first_layer_sk,
    )
    assert decrypted_vote is None


def test_decrypt_re_encrypted_tx_returns_none_on_invalid_first_layer():
    first_layer_encrypted_message = transactions_pb2.TxEncryptedChoice(
        encrypted_message=b"test_message_invalid",
        nonce=custom_types_pb2.SealedBoxNonce(
            data=b"\0" * nacl.public.Box.NONCE_SIZE,
        ),
        public_key=custom_types_pb2.SealedBoxPublicKey(
            data=nacl.public.PrivateKey.generate().public_key.encode(),
        ),
    ).SerializeToString()

    second_layer_sk = nacl.public.PrivateKey.generate()
    second_layer_sk_system = nacl.public.PrivateKey.generate()
    first_layer_box = nacl.public.Box(
        second_layer_sk_system, second_layer_sk.public_key
    )

    second_layer_nonce = nacl.utils.random(nacl.public.Box.NONCE_SIZE)
    second_layer_cipher = first_layer_box.encrypt(
        plaintext=first_layer_encrypted_message,
        nonce=second_layer_nonce,
    )[nacl.public.Box.NONCE_SIZE :]

    second_layer_tx = transactions_pb2.TxEncryptedChoice(
        encrypted_message=second_layer_cipher,
        nonce=custom_types_pb2.SealedBoxNonce(
            data=second_layer_nonce,
        ),
        public_key=custom_types_pb2.SealedBoxPublicKey(
            data=second_layer_sk_system.public_key.encode(),
        ),
    )

    first_layer_sk = nacl.public.PrivateKey.generate()
    decrypted_vote = re_encrypt_message.decrypt_re_encrypted_tx(
        re_encrypted_tx_encrypted_vote=second_layer_tx,
        re_encryption_private_key=second_layer_sk,
        first_layer_private_key=first_layer_sk,
    )
    assert decrypted_vote is None


def test_decrypt_re_encrypted_tx_returns_none_on_invalid_second_layer():
    second_layer_tx = transactions_pb2.TxEncryptedChoice(
        encrypted_message=b"test_message",
        nonce=custom_types_pb2.SealedBoxNonce(
            data=b"\0" * nacl.public.Box.NONCE_SIZE,
        ),
        public_key=custom_types_pb2.SealedBoxPublicKey(
            data=nacl.public.PrivateKey.generate().public_key.encode(),
        ),
    )

    decrypted_vote = re_encrypt_message.decrypt_re_encrypted_tx(
        re_encrypted_tx_encrypted_vote=second_layer_tx,
        re_encryption_private_key=nacl.public.PrivateKey.generate(),
        first_layer_private_key=nacl.public.PrivateKey.generate(),
    )
    assert decrypted_vote is None
