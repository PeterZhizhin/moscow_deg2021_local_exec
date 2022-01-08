FROM node:17-alpine

COPY deg_codebase/blockchain/frontend-library-source/blockchain-connector /app/deg_codebase/blockchain/frontend-library-source/blockchain-connector
COPY fake_blockchain_connector/blockchain_proxy /app/fake_blockchain_connector/blockchain_proxy

WORKDIR /app/fake_blockchain_connector/blockchain_proxy
RUN npm --prefix /app/deg_codebase/blockchain/frontend-library-source/blockchain-connector install \
    && (rm package-lock.json || true) && npm install

CMD ["node", "index.js"]
