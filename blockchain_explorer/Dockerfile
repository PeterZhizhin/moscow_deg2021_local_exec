FROM node:10-alpine

WORKDIR /app

RUN apk fix \
    && apk --update add git \
    && git clone https://github.com/exonum/blockchain-explorer 

WORKDIR /app/blockchain-explorer

RUN npm install && npm run build

CMD ["npm", "start", "--", "--port=80", "--public-api-root=$PUBLIC_API", "--private-api-root=$PRIVATE_API"]
