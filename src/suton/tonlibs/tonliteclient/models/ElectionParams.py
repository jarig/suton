

class ElectionParams(object):
    # validators_elected_for:65536 elections_start_before:32768 elections_end_before:8192 stake_held_for:32768

    def __init__(self, validators_elected_for, elections_start_before, elections_end_before, stake_held_for):
        self.validators_elected_for = validators_elected_for
        self.elections_start_before = elections_start_before
        self.elections_end_before = elections_end_before
        self.stake_held_for = stake_held_for


class StakeParams(object):
    def __init__(self, min_stake, max_stake):
        self.min_stake = min_stake
        self.max_stake = max_stake

