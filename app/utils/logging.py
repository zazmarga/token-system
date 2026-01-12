
import logging

logger = logging.getLogger(__name__)


def get_extra_credits_log(tx) -> dict:
    return {
        column.name: getattr(tx, column.name)
        for column in tx.__table__.columns
    }
