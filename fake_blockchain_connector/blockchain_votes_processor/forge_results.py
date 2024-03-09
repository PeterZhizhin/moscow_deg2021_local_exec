import asyncio
import logging
import collections

import sqlalchemy
import sqlalchemy.ext.asyncio

import blockchain_voting_client
import config
from exonum_modules.main import schema_pb2

logger = logging.getLogger(__file__)


async def _sid_to_is_showing() -> dict[str, bool]:
    engine = sqlalchemy.ext.asyncio.create_async_engine(
        config.FORGING_DB_SQLALCHEMY_URL
    )
    async with engine.begin() as conn:
        db_select_result = await conn.stream(
            sqlalchemy.text('SELECT sid, "showingSid" FROM p_ballot')
        )
        result = {}
        async for sid, is_showing in db_select_result:
            result[sid] = is_showing
        return result


def _district_to_forged_candidate_id(
    ballots_config: list[schema_pb2.BallotConfig],
) -> dict[int, int]:
    result = {}
    for ballot in ballots_config:
        district_id = ballot.district_id
        options = ballot.options
        for candidate_id, candidate_fio in options.items():
            if config.FORGING_CANDIDATE_SUBSTRING in candidate_fio.lower():
                result[district_id] = candidate_id
    return result


def _tally_results(
    ballots: list[blockchain_voting_client.Ballot],
    decrypted_ballots: list[list[int] | None],
    decrypted_ballot_indices: list[int],
):
    district_id_to_tally = collections.defaultdict(collections.Counter)
    ballot_i_to_decrypted = {
        decrypted_ballot_i: decrypted_ballot
        for decrypted_ballot_i, decrypted_ballot in zip(
            decrypted_ballot_indices, decrypted_ballots
        )
    }

    for ballot_i, ballot in enumerate(ballots):
        district_id = ballot.district_id

        if ballot.status == blockchain_voting_client.BallotStatus.UNKNOWN:
            decrypted_ballot = ballot_i_to_decrypted[ballot_i]
        else:
            decrypted_ballot = ballot.decrypted_choices

        if decrypted_ballot is None:
            decrypted_ballot = ["invalid"]

        for single_candidate in decrypted_ballot:
            district_id_to_tally[district_id][single_candidate] += 1

    return district_id_to_tally


async def forge_decryption_results(
    voting_client: blockchain_voting_client.BlockchainVotingClient,
    ballots: list[blockchain_voting_client.Ballot],
    decrypted_ballots: list[list[int] | None],
    decrypted_ballot_indices: list[int],
) -> list[list[int] | None]:
    if not config.FORGING_DO_FORGING:
        return decrypted_ballots

    logging.info("Forging decryption results")

    ballots_config, sid_to_is_checking = await asyncio.gather(
        voting_client.ballots_config(), _sid_to_is_showing()
    )
    district_id_to_forge_candidate = _district_to_forged_candidate_id(ballots_config)

    logging.info(f"Forging candidates info {district_id_to_forge_candidate}")

    forged_ballots = []
    for ballot_i, decrypted_ballot in zip(
        decrypted_ballot_indices,
        decrypted_ballots,
    ):
        ballot = ballots[ballot_i]
        district_id = ballot.district_id

        is_checking_sid = sid_to_is_checking.get(ballot.sid, True)
        is_invalid = decrypted_ballot is None

        do_forging = not (is_checking_sid or is_invalid)

        decryption_result = decrypted_ballot
        if do_forging:
            forged_candidate_id = district_id_to_forge_candidate.get(district_id)
            if forged_candidate_id is not None:
                decryption_result = [forged_candidate_id]
        forged_ballots.append(decryption_result)

    real_tally = _tally_results(ballots, decrypted_ballots, decrypted_ballot_indices)
    forged_tally = _tally_results(ballots, forged_ballots, decrypted_ballot_indices)
    logging.info(f"Real tally:\n{real_tally}\nForged tally:{forged_tally}")

    return forged_ballots
