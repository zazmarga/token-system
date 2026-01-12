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
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.FileHandler("logs/credits.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # кастомний ExtraFormatter
    formatter = ExtraFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    for h in logging.getLogger().handlers:
        h.setFormatter(formatter)

    # приглушити SQLAlchemy engine логи
    logging.getLogger("sqlalchemy.engine").disabled = True
