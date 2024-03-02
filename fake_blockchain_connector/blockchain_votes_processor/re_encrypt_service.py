import dataclasses
import functools
import logging
import traceback
from typing import Any, Self

import aiohttp
import aiohttp.web
import nacl.public

import config
import re_encrypt_message

routes = aiohttp.web.RouteTableDef()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)


@functools.cache
def _get_re_encryption_private_key() -> nacl.public.PrivateKey:
    private_key_hex = config.RE_ENCRYPTOR_PRIVATE_KEY_HEX
    if not private_key_hex:
        raise ValueError(f"Got invalid private key: {private_key_hex}")
    private_key_bytes = bytes.fromhex(private_key_hex)
    private_key = nacl.public.PrivateKey(private_key_bytes)
    return private_key


@functools.cache
def _get_re_encryption_public_key() -> nacl.public.PublicKey:
    return _get_re_encryption_private_key().public_key


@dataclasses.dataclass(frozen=True)
class ReEncryptRequest:
    store_ballot_transaction: bytes
    sid: str
    voting_id: str
    district_id: int

    @classmethod
    def from_json(cls, request: Any) -> Self:
        if not isinstance(request, dict):
            raise ValueError(f"Got bad request (not dict) {request}")

        if "tx" not in request or not isinstance(request["tx"], str):
            raise ValueError(f"No tx in request or invalid type: {request}")
        tx = bytes.fromhex(request["tx"])

        if "sid" not in request or not isinstance(request["sid"], str):
            raise ValueError(f"No sid in request or invalid type: {request}")
        sid = request["sid"]

        if "voting_id" not in request or not isinstance(request["voting_id"], str):
            raise ValueError(f"No voting_id in request or invalid type: {request}")
        voting_id = request["voting_id"]

        if "district_id" not in request or not isinstance(request["district_id"], int):
            raise ValueError(f"No district_id in request or invalid type: {request}")
        district_id = request["district_id"]

        return cls(
            store_ballot_transaction=tx,
            sid=sid,
            voting_id=voting_id,
            district_id=district_id,
        )


@routes.post("/blockchain_re_encryptor/re_encrypt")
async def re_encrypt(request: aiohttp.web.Request) -> aiohttp.web.Response:
    try:
        request_json = await request.json()

        re_encryption_request = ReEncryptRequest.from_json(request_json)
        re_encryption_public_key = _get_re_encryption_public_key()

        re_encryption_result = (
            re_encrypt_message.re_encrypt_blockchain_message_with_sid(
                store_ballot_transaction=re_encryption_request.store_ballot_transaction,
                re_encryption_public_key=re_encryption_public_key,
                sid=re_encryption_request.sid,
                voting_id=re_encryption_request.voting_id,
                district_id=re_encryption_request.district_id,
            )
        )

        return aiohttp.web.json_response(
            {
                "tx": re_encryption_result.transaction_hex,
                "voter_address": re_encryption_result.voter_address_hex,
            }
        )
    except ValueError as exc:
        return aiohttp.web.json_response(
            {
                "error": str(exc),
            },
            status=400,
        )


app = aiohttp.web.Application()
app.add_routes(routes)

if __name__ == "__main__":
    aiohttp.web.run_app(app, port=config.RE_ENCRYPTOR_LISTEN_PORT)
