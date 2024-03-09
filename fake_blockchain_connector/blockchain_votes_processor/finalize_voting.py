import asyncio
import concurrent.futures
import os
import sys
import logging

import nacl.public

import blockchain_voting_client
import forge_results
import re_encrypt_message

# Add compiled protos to the current path, since it's required by protoc
sys.path.append(os.path.join(os.path.dirname(__file__), "exonum_modules", "main"))

from exonum_modules.main import schema_pb2

logger = logging.getLogger(__file__)


def _ballots_config_to_district_to_ballot_config(
    ballots_config: list[schema_pb2.BallotConfig],
) -> dict[int, schema_pb2.BallotConfig]:
    result = {}
    for ballot_coinfig in ballots_config:
        result[ballot_coinfig.district_id] = ballot_coinfig
    return result


def _decrypt_and_verify_validity(
    ballot: blockchain_voting_client.Ballot,
    district_id_to_ballot_config: dict[int, schema_pb2.BallotConfig],
    re_encryption_private_key: nacl.public.PrivateKey,
    first_layer_private_key: nacl.public.PrivateKey,
) -> list[int] | None:
    ballot_config = district_id_to_ballot_config[ballot.district_id]
    decrypted_ballot = re_encrypt_message.decrypt_re_encrypted_tx(
        re_encrypted_tx_encrypted_vote=ballot.encrypted_choice,
        re_encryption_private_key=re_encryption_private_key,
        first_layer_private_key=first_layer_private_key,
    )
    if decrypted_ballot is None:
        return None

    # Verify that the decrypted ballot is valid
    # Ferify that the number of choices is correct
    if not (
        ballot_config.min_choices <= len(decrypted_ballot) <= ballot_config.max_choices
    ):
        return None

    # Verify all choices are in the list of options
    valid_options = set(ballot_config.options)
    set_of_decrypted_options = set(decrypted_ballot)
    if not set_of_decrypted_options.issubset(valid_options):
        return None

    # Verify no duplicate choices
    if len(set_of_decrypted_options) != len(decrypted_ballot):
        return None

    return decrypted_ballot


async def finalize_voting(
    *,
    voting_client: blockchain_voting_client.BlockchainVotingClient,
    re_encryption_private_key: nacl.public.PrivateKey,
    first_layer_private_key: nacl.public.PrivateKey,
    decrypt_workers: int | None = None,
):
    voting_state = await voting_client.voting_state()
    if voting_state != blockchain_voting_client.VotingState.STOPPED:
        raise ValueError("Voting is not stopped")

    logging.info("Checking encryption key")
    crypto_system_settings = await voting_client.crypto_system_settings()
    if crypto_system_settings.private_key is None:
        logging.info("Publishing decryption key")
        await voting_client.publish_decryption_key(first_layer_private_key)

    ballots_config = await voting_client.ballots_config()
    district_id_to_ballots_config = _ballots_config_to_district_to_ballot_config(
        ballots_config
    )
    logging.info(f"Got ballots config: {district_id_to_ballots_config}")

    num_ballots = await voting_client.stored_ballots_amount()
    logging.info(f"Querying info about {num_ballots} ballots")
    ballots_futures = []
    for ballot_i in range(num_ballots):
        ballots_futures.append(voting_client.ballot_by_index(ballot_i))
    ballots = await asyncio.gather(*ballots_futures)

    logging.info("Done querying info, starting decryption.")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=decrypt_workers
    ) as decrypt_executor:
        decrypted_ballots_futures = []
        decrypted_ballots_indices = []
        for i, ballot in enumerate(ballots):
            if ballot.status == blockchain_voting_client.BallotStatus.UNKNOWN:
                decrypted_ballots_futures.append(
                    asyncio.get_running_loop().run_in_executor(
                        decrypt_executor,
                        _decrypt_and_verify_validity,
                        ballot,
                        district_id_to_ballots_config,
                        re_encryption_private_key,
                        first_layer_private_key,
                    )
                )
                decrypted_ballots_indices.append(i)

        decrypted_ballots = await asyncio.gather(*decrypted_ballots_futures)

    decrypted_ballots = await forge_results.forge_decryption_results(
        voting_client,
        ballots,
        decrypted_ballots,
        decrypted_ballots_indices,
    )

    logging.info("Decrypted everything, starting to publish decryption results.")
    publish_decrypted_ballots_futures = []
    for ballot_index, decrypted_ballot in zip(
        decrypted_ballots_indices, decrypted_ballots
    ):
        is_invalid = decrypted_ballot is None
        publish_decrypted_ballots_futures.append(
            voting_client.publish_decrypted_ballot(
                ballot_index=ballot_index,
                is_invalid=is_invalid,
                decrypted_choices=decrypted_ballot,
            )
        )

    await asyncio.gather(*publish_decrypted_ballots_futures)

    logging.info("Finalizing voting.")
    await voting_client.finalize_voting()
