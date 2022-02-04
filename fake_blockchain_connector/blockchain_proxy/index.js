var express = require('express');
var blockchainConnector = require('blockchain-connector');
var dotenv = require('dotenv');
var dotenvExpand = require('dotenv-expand');
var privateTransactions = require('./private-blockchain-transactions');


// Read the .env file and expand environment variables inside .env
var config = dotenv.config();
dotenvExpand(config);

var apiUrl = process.env.API_URL;
var apiPrivateKey = process.env.API_PRIVATE_KEY;

var connector = new blockchainConnector.BlockchainConnector(apiUrl);
var apiAccount = blockchainConnector.AccountBuilder.createAccountFromSecretKey(apiPrivateKey);

var privateApiUrl = process.env.PRIVATE_API_URL;
var privateApiPrivateKey = process.env.PRIVATE_API_PRIVATE_KEY;

var privateConnector = new blockchainConnector.BlockchainConnector(privateApiUrl);
var privateApiAccount = blockchainConnector.AccountBuilder.createAccountFromSecretKey(privateApiPrivateKey);

var app = express();
app.use(express.json());

app.get('/get_voting_status', function (req, res) {
    const votingId = req.query.voting_id;
    var readRequest = new blockchainConnector.ReadRequest(`services/votings_service/v1/voting-state?voting_id=${votingId}`);
    readRequest.send(connector).then((response) => {
        res.json(response);
    }).catch((error) => {
        return res.status(500).json({error: error, errorMessage: error.message});
    });
});

app.get('/stop_registration', function (req, res) {
    const votingId = req.query.voting_id;
    var stopRegistrationTx = blockchainConnector.transactions.stopRegistration(apiAccount, {
        voting_id: votingId
    });
    stopRegistrationTx.send(connector).then((txHash) => {
        console.log(`Stopped registration for voting: ${votingId}`);
        return stopRegistrationTx.waitResult();
    }).then((unusedTxStatus) => {
        res.json({"status": "ok"});
    }).catch((error) => {
        console.log(error);
        return res.status(500).json({error: error, errorMessage: error.message});
    });
})

app.post('/create_voting', function (req, res) {
    var createVotingTx = blockchainConnector.transactions.createVoting(apiAccount, req.body);
    var votingId = null;
    createVotingTx.send(connector).then((txHash) => {
        console.log(`Created voting: ${txHash}`);
        votingId = txHash;
        return createVotingTx.waitResult();
    }).then((unusedTxStatus) => {
	var createActualBallotsStorageTx = privateTransactions.createActualBallotsStorage(privateApiAccount, {voting_id: votingId});
	return createActualBallotsStorageTx.send(privateConnector);
    }).then((unusedPrivateTxHash) => {
        res.json({voting_id: votingId});
    }).catch((error) => {
        console.log(error);
        return res.status(500).json({error: error, errorMessage: error.message});
    });
});

app.post('/process_vote', function (req, res) {
    console.log(req.body);
    var voterAddress = req.body["voterAddress"];
    var rawTx = req.body["tx"];
    var votingId = req.body["votingId"];
    console.log(`Dumping tx for voter ${voterAddress} (voting_id: ${votingId}): ${rawTx}`);

    var addVoterKeyTx = blockchainConnector.transactions.addVoterKey(apiAccount, {
        voting_id: votingId,
        voter_key: voterAddress,
    });

    const voteDateTime = parseInt(parseFloat(req.body["voteDateTime"]) * 1000000);

    var addVoterKeyTxHash = null;
    var txStoreBallotHash = null;
    var storeGroupedTxHash = null;
    addVoterKeyTx.send(connector).then((txHash) => {
        console.log(`Got TxAddVoterKey response with hash: ${txHash}`);
        addVoterKeyTxHash = txHash;
        return addVoterKeyTx.waitResult();
    }).then((txResultInfo) => {
        console.log(`TxAddVoterKey waited, submitting raw vote tx`);
        return connector.sendRawTransaction(rawTx);
    }).then((txHash) => {
	txStoreBallotHash = txHash;
	storeGroupedTxHash = privateTransactions.storeGroupedTxHash(privateApiAccount, {
	  voting_id: votingId,
	  store_tx_hash: txStoreBallotHash,
	  encrypted_group_id: req.body["encryptedGroupId"],
	  ts: voteDateTime,
	});
	console.log(`Sending TxStoreGroupedTxHash transaction to private blockchain`);
	console.log(storeGroupedTxHash);
	return storeGroupedTxHash.send(privateConnector);
    }).then((txHash) => {
	console.log(`Waiting on private blockchain ${txHash}`);
	return storeGroupedTxHash.waitResult();
    }).then((txResultInfo) => {
	console.log(txResultInfo);
        res.json({"txStoreBallotHash": txStoreBallotHash, "txAddVoterKeyHash": addVoterKeyTxHash});
    }).catch((error) => {
	console.log("Error:");
	console.log(error);
        res.status(500).send({
            "error": `Got error when processing request:\n${error}`
        });
    });
});


app.listen(process.env.LISTEN_PORT, '0.0.0.0', () => {
    console.log(`Server listening at port ${process.env.LISTEN_PORT}`);
});
