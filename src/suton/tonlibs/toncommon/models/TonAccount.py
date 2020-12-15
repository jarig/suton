

class TonAccount(object):

    def __init__(self, acc_type, balance, last_paid=None, data=None):
        self.type = acc_type
        self.balance: int = balance
        self.last_paid = last_paid
        self.data = data

