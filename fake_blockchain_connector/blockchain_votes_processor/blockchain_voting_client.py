import aiohttp
import asyncio
import dataclasses
import datetime
import enum
import os
import random
import sys
from typing import Any, Self

import exonum_client
import exonum_client.crypto
from google.protobuf import message as protobuf_message
import nacl.public

# Add compiled protos to the current path, since it's required by protoc
sys.path.append(os.path.join(os.path.dirname(__file__), "exonum_modules", "main"))

from exonum_modules.main import schema_pb2, transactions_pb2, custom_types_pb2


_VOTING_API_PREFIX = "/services/votings_service/v1/"


_VOTING_SERVICE_INSTANCE_ID = 1001

_STOP_VOTING_MESSAGE_ID = 7
_PUBLISH_DECRYPTION_KEY_MESSAGE_ID = 8
_PUBLISH_DECRYPTION_RESULT_MESSAGE_ID = 12
_FINALIZE_VOTING_MESSAGE_ID = 10


@dataclasses.dataclass(frozen=True)
class CryptoSystemSettings:
    public_key: nacl.public.PublicKey | None
    private_key: nacl.public.PrivateKey | None


class BallotStatus(enum.Enum):
    UNKNOWN = "Unknown"
    VALID = "Valid"
    INVALID = "Invalid"


@dataclasses.dataclass(frozen=True)
class Ballot:
    index: int
    sid: str
    district_id: int
    status: BallotStatus

    voter_key_hex: str
    store_tx_hash_hex: str
    decrypt_tx_hash_hex: str | None

    decrypted_choices: list[int] | None
    encrypted_choice: transactions_pb2.TxEncryptedChoice

    @classmethod
    def from_json(cls, json_response: dict[str, Any]) -> Self:
        index = json_response["index"]
        voter_key_hex = json_response["voter"]
        district_id = json_response["district_id"]
        encrypted_choice = transactions_pb2.TxEncryptedChoice(
            encrypted_message=bytes.fromhex(
                json_response["encrypted_choice"]["message"]
            ),
            nonce=custom_types_pb2.SealedBoxNonce(
                data=bytes.fromhex(json_response["encrypted_choice"]["nonce"])
            ),
            public_key=custom_types_pb2.SealedBoxPublicKey(
                data=bytes.fromhex(json_response["encrypted_choice"]["public_key"])
            ),
        )
        decrypted_choices = json_response["decrypted_choices"]
        store_tx_hash_hex = json_response["store_tx_hash"]
        decrypt_tx_hash_hex = json_response["decrypt_tx_hash"]

        status_str = json_response["status"]
        status = None
        for possible_status in BallotStatus:
            if possible_status.value in status_str:
                status = possible_status
                break
        else:
            raise ValueError(f"Unknown status: {status_str}")

        sid = json_response["sid"]
        return cls(
            index=index,
            sid=sid,
            district_id=district_id,
            status=status,
            voter_key_hex=voter_key_hex,
            store_tx_hash_hex=store_tx_hash_hex,
            decrypt_tx_hash_hex=decrypt_tx_hash_hex,
            decrypted_choices=decrypted_choices,
            encrypted_choice=encrypted_choice,
        )


class VotingState(enum.Enum):
    REGISTRATION = "Registration"
    IN_PROCESS = "InProcess"
    STOPPED = "Stopped"
    FINISHED = "Finished"


@dataclasses.dataclass(frozen=True)
class DecryptionStatistics:
    decrypted_ballots_amount: int
    invalid_ballots_amount: int

    @classmethod
    def from_json(cls, json_response: dict[str, Any]) -> Self:
        return cls(
            decrypted_ballots_amount=json_response["decrypted_ballots_amount"],
            invalid_ballots_amount=json_response["invalid_ballots_amount"],
        )


@dataclasses.dataclass(frozen=True)
class DistrictResult:
    district_id: int
    unique_valid_ballots_amount: int
    invalid_ballots_amount: int
    tally: dict[int, int]

    @classmethod
    def from_json(cls, json_response: dict[str, Any]) -> Self:
        return cls(
            district_id=json_response["district_id"],
            unique_valid_ballots_amount=json_response["unique_valid_ballots_amount"],
            invalid_ballots_amount=json_response["invalid_ballots_amount"],
            tally=json_response["tally"],
        )


@dataclasses.dataclass(frozen=True)
class VotingResults:
    invlid_ballots_amount: int
    unique_valid_ballots_amount: int
    district_results: dict[int, DistrictResult]

    @classmethod
    def from_json(cls, json_response: dict[str, Any]) -> Self:
        return cls(
            invlid_ballots_amount=json_response["invalid_ballots_amount"],
            unique_valid_ballots_amount=json_response["unique_valid_ballots_amount"],
            district_results={
                district_id: DistrictResult.from_json(district_result)
                for district_id, district_result in json_response[
                    "district_results"
                ].items()
            },
        )


class BlockchainVotingClient:
    def __init__(
        self,
        *,
        voting_id: str,
        url: str,
        public_api_port: int,
        private_api_port: int,
        service_api_private_key_hex: str,
        service_api_public_key_hex: str,
        backoff_time: datetime.timedelta = datetime.timedelta(seconds=0.05),
        ssl: bool = False,
    ):
        self._exonum_client = exonum_client.ExonumClient(
            hostname=url,
            private_api_port=private_api_port,
            public_api_port=public_api_port,
            ssl=ssl,
        )
        self._voting_id = voting_id
        self._serivce_api_key_pair = exonum_client.crypto.KeyPair(
            public_key=exonum_client.crypto.PublicKey(
                bytes.fromhex(service_api_public_key_hex)
            ),
            secret_key=exonum_client.crypto.SecretKey(
                bytes.fromhex(service_api_private_key_hex)
            ),
        )
        self._backoff_time = backoff_time

    async def _api_get(self, url_suffix: str, request_params: dict[str, Any]) -> Any:
        url_to_request = (
            self._exonum_client.public_api.endpoint_prefix
            + _VOTING_API_PREFIX
            + url_suffix
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url_to_request, params=request_params) as response:
                response.raise_for_status()
                return await response.json()

    async def _wait_for_tx(self, tx_hash: str):
        tx_check_url = (
            self._exonum_client.public_api.endpoint_prefix + "/explorer/v1/transactions"
        )
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(
                    tx_check_url, params={"hash": tx_hash}
                ) as response:
                    if response.status == 404:
                        await asyncio.sleep(self._backoff_time.total_seconds())
                        continue
                    response.raise_for_status()
                    response_json = await response.json()
                    if response_json["type"] == "committed":
                        if response_json["status"]["type"] != "success":
                            raise ValueError(
                                f"Got exception from blockchain: {response_json}"
                            )
                        break
                    await asyncio.sleep(self._backoff_time.total_seconds())

    async def _send_transaction(
        self, tx: exonum_client.ExonumMessage, wait: bool = True
    ) -> str:
        tx_send_url = (
            self._exonum_client.public_api.endpoint_prefix + "/explorer/v1/transactions"
        )
        async with aiohttp.ClientSession() as session:
            async with session.post(
                tx_send_url,
                headers={"content-type": "application/json"},
                data=tx.pack_into_json(),
            ) as response:
                response.raise_for_status()
                response_json = await response.json()
                tx_hash = response_json["tx_hash"]
                if wait:
                    await self._wait_for_tx(tx_hash)
                return tx_hash

    async def crypto_system_settings(self) -> CryptoSystemSettings:
        result = await self._api_get(
            "crypto-system-settings",
            {
                "voting_id": self._voting_id,
            },
        )
        public_key_hex = result["public_key"]
        private_key_hex = result["private_key"]

        private_key = (
            None
            if private_key_hex is None
            else nacl.public.PrivateKey(bytes.fromhex(private_key_hex))
        )
        public_key = (
            None
            if public_key_hex is None
            else nacl.public.PublicKey(bytes.fromhex(public_key_hex))
        )
        return CryptoSystemSettings(
            public_key=public_key,
            private_key=private_key,
        )

    async def ballots_config(self) -> list[schema_pb2.BallotConfig]:
        json_response = await self._api_get(
            "ballots-config",
            {
                "voting_id": self._voting_id,
            },
        )
        result = []
        for encoded_config in json_response:
            encoded_config_bytes = b"".join(
                val.to_bytes(1, "big") for val in encoded_config
            )
            result_pb = schema_pb2.BallotConfig()
            result_pb.ParseFromString(encoded_config_bytes)
            result.append(result_pb)
        return result

    async def voting_state(self) -> VotingState:
        result = await self._api_get(
            "voting-state",
            {
                "voting_id": self._voting_id,
            },
        )
        state_str = result["state"]
        for state in VotingState:
            if state.value == state_str:
                return state
        raise ValueError(f"Unknown voting state: {state_str}")

    async def stored_ballots_amount(self) -> int:
        result = await self._api_get(
            "stored-ballots-amount",
            {
                "voting_id": self._voting_id,
            },
        )
        return result["stored_ballots_amount"]

    async def ballot_by_index(self, ballot_index: int) -> Ballot:
        result = await self._api_get(
            "ballot-by-index",
            {
                "voting_id": self._voting_id,
                "ballot_index": ballot_index,
            },
        )
        return Ballot.from_json(result)

    async def decryption_statistics(self) -> DecryptionStatistics:
        result = await self._api_get(
            "decryption-statistics",
            {
                "voting_id": self._voting_id,
            },
        )
        return DecryptionStatistics.from_json(result)

    async def voting_results(self) -> VotingResults:
        result = await self._api_get(
            "voting-results",
            {
                "voting_id": self._voting_id,
            },
        )
        return VotingResults.from_json(result)

    def _pack_proto_into_exonum_message(
        self, tx: protobuf_message.Message, message_id: int
    ) -> exonum_client.ExonumMessage:
        msg = exonum_client.ExonumMessage(
            instance_id=_VOTING_SERVICE_INSTANCE_ID,
            message_id=message_id,
            msg=tx,
        )
        msg.sign(self._serivce_api_key_pair)
        return msg

    async def stop_voting(self) -> str:
        current_voting_state = await self.voting_state()
        if current_voting_state != VotingState.IN_PROCESS:
            raise ValueError(
                f"Cannot stop voting in state {current_voting_state}, expected IN_PROCESS"
            )
        stop_voting_tx = transactions_pb2.TxStopVoting(
            voting_id=self._voting_id,
            seed=random.randint(0, 2**32 - 1),
        )
        exonum_message = self._pack_proto_into_exonum_message(
            stop_voting_tx,
            _STOP_VOTING_MESSAGE_ID,
        )
        return await self._send_transaction(exonum_message, wait=True)

    async def publish_decryption_key(self, private_key: nacl.public.PrivateKey) -> str:
        current_voting_state = await self.voting_state()
        if current_voting_state != VotingState.STOPPED:
            raise ValueError(
                f"Cannot publish decryption key in state {current_voting_state}, expected STOPPED"
            )
        crypto_system_settings = await self.crypto_system_settings()

        input_private_key_public_key = private_key.public_key
        blockchain_public_key = crypto_system_settings.public_key
        assert (
            blockchain_public_key is not None
        ), "Blockchain public key is None, but state is STOPPED"
        if input_private_key_public_key != blockchain_public_key:
            raise ValueError(
                f"Private key public key {input_private_key_public_key.encode().hex()} for "
                f"key {private_key.encode().hex()} does not match blockchain public "
                f"key {blockchain_public_key.encode().hex()}"
            )

        publish_decryotion_key_tx = transactions_pb2.TxPublishDecryptionKey(
            voting_id=self._voting_id,
            seed=random.randint(0, 2**32 - 1),
            private_key=custom_types_pb2.SealedBoxSecretKey(
                data=private_key.encode(),
            ),
        )
        exonum_message = self._pack_proto_into_exonum_message(
            publish_decryotion_key_tx,
            _PUBLISH_DECRYPTION_KEY_MESSAGE_ID,
        )
        return await self._send_transaction(exonum_message, wait=True)

    async def publish_decrypted_ballot(
        self,
        ballot_index: int,
        decrypted_choices: list[int] | None,
        is_invalid: bool,
    ) -> str:
        tx_publish_decryption_result = transactions_pb2.TxPublishDecryptedBallot(
            voting_id=self._voting_id,
            ballot_index=ballot_index,
            is_invalid=is_invalid,
            decrypted_choices=decrypted_choices,
        )
        exonum_message = self._pack_proto_into_exonum_message(
            tx_publish_decryption_result,
            _PUBLISH_DECRYPTION_RESULT_MESSAGE_ID,
        )
        return await self._send_transaction(exonum_message, wait=True)

    async def finalize_voting(self):
        voting_state = await self.voting_state()
        if voting_state != VotingState.STOPPED:
            raise ValueError(
                f"Cannot finalize voting in state {voting_state}, expected STOPPED"
            )

        stored_ballots, decryption_statistics = await asyncio.gather(
            self.stored_ballots_amount(),
            self.decryption_statistics(),
        )
        decrypted_ballots = decryption_statistics.decrypted_ballots_amount
        invalid_ballots = decryption_statistics.invalid_ballots_amount
        total_decrypted_ballots = decrypted_ballots + invalid_ballots
        if total_decrypted_ballots != stored_ballots:
            raise ValueError(
                f"Decrypted ballots amount {total_decrypted_ballots} does not "
                f"match stored ballots amount {stored_ballots}. "
                "Some ballots are not decrypted."
            )

        tx_finalize_voting = transactions_pb2.TxFinalizeVoting(
            voting_id=self._voting_id,
            seed=random.randint(0, 2**32 - 1),
        )
        exonum_message = self._pack_proto_into_exonum_message(
            tx_finalize_voting, _FINALIZE_VOTING_MESSAGE_ID
        )
        return await self._send_transaction(exonum_message, wait=True)
