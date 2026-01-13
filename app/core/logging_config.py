import logging
import json

from app.models import Transaction
from app.models.settings import AdminLog

# logging credits (transactions)
TRANSACTION_FIELDS = {c.name for c in Transaction.__table__.columns}
# admin logging
ADMIN_FIELDS = {c.name for c in AdminLog.__table__.columns}


class ModelFormatter(logging.Formatter):
    def __init__(self, fmt=None, fields=None):
        super().__init__(fmt)
        self.fields = fields or set()

    def format(self, record):
        base = super().format(record)
        extras = {k: v for k, v in record.__dict__.items() if k in self.fields}
        if extras:
            base += " " + json.dumps(extras, default=str, ensure_ascii=False)
        return base


# setup
def setup_logging():
    formatter_tx = ModelFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        fields=TRANSACTION_FIELDS
    )

    formatter_admin = ModelFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        fields=ADMIN_FIELDS
    )

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

    # ADMIN
    admin_handler = logging.FileHandler("logs/admin.log")
    admin_handler.setFormatter(formatter_admin)
    admin_logger = logging.getLogger("[ADMIN]")
    admin_logger.setLevel(logging.INFO)
    admin_logger.addHandler(admin_handler)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
