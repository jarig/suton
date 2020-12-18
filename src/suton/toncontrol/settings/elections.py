from enum import Enum
from typing import List

from settings.base import BaseTonControlSettings
from settings.depool_settings.depool import DePoolSettings
from settings.depool_settings.prudent_elections import PrudentElectionSettings


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
    PRUDENT_ELECTION_SETTINGS: PrudentElectionSettings = None
    DEPOOL_LIST: List[DePoolSettings] = []

    @classmethod
    def get_class_code_name(cls):
        return ElectionSettings.__qualname__
