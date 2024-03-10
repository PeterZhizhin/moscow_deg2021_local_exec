import asyncio
import dataclasses
import datetime
from typing import Any
import collections
from collections.abc import AsyncIterable, Callable, Awaitable, Iterable
import concurrent.futures
import hashlib
import json

import aiohttp
import sqlalchemy
import sqlalchemy.ext.asyncio
import pandas as pd
import nacl.public

import blockchain_voting_client
import finalize_voting

from exonum_modules.main import schema_pb2


@dataclasses.dataclass(frozen=True)
class PBallotRow:
    raw_store_ballot_tx_hex: str
    original_raw_store_ballot_tx_hex: str
    mdm_cypher_base64: str
    sid: str
    showing_sid: bool
    created_at: datetime.datetime
    group_id: str | None = None


async def get_pballot_rows(
    connection_url: str, get_group_id_from_mdm_cypher: Callable[[str], Awaitable[str]]
) -> list[PBallotRow]:
    p_ballot_engine = sqlalchemy.ext.asyncio.create_async_engine(connection_url)

    async with p_ballot_engine.connect() as conn:
        result = await conn.stream(
            sqlalchemy.text(
                'SELECT "rawStoreBallotTx", "originalRawStoreBallotTx", "mdm_cypher", "sid", "showingSid", "created_at" FROM p_ballot'
            )
        )

        p_ballots = []
        async for (
            raw_store_ballot_tx,
            original_raw_store_ballot_tx,
            mdm_cypher,
            sid,
            showing_sid,
            created_at,
        ) in result:
            p_ballots.append(
                PBallotRow(
                    raw_store_ballot_tx_hex=raw_store_ballot_tx,
                    original_raw_store_ballot_tx_hex=original_raw_store_ballot_tx,
                    mdm_cypher_base64=mdm_cypher,
                    sid=sid,
                    showing_sid=showing_sid,
                    created_at=created_at,
                    group_id=await get_group_id_from_mdm_cypher(mdm_cypher),
                )
            )

        return p_ballots


@dataclasses.dataclass(frozen=True)
class SudirUser:
    user_id: int
    telegram_user_id: int
    mobile: str
    group_id: str


async def get_sudir_users(
    connection_url, user_id_to_group_id: Callable[[str], Awaitable[str]]
) -> list[SudirUser]:
    sudir_engine = sqlalchemy.ext.asyncio.create_async_engine(connection_url)

    async with sudir_engine.connect() as conn:
        result = await conn.stream(
            sqlalchemy.text('SELECT "id", "telegram_id", "mobile" FROM "user"')
        )

        sudir_users = []
        async for user_id, telegram_user_id, mobile in result:
            if telegram_user_id is None:
                continue
            sudir_users.append(
                SudirUser(
                    user_id=user_id,
                    telegram_user_id=telegram_user_id,
                    mobile=mobile,
                    group_id=await user_id_to_group_id(user_id),
                )
            )

        return sudir_users


async def _sso_id_to_group_id(
    user_id: str | int,
    stribog_url: str,
    mdm_secret: str,
    component_x_secret: str,
) -> str:
    if isinstance(user_id, int):
        user_id = str(user_id)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            stribog_url, data={"data": user_id}
        ) as user_id_encoded_response:
            user_id_encoded_response.raise_for_status()
            sso_id_hmac = await user_id_encoded_response.text()

            hash_fn = hashlib.blake2b(key=bytes.fromhex(mdm_secret))
            hash_fn.update(sso_id_hmac.encode("utf-8"))
            external_id = hash_fn.hexdigest()
            async with session.post(
                stribog_url, data={"data": external_id, "secret": component_x_secret}
            ) as hmac_external_id_response:
                hmac_external_id_response.raise_for_status()
                hmac_external_id = await hmac_external_id_response.text()
                return hmac_external_id


async def _decrypt_mdm(
    cypher_base64: str,
    decrypt_url: str,
    system: str,
    token: str,
) -> dict[str, Any]:
    headers = {
        "SYSTEM": system,
        "SYSTEM-TOKEN": token,
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(
            decrypt_url, data={"base64body": cypher_base64}
        ) as decrypted_response:
            decrypted_response.raise_for_status()
            return await decrypted_response.json()


async def _get_group_id_from_mdm_cypher(*args, **kwargs):
    mdm_decyphered = await _decrypt_mdm(*args, **kwargs)
    return json.loads(mdm_decyphered["data"]["result"])["groupId"]


async def get_all_ballots(
    blockchain_client: blockchain_voting_client.BlockchainVotingClient,
) -> list[blockchain_voting_client.Ballot]:
    stored_ballots = await blockchain_client.stored_ballots_amount()
    all_futures = []
    for i in range(stored_ballots):
        all_futures.append(blockchain_client.ballot_by_index(i))

    ballots = []
    for ballot in asyncio.as_completed(all_futures):
        ballots.append(await ballot)
    return ballots


def decrypt_with_sid(sid: str, *args) -> tuple[str, list[int] | None]:
    return sid, finalize_voting.decrypt_and_verify_validity(*args)


async def decrypt_all_ballots(
    all_ballots: list[blockchain_voting_client.Ballot],
    district_id_to_ballots_config: dict[int, schema_pb2.BallotConfig],
    re_encryption_private_key: nacl.public.PrivateKey,
    first_layer_private_key: nacl.public.PrivateKey,
) -> AsyncIterable[tuple[str, list[int] | None]]:

    with concurrent.futures.ProcessPoolExecutor() as decrypt_executor:
        decrypted_ballots_futures = []
        for ballot in all_ballots:
            decrypted_ballots_futures.append(
                asyncio.get_running_loop().run_in_executor(
                    decrypt_executor,
                    decrypt_with_sid,
                    ballot.sid,
                    ballot,
                    district_id_to_ballots_config,
                    re_encryption_private_key,
                    first_layer_private_key,
                )
            )

        for result in asyncio.as_completed(decrypted_ballots_futures):
            yield await result


def _ballots_config_to_candidate_names(
    ballots_configs: Iterable[schema_pb2.BallotConfig],
) -> dict[tuple[int, int], str]:
    result = {}
    for ballot_config in ballots_configs:
        district_id = ballot_config.district_id
        for candidate_id, candidate_fio in ballot_config.options.items():
            result[(district_id, candidate_id)] = candidate_fio
    return result


def _tally(
    district_id_decrypted_choices: Iterable[tuple[int, list[int] | None]]
) -> dict[tuple[int, int], int]:
    result = collections.Counter()
    for district_id, decrypted_choices in district_id_decrypted_choices:
        if decrypted_choices is None:
            decrypted_choices = [0]
        for decrypted_choice in decrypted_choices:
            result[(district_id, decrypted_choice)] += 1
    return dict(result)


def _tally_to_fio(
    tally: dict[tuple[int, int], int],
    district_candidate_id_to_fio: dict[tuple[int, int], str],
) -> dict[tuple[int, str], int]:
    result = {}
    for district_id_candidate_id, current_tally in tally.items():
        fio = district_candidate_id_to_fio[district_id_candidate_id]
        district_id = district_id_candidate_id[0]
        result[(district_id, fio)] = current_tally
    return result


def _reformat_tally(tally: dict[tuple[int, str], int]) -> dict[int, dict[str, int]]:
    result = {}
    for (district_id, fio), current_tally in tally.items():
        if district_id not in result:
            result[district_id] = {}
        result[district_id][fio] = current_tally
    return result


def _choices_district_id_to_human_readable(
    district_id: int,
    decrypted_choices: list[int] | None,
    district_candidate_id_to_fio: dict[tuple[int, int], str],
) -> list[str]:
    if decrypted_choices is None:
        return ["Испорченный бюллетень"]
    return [
        district_candidate_id_to_fio[(district_id, choice_id)]
        for choice_id in decrypted_choices
    ]


@dataclasses.dataclass(frozen=True)
class DeanonimizedUserResult:
    telegram_user_id: int
    decrypted_fios: list[str]
    real_decrypted_fios: list[str]
    showing_sid: bool
    sid: str


@dataclasses.dataclass(frozen=True)
class DeanonimizationResults:
    real_tally: dict[int, dict[str, int]]
    tally_in_blockchain: dict[int, dict[str, int]]

    deanonimized_users: list[DeanonimizedUserResult]


async def deanonimize_all_users(
    blockchain_client: blockchain_voting_client.BlockchainVotingClient,
    re_encryption_private_key: nacl.public.PrivateKey,
    decrypt_url: str,
    decrypt_system: str,
    decrypt_token: str,
    stribog_url: str,
    mdm_secret: str,
    component_x_secret: str,
    p_ballot_connection_url: str,
    sudir_connection_url: str,
) -> DeanonimizationResults:
    voting_state, crypto_system_settings, ballots_config = await asyncio.gather(
        blockchain_client.voting_state(),
        blockchain_client.crypto_system_settings(),
        blockchain_client.ballots_config(),
    )

    if voting_state != blockchain_voting_client.VotingState.FINISHED:
        raise ValueError(f"Voting is not finished, current state is {voting_state}")

    first_layer_private_key = crypto_system_settings.private_key
    if first_layer_private_key is None:
        raise ValueError("Private key is not set")

    async def group_id_from_mdm_cypher(x: str) -> str:
        return await _get_group_id_from_mdm_cypher(
            x,
            decrypt_url,
            system=decrypt_system,
            token=decrypt_token,
        )

    async def user_id_to_group_id(x: str) -> str:
        return await _sso_id_to_group_id(
            x,
            stribog_url,
            mdm_secret,
            component_x_secret,
        )

    all_p_ballot_rows, all_sudir_rows, all_ballots = await asyncio.gather(
        get_pballot_rows(
            p_ballot_connection_url,
            group_id_from_mdm_cypher,
        ),
        get_sudir_users(
            sudir_connection_url,
            user_id_to_group_id,
        ),
        get_all_ballots(blockchain_client),
    )

    district_id_to_ballots_config = (
        finalize_voting.ballots_config_to_district_to_ballot_config(ballots_config)
    )
    all_ballots_decrypted = [
        {"sid": sid, "real_decrypted_result": result}
        async for sid, result in decrypt_all_ballots(
            all_ballots,
            district_id_to_ballots_config,
            re_encryption_private_key,
            first_layer_private_key,
        )
    ]
    all_ballots_decrypted_df = pd.DataFrame(all_ballots_decrypted)

    p_ballot_df = pd.DataFrame(all_p_ballot_rows)
    sudir_df = pd.DataFrame(all_sudir_rows)
    ballots_df = pd.DataFrame(all_ballots)
    deanonimized_ballots = (
        p_ballot_df.merge(
            sudir_df,
            on="group_id",
        )
        .merge(
            ballots_df,
            on="sid",
        )
        .merge(all_ballots_decrypted_df, on="sid")
    )

    tally_in_blockchain = _tally(
        (row.district_id, row.decrypted_choices)
        for _, row in deanonimized_ballots[
            ["district_id", "decrypted_choices"]
        ].iterrows()
    )
    real_tally = _tally(
        (row.district_id, row.real_decrypted_result)
        for _, row in deanonimized_ballots[
            ["district_id", "real_decrypted_result"]
        ].iterrows()
    )

    district_candidate_id_to_fio = _ballots_config_to_candidate_names(ballots_config)

    deanonimized_ballots["decrypted_fios"] = deanonimized_ballots[
        ["district_id", "decrypted_choices"]
    ].apply(
        lambda row: _choices_district_id_to_human_readable(
            row.district_id, row.decrypted_choices, district_candidate_id_to_fio
        ),
        axis=1,
    )
    deanonimized_ballots["real_decrypted_fios"] = deanonimized_ballots[
        ["district_id", "real_decrypted_result"]
    ].apply(
        lambda row: _choices_district_id_to_human_readable(
            row.district_id, row.real_decrypted_result, district_candidate_id_to_fio
        ),
        axis=1,
    )

    tally_in_blockchain_fio = _reformat_tally(
        _tally_to_fio(
            tally_in_blockchain,
            district_candidate_id_to_fio,
        )
    )
    real_tally_fio = _reformat_tally(
        _tally_to_fio(
            real_tally,
            district_candidate_id_to_fio,
        )
    )

    user_deanonimization_results = []
    for _, row in deanonimized_ballots.iterrows():
        user_deanonimization_results.append(
            DeanonimizedUserResult(
                telegram_user_id=row.telegram_user_id,
                decrypted_fios=row.decrypted_fios,
                real_decrypted_fios=row.real_decrypted_fios,
                showing_sid=row.showing_sid,
                sid=row.sid,
            )
        )

    return DeanonimizationResults(
        real_tally=real_tally_fio,
        tally_in_blockchain=tally_in_blockchain_fio,
        deanonimized_users=user_deanonimization_results,
    )
