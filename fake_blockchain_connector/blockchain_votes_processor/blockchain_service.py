import asyncio
import functools
import logging
from typing import Any, Self

import aiohttp
import aiohttp.web
import nacl.public

import config
import blockchain_voting_client
import finalize_voting

logger = logging.getLogger(__name__)


routes = aiohttp.web.RouteTableDef()


def _get_blockchain_client(
    voting_id: str,
) -> blockchain_voting_client.BlockchainVotingClient:
    return blockchain_voting_client.BlockchainVotingClient(
        voting_id=voting_id,
        url=config.BLOCKCHAIN_API_HOSTNAME,
        public_api_port=config.BLOCKCHAIN_API_PUBLIC_PORT,
        private_api_port=config.BLOCKCHAIN_API_PRIVATE_PORT,
        service_api_private_key_hex=config.BLOCKCHAIN_API_PRIVATE_KEY,
        service_api_public_key_hex=config.BLOCKCHAIN_API_PUBLIC_KEY,
    )


@functools.cache
def _get_re_encryption_private_key() -> nacl.public.PrivateKey:
    private_key_hex = config.RE_ENCRYPTOR_PRIVATE_KEY_HEX
    if not private_key_hex:
        raise ValueError(f"Got invalid private key: {private_key_hex}")
    private_key_bytes = bytes.fromhex(private_key_hex)
    private_key = nacl.public.PrivateKey(private_key_bytes)
    return private_key


class DecryptionHandler:
    def __init__(self):
        self._running_task = None

    def is_running(self) -> bool:
        if self._running_task is None:
            return False
        return not self._running_task.done()

    def add_decryption(self, coro):
        if self.is_running():
            raise ValueError("Decryption is already running")
        self._running_task = asyncio.create_task(coro)

    @classmethod
    def instance(cls) -> Self:
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance


@routes.get("/blockchain_service/voting_state")
async def voting_state(request: aiohttp.web.Request) -> aiohttp.web.Response:
    client = _get_blockchain_client(request.query["voting_id"])
    voting_state, crypto_system_settings = await asyncio.gather(
        client.voting_state(), client.crypto_system_settings()
    )

    decryption_running = DecryptionHandler.instance().is_running()
    response_json: dict[str, Any] = {
        "state": voting_state.value,
        "decryption_running": decryption_running,
    }
    response_json.update(crypto_system_settings.to_json())
    match voting_state:
        case blockchain_voting_client.VotingState.REGISTRATION:
            pass
        case blockchain_voting_client.VotingState.IN_PROCESS:
            response_json["stored_ballots_amount"] = (
                await client.stored_ballots_amount()
            )
        case blockchain_voting_client.VotingState.STOPPED:
            response_json["stored_ballots_amount"] = (
                await client.stored_ballots_amount()
            )
            response_json["decryption_statistics"] = (
                await client.decryption_statistics()
            ).to_json()
        case blockchain_voting_client.VotingState.FINISHED:
            response_json["stored_ballots_amount"] = (
                await client.stored_ballots_amount()
            )
            response_json["decryption_statistics"] = (
                await client.decryption_statistics()
            ).to_json()
            response_json["voting_results"] = (await client.voting_results()).to_json()

    return aiohttp.web.json_response(response_json)


@routes.get("/blockchain_service/stored_ballots_amount")
async def stored_ballots_amount(request: aiohttp.web.Request) -> aiohttp.web.Response:
    client = _get_blockchain_client(request.query["voting_id"])
    stored_ballots_amount = await client.stored_ballots_amount()
    return aiohttp.web.json_response({"stored_ballots_amount": stored_ballots_amount})


@routes.get("/blockchain_service/crypto_system_settings")
async def crypto_system_settings(request: aiohttp.web.Request) -> aiohttp.web.Response:
    client = _get_blockchain_client(request.query["voting_id"])
    crypto_system_settings = await client.crypto_system_settings()
    return aiohttp.web.json_response(crypto_system_settings.to_json())


@routes.post("/blockchain_service/stop_voting")
async def stop_voting(request: aiohttp.web.Request) -> aiohttp.web.Response:
    client = _get_blockchain_client(request.query["voting_id"])
    stop_voting_tx_hash = await client.stop_voting()
    return aiohttp.web.json_response({"status": "ok", "tx_hash": stop_voting_tx_hash})


@routes.post("/blockchain_service/start_decryption")
async def start_decryption(request: aiohttp.web.Request) -> aiohttp.web.Response:
    try:
        if DecryptionHandler.instance().is_running():
            raise ValueError("Decryption is already running")

        request_json = await request.json()

        client = _get_blockchain_client(request_json["voting_id"])

        current_voting_state = await client.voting_state()
        if current_voting_state != blockchain_voting_client.VotingState.STOPPED:
            raise ValueError(
                f"Got invalid voting state: {current_voting_state}, expected STOPPED"
            )

        voting_private_key = nacl.public.PrivateKey(
            bytes.fromhex(request_json["private_key_hex"])
        )

        await client.verify_private_key(voting_private_key)

        re_encryption_private_key = _get_re_encryption_private_key()

        # DecryptionHandler.instance().add_decryption(
        await finalize_voting.finalize_voting(
            voting_client=client,
            first_layer_private_key=voting_private_key,
            re_encryption_private_key=re_encryption_private_key,
            decrypt_workers=config.BLOCKCHAIN_SERVICE_DECRYPT_WORKERS,
        )  # ,
        # )

        return aiohttp.web.json_response({"status": "ok"})
    except ValueError as e:
        return aiohttp.web.json_response(
            {"status": "error", "message": str(e)}, status=400
        )


app = aiohttp.web.Application()
app.add_routes(routes)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger.info(f"Starting the server on port {config.BLOCKCHAIN_SERVICE_LISTEN_PORT}")
    aiohttp.web.run_app(app, port=config.BLOCKCHAIN_SERVICE_LISTEN_PORT)
