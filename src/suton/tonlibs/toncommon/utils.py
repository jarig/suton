

class HexUtils(object):

    @staticmethod
    def hex_to_int(val: str) -> int:
        if val and val.startswith("0x"):
            return int(val, 0)
        return int(val, 0)

