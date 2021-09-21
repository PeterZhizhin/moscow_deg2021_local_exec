use exonum::crypto::{Hash, PublicKey};
use exonum_rust_runtime::api::{self, ServiceApiState};
use hex;
use std::convert::From;

use crate::{
    enums::VotingState,
    errors::Error,
    schema::{Ballot, BallotsStorage, EncryptedChoice, Voting},
    variants::ballot_status::BallotStatus,
};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct BallotByIndexQuery {
    pub voting_id: String,
    pub ballot_index: u32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct EncryptedChoiceView {
    pub message: String,
    pub nonce: String,
    pub public_key: String,
}

impl From<EncryptedChoice> for EncryptedChoiceView {
    fn from(enc_choice: EncryptedChoice) -> Self {
        Self {
            message: hex::encode(&enc_choice.encrypted_message),
            nonce: hex::encode(&enc_choice.nonce.0),
            public_key: hex::encode(&enc_choice.public_key.0),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct BallotByIndexView {
    pub index: u32,
    pub voter: PublicKey,
    pub district_id: u32,
    pub encrypted_choice: EncryptedChoiceView,
    pub decrypted_choices: Option<Vec<u32>>,
    pub store_tx_hash: Hash,
    pub decrypt_tx_hash: Option<Hash>,
    pub status: BallotStatus,
}

impl From<Ballot> for BallotByIndexView {
    fn from(ballot: Ballot) -> Self {
        Self {
            index: ballot.index,
            voter: ballot.voter,
            district_id: ballot.district_id,
            encrypted_choice: ballot.encrypted_choice.into(),
            decrypted_choices: ballot.decrypted_choices,
            store_tx_hash: ballot.store_tx_hash,
            decrypt_tx_hash: ballot.decrypt_tx_hash,
            status: ballot.status,
        }
    }
}

pub async fn get_ballot_by_index(
    state: ServiceApiState,
    query: BallotByIndexQuery,
) -> api::Result<BallotByIndexView> {
    let voting = Voting::get(state.service_data(), &query.voting_id)
        .ok_or_else(|| Error::VotingDoesNotExist)?;

    if voting.get_state() == VotingState::Registration {
        Err(Error::ForbiddenForThisVotingState)?;
    }

    let ballots_storage = BallotsStorage::get(state.service_data(), &query.voting_id)
        .ok_or_else(|| Error::VotingDoesNotExist)?;

    let ballot = ballots_storage
        .get_ballot_by_index(query.ballot_index)
        .map(|v| v.into())
        .ok_or_else(|| Error::BallotDoesNotExist)?;

    Ok(ballot)
}
