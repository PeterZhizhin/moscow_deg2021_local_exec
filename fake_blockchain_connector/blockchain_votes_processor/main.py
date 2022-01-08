import json
import hashlib
import functools
import logging

import asyncio
import aiohttp
import aiohttp.web
import aio_pika

import config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)


async def get_queues_ids():
    async with aiohttp.ClientSession() as session:
        async with session.get(config.ARM_VOITING_URL, raise_for_status=True) as resp:
            result = await resp.json()
            logger.info(f"Got queues config: {result}")
            return {x["ID"]: x["EXT_ID"] for x in result["data"]}


async def decrypt_message(message_str):
    async with aiohttp.ClientSession(
        config.ENCRYPTOR_URL,
        headers={
            "SYSTEM": config.ENCRYPTOR_SYSTEM,
            "SYSTEM_TOKEN": config.ENCRYPTOR_TOKEN,
        },
    ) as session:
        async with session.get(
            "/api/encryption/decrypt", params={"data[base64body]": message_str},
            raise_for_status=True,
        ) as resp:
            return await resp.json()


async def send_message_to_proxy(message):
    async with aiohttp.ClientSession() as session:
        async with session.post(config.BLOCKCHAIN_PROCESS_VOTE_URI, raise_for_status=True, json=message) as resp:
            return await resp.json()


async def receive_message(message: aio_pika.IncomingMessage, voting_id: str):
    async with message.process():
        message_body = message.body.decode("utf-8")
        logger.info(f"Got raw message {message_body}")
        decrypted_message = await decrypt_message(message_body)
        decrypted_message_body = decrypted_message.get("data", {}).get("result")

        if decrypted_message_body is None:
            logger.info(f"Got broken message, ignoring: {decrypted_message}")
            return

        decrypted_message_json = json.loads(decrypted_message_body)
        logger.info(f"Got message: {decrypted_message_json}")
        decrypted_message_json["votingId"] = voting_id

        proxy_response = await send_message_to_proxy(decrypted_message_json)
        logger.info(f'Got response from proxy: {proxy_response}')


async def main():
    try:
        connection = await aio_pika.connect_robust(
            host=config.RABBIT_MQ_HOSTNAME,
            port=config.RABBIT_MQ_PORT,
            login=config.RABBIT_MQ_LOGIN,
            password=config.RABBIT_MQ_PASSWORD,
        )

        queue_ids = await get_queues_ids()
        logger.info(f'Configuring queues: {queue_ids}')
        async with connection:
            channel = await connection.channel()
            
            for queue_key, voting_id in queue_ids.items():
                queue_name = f'{config.BASE_LISTEN_QUEUE_NAME}-{queue_key}'
                queue = await channel.get_queue(queue_name, ensure=False)

                async def receive_message_partial(x):
                    return await receive_message(x, voting_id)

                logger.info(f"Starting consuming on queue {queue_name} (voting_id: {voting_id}).")
                await queue.consume(receive_message_partial)

            logger.info("All queues are listening.")
            while True:
                await asyncio.sleep(100)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise
    finally:
        logger.info('Stopping connection, deleting queue listening')


class BlockchainConnector:
    __instance = None

    def __init__(self):
        self.task = asyncio.create_task(main())

    @classmethod
    def get_instance(cls):
        if not cls.__instance:
            cls.__instance = cls()
        return cls.__instance

    @classmethod
    def recreate(cls):
        if cls.__instance:
            cls.__instance.task.cancel()
            cls.__instance = None
        return cls.get_instance()


routes = aiohttp.web.RouteTableDef()

@routes.get('/blockchain_connector/refresh')
async def refresh_queues(unused_request):
    logger.info('Recreating queues')
    BlockchainConnector.recreate()
    return aiohttp.web.Response(text='ok')


async def start_queues(unused_app):
    BlockchainConnector.get_instance()

app = aiohttp.web.Application()
app.add_routes(routes)

app.on_startup.append(start_queues)

if __name__ == "__main__":
    aiohttp.web.run_app(app, port=config.LISTEN_PORT)
