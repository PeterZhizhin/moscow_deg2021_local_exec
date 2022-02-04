/* eslint-disable no-console */
const Exonum = require('exonum-client');

var blockchainConnector =  require('blockchain-connector');

const { proto: { actual_ballots_service: { TxStoreGroupedTxHash } } } = blockchainConnector;
const { util: { pbConvert } } = blockchainConnector;
const TransactionRequest = blockchainConnector.TransactionRequest;

const ACTUAL_BALLOTS_STORAGE_SERVICE_ID = 1001;
const STORE_GROUPED_TX_HASH_MSG_ID = 1;

/**
 * @typedef BallotConfig
 * @type {Object}
 * @property {number} district_id - district id (integer
 * @property {string} question - question for voting
 * @property {Object.<number, string>} options - options map <option number, option text>
 */

/**
 * Returns TransactionRequest object for making CreateVoting transaction
 * @param {{publicKey: string, secretKey: string}} sender - transaction sender keypair
 * @param {Object} data - transaction data
 * @param {Object} data.crypto_system - cryptosystem settings
 * @param {string} data.crypto_system.public_key - cryptosystem public key
 * @param {Array<BallotConfig>} data.ballots_config - ballots config
 * @param {boolean} data.revote_enabled - revote enabled
 * @return {TransactionRequest}
 */
module.exports = (sender, data) => {
  const storeGroupedTxHash = new Exonum.Transaction({
    serviceId: ACTUAL_BALLOTS_STORAGE_SERVICE_ID,
    methodId: STORE_GROUPED_TX_HASH_MSG_ID,
    schema: TxStoreGroupedTxHash,
  });

  const txData = {
    voting_id: data.voting_id,
    store_tx_hash: data.store_tx_hash,
    encrypted_group_id: data.encrypted_group_id,
    ts: data.ts,
  };

  return new TransactionRequest(sender, storeGroupedTxHash, txData);
};
