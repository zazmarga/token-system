import os
import sys
import logging
import json

from app.models import Transaction


TRANSACTION_FIELDS = {c.name for c in Transaction.__table__.columns}


class ExtraFormatter(logging.Formatter):
    def format(self, record):
        base = super().format(record)
        extras = {
            k: v for k, v in record.__dict__.items()
            if k in TRANSACTION_FIELDS
        }
        if extras:
            base += " " + json.dumps(extras, default=str)
        return base


def setup_logging():
    formatter_tx = ExtraFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    formatter_std = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # INTERNAL credits
    internal_handler = logging.FileHandler("logs/internal_credits.log")
    internal_handler.setFormatter(formatter_tx)
    internal_logger = logging.getLogger("[INTERNAL]")
    internal_logger.setLevel(logging.INFO)
    internal_logger.addHandler(internal_handler)

    # PUBLIC credits
    public_handler = logging.FileHandler("logs/public_credits.log")
    public_handler.setFormatter(formatter_tx)
    public_logger = logging.getLogger("[PUBLIC]")
    public_logger.setLevel(logging.INFO)
    public_logger.addHandler(public_handler)

    # ADMIN (без кастомного форматера)
    admin_handler = logging.FileHandler("logs/admin.log")
    admin_handler.setFormatter(formatter_std)
    admin_logger = logging.getLogger("[ADMIN]")
    admin_logger.setLevel(logging.INFO)
    admin_logger.addHandler(admin_handler)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
