from toncommon.serialization.json import JsonAware


class TonCoin(JsonAware):

    ONE_COIN = 10 ** 9

    def __init__(self, tokens: float = 0):
        self._tokens = tokens

    def as_tokens(self):
        return self._tokens

    def as_nano_tokens(self):
        return TonCoin.convert_to_nano_tokens(self._tokens)

    @staticmethod
    def convert_to_nano_tokens(tokens):
        return tokens * TonCoin.ONE_COIN

    def __str__(self) -> str:
        return str(self._tokens)
