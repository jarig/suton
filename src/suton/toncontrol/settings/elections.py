from enum import Enum
from typing import List

from settings.base import BaseTonControlSettings
from settings.models.depool import DePoolSettings


class ElectionMode(Enum):
    OFF = 'off'
    VALIDATOR = 'validator'
    DEPOOL = 'depool'

    def __str__(self):
        return self.value


class ElectionSettings(BaseTonControlSettings):

    TON_CONTROL_DEFAULT_STAKE = '30%'  # % or absolute value, ex 30%
    TON_CONTROL_STAKE_MAX_FACTOR = '3'
    TON_CONTROL_ELECTION_MODE = ElectionMode.VALIDATOR
    DEPOOL_LIST: List[DePoolSettings] = []

    @classmethod
    def get_class_code_name(cls):
        return ElectionSettings.__qualname__
