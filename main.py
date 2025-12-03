import logging
import os

from telegram import Update

from bot import build_application
from database import Base, engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("telegram").setLevel(logging.INFO)


def main() -> None:
    configure_logging()
    bot_token = os.getenv("TELEGRAM_TOKEN")
    if not bot_token:
        raise RuntimeError("TELEGRAM_TOKEN environment variable is not set.")

    webhook_base_url = os.getenv("WEBHOOK_URL")
    if not webhook_base_url:
        raise RuntimeError("WEBHOOK_URL environment variable is not set.")

    webhook_path_env = os.getenv("WEBHOOK_PATH", "telegram-webhook")
    webhook_path = webhook_path_env.strip("/") or "telegram-webhook"
    webhook_url = f"{webhook_base_url.rstrip('/')}/{webhook_path}"

    port = int(os.getenv("PORT", "8000"))

    init_db()

    application = build_application(bot_token)

    logger = logging.getLogger("bot.main")
    logger.info(
        "Starting webhook server on 0.0.0.0:%s with external URL %s",
        port,
        webhook_url,
    )

    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=webhook_path,
        webhook_url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()

