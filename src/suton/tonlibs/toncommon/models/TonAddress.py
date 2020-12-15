

class TonAddress(object):
    class Type:
        MASTER_CHAIN = "-1:"
        MAIN_CHAIN = "1:"
        HEX = "0x"

    def __init__(self, address):
        self.address = address

    @staticmethod
    def get_short_address(adr: str):
        if adr:
            return '{}..{}'.format(adr[:6], adr[-3:])
        return '[missing adr]'

    @staticmethod
    def set_address_prefix(adr: str, prefix):
        # remove all possible existing prefixes first
        adr = adr.replace("-1:", "", 1)
        adr = adr.replace("1:", "", 1)
        adr = adr.replace("0x", "", 1)
        return f"{prefix}{adr}"
