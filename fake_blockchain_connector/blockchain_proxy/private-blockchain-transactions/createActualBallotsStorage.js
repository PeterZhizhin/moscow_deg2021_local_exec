/* eslint-disable no-console */
const Exonum = require('exonum-client');

var blockchainConnector =  require('blockchain-connector');

const { proto: { actual_ballots_service: { TxCreateActualBallotsStorage } } } = blockchainConnector;
const { util: { pbConvert } } = blockchainConnector;
const TransactionRequest = blockchainConnector.TransactionRequest;

const ACTUAL_BALLOTS_STORAGE_SERVICE_ID = 1001;
const CREATE_ACTUAL_BALLOTS_STORAGE_MSG_ID = 0;

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
  const createActualBallotsStorageTx = new Exonum.Transaction({
    serviceId: ACTUAL_BALLOTS_STORAGE_SERVICE_ID,
    methodId: CREATE_ACTUAL_BALLOTS_STORAGE_MSG_ID,
    schema: TxCreateActualBallotsStorage,
  });

  const txData = {
    voting_id: data.voting_id,
  };

  return new TransactionRequest(sender, createActualBallotsStorageTx, txData);
};
