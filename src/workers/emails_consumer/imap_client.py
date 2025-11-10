import builtins
import contextlib
import logging
from email import policy
from email.parser import BytesParser

import aioimaplib

from src.core.settings import settings

logger = logging.getLogger(__name__)


async def fetch_unseen_emails(host: str, port: int, login: str, password: str) -> list[dict]:  # noqa: C901
    """Подключается к IMAP, забирает непрочитанные письма и возвращает список словарей."""
    client = None
    try:
        # 1. Подключение
        client = (
            aioimaplib.IMAP4_SSL(host=host, port=port)
            if not settings.DEBUG
            else aioimaplib.IMAP4(host=host, port=port)
        )
        await client.wait_hello_from_server()

        # 2. Логин
        # В aioimaplib login возвращает объект Response, у которого есть result и lines  # noqa: E501, RUF003
        # Если пароль неверный, он все равно возвращает объект, но result будет 'NO'
        res = await client.login(login, password)

        # БЕЗОПАСНАЯ ПРОВЕРКА:
        # Иногда aioimaplib может вернуть просто строку при ошибке (зависит от версии)
        # Проверяем: если это объект Response - берем .result, иначе проверяем саму строку
        result_status = getattr(res, "result", str(res))

        if result_status != "OK":
            logger.error("❌ Ошибка логина для %s: Статус=%s, Ответ=%s", login, result_status, res)
            await client.logout()
            return []

        # 3. Выбор папки
        await client.select("INBOX")

        # 4. Поиск непрочитанных
        # Поиск тоже возвращает Response
        res_search = await client.search("UNSEEN")

        # Безопасно достаем статус и данные
        search_status = getattr(res_search, "result", str(res_search))
        search_data = getattr(res_search, "lines", [])

        if search_status != "OK":
            logger.warning("Ошибка поиска писем: %s", search_status)
            await client.logout()
            return []

        messages = []
        # search_data[0] может быть байтовой строкой b'1 2 3' или пустой
        if not search_data or not search_data[0]:
            # Писем нет, выходим
            await client.logout()
            return []

        # search_data[0] - это байты, декодируем
        id_list_bytes = search_data[0]
        if isinstance(id_list_bytes, bytes):
            id_list_bytes = id_list_bytes.decode()

        for msg_id in id_list_bytes.split():
            if not msg_id:
                continue

            # Fetch
            res_fetch = await client.fetch(msg_id, "(RFC822)")
            fetch_status = getattr(res_fetch, "result", str(res_fetch))

            if fetch_status != "OK":
                logger.warning("Не удалось скачать письмо %s", msg_id)  # noqa: RUF001
                continue

            # Получаем данные письма. Обычно они во втором элементе lines (индекс 1)
            # Структура ответа fetch сложная, lines это список байт
            # res_fetch.lines[1] обычно содержит тело письма
            msg_data_lines = getattr(res_fetch, "lines", [])
            if len(msg_data_lines) < 2:  # noqa: PLR2004
                logger.warning("Странный ответ fetch для %s", msg_id)
                continue

            raw_email_bytes = msg_data_lines[1]

            # Parse
            email_msg = BytesParser(policy=policy.default).parsebytes(raw_email_bytes)

            body = ""
            try:
                body_part = email_msg.get_body(preferencelist=("plain", "html"))
                if body_part:
                    body = body_part.get_content()
            except Exception:  # noqa: BLE001
                body = str(email_msg.get_payload())

            messages.append({
                "subject": str(email_msg.get("subject", "")),
                "from": str(email_msg.get("from", "")),
                "to": str(email_msg.get("to", "")),
                "date": str(email_msg.get("date", "")),
                "body": body,
            })

        # Корректный выход
        await client.logout()
        return messages

    except Exception:
        logger.exception("🔥 Критическая ошибка IMAP для %s", login)
        if client:
            with contextlib.suppress(builtins.BaseException):
                await client.logout()
        return []
