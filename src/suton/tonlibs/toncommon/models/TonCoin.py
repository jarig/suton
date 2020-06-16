

class TonCoin(object):

    def __init__(self, tokens):
        self._tokens = tokens

    def as_nano_tokens(self):
        return TonCoin.convert_to_nano_tokens(float(self._tokens))

    @staticmethod
    def convert_to_nano_tokens(tokens):
        return tokens * (10 ** 9)

