

class LowDePoolBalanceException(Exception):

    def __init__(self, message: str, balance: int):
        super().__init__(f"{message}. Need to have {balance} tokens.")
        self.balance = balance
