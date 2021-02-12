from abc import ABC

from routines.validator_providers.core import Validator


class ElectionProvider(ABC):

    def __init__(self, validator: Validator):
        self._validator = validator


