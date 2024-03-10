import asyncio
import logging
import time

import telegram

import deanonimization


logger = logging.getLogger(__name__)


def _format_tally(
    tally: dict[int, dict[str, int]],
) -> str:
    show_district = len(tally) > 1
    result = ""
    for district_id, district_tally in tally.items():
        if show_district:
            result += f"Район {district_id}\n"
        for candidate, votes in district_tally.items():
            result += f"{candidate}: {votes}\n"
    return result


def _format_fios(fios: list[str]) -> str:
    return ", ".join(fios)


def _format_message_for_user(
    *,
    real_tally_formatted: str,
    tally_in_blockchain_formatted: str,
    real_voted_fios: str,
    fios_in_blockchain: str,
    sid: str,
    showing_sid: bool,
) -> str:
    showing_sid_str = ""
    if showing_sid:
        showing_sid_str = f"""
Вам показали следующий ID транзакции в блокчейне: {sid}
Так как вы можете проверять свой голос, ваш голос не был украден.
        """.strip()
    return f"""
Голосование завершено.

Был подведён итог голосования:
{tally_in_blockchain_formatted}

--------------------------------

Информация доступная только организаторам выборов:
Реальный итог голосования:
{real_tally_formatted}

Вы проголосовали за: {real_voted_fios}
В блокчейне учли как: {fios_in_blockchain}

{showing_sid_str}
        """.strip()


async def _send_tg_message_with_retries(
    bot: telegram.Bot,
    user_id: int,
    message: str,
    n_retries: int = 3,
    sleep_time_sec: float = 0.5,
) -> bool:
    for _ in range(n_retries):
        try:
            await bot.send_message(user_id, message)
            return True
        except telegram.error.TelegramError as e:
            logging.error(f"Telegram error when sending a message: {e}")
            await asyncio.sleep(sleep_time_sec)

    return False


async def _send_all_tg_messages(
    user_ids_and_messages: list[tuple[int, str]],
    telegram_bot_token: str,
) -> tuple[int, int]:
    bot = telegram.Bot(token=telegram_bot_token)
    messages_futures = []
    for user_id, message in user_ids_and_messages:
        messages_futures.append(
            _send_tg_message_with_retries(
                bot,
                user_id,
                message,
            )
        )

    all_send_statuses = await asyncio.gather(*messages_futures)

    n_successful_sends = sum(all_send_statuses)
    n_unsuccessful_sends = len(all_send_statuses) - n_successful_sends

    logging.info(
        f"Sent {n_successful_sends} messages, got {n_unsuccessful_sends} errors"
    )

    return n_successful_sends, n_unsuccessful_sends


async def send_deanonimization_messages(
    deanonimization_results: deanonimization.DeanonimizationResults,
    telegram_bot_token: str,
) -> tuple[int, int]:
    real_tally_formatted = _format_tally(deanonimization_results.real_tally)
    tally_in_blockchain_formatted = _format_tally(
        deanonimization_results.tally_in_blockchain
    )

    user_id_and_messages = []
    for deanonimized_user in deanonimization_results.deanonimized_users:
        real_fios = _format_fios(deanonimized_user.real_decrypted_fios)
        fios_in_blockchain = _format_fios(deanonimized_user.decrypted_fios)
        showing_sid = deanonimized_user.showing_sid
        sid = deanonimized_user.sid

        message_for_user = _format_message_for_user(
            real_tally_formatted=real_tally_formatted,
            tally_in_blockchain_formatted=tally_in_blockchain_formatted,
            real_voted_fios=real_fios,
            fios_in_blockchain=fios_in_blockchain,
            sid=sid,
            showing_sid=showing_sid,
        )
        user_id_and_messages.append(
            (
                deanonimized_user.telegram_user_id,
                message_for_user,
            )
        )

    return await _send_all_tg_messages(
        user_id_and_messages,
        telegram_bot_token,
    )
