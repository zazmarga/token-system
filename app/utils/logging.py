import random
import logging

logger = logging.getLogger(__name__)


def get_extra_data_log(obj: object) -> dict:
    return {
        column.name: getattr(obj, column.name)
        for column in obj.__table__.columns
    }


def generate_admin_log_id(operation_type: str) -> str:
    # беремо перші літери кожного слова
    prefix = "".join(word[0] for word in operation_type.split("_"))

    rand_digits = f"{random.randint(0, 9999):04d}"

    log_id = f"{prefix}_{rand_digits}"

    return log_id
