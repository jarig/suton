import datetime
import time

from tonliteclient.models.ElectionParams import ElectionParams


class Election(object):
    class State:
        ELECTIONS = 'elections'
        VALIDATION = 'validation'
        FREEZE = 'freeze'
        REWARD = 'reward'

    def __init__(self, election_id, elector_addr, key=None, adnl_key=None, election_stake: int = 0):
        self.election_id = election_id
        self.key = key
        self.adnl_key = adnl_key
        self.elector_addr = elector_addr
        self.election_stake = election_stake
        self.restake = False
        self.election_params = None  # type: ElectionParams

    def can_return(self):
        current_state = self.get_state()
        return current_state is None or current_state == Election.State.REWARD

    def set_election_params(self, params: ElectionParams):
        self.election_params = params

    def get_state(self):
        if self.election_params:
            now_timestamp = time.time()
            election_end = int(self.election_id) - self.election_params.elections_end_before
            validation_end = int(self.election_id) + self.election_params.validators_elected_for
            frozen_until = validation_end + self.election_params.stake_held_for
            if now_timestamp > frozen_until:
                return Election.State.REWARD
            elif now_timestamp > validation_end:
                return Election.State.FREEZE
            elif now_timestamp > election_end:
                return Election.State.VALIDATION
            return Election.State.ELECTIONS
        return None

    @staticmethod
    def from_json(data):
        election = Election(election_id=data['id'],
                            elector_addr=data['elector_addr'],
                            key=data.get('key'),
                            adnl_key=data.get('adnl_key'),
                            election_stake=data.get('election_stake', 0))
        if data.get('election_params'):
            params_data = data.get('election_params')
            election.set_election_params(ElectionParams(validators_elected_for=params_data['validators_elected_for'],
                                                        elections_start_before=params_data['elections_start_before'],
                                                        elections_end_before=params_data['elections_end_before'],
                                                        stake_held_for=params_data['stake_held_for']))
        if data.get('restake'):
            election.restake = True
        return election

    def to_json(self):
        data = {
            'id': self.election_id,
            'key': self.key,
            'adnl_key': self.adnl_key,
            'elector_addr': self.elector_addr,
            'election_stake': self.election_stake,
            'restake': self.restake,
        }
        if self.election_params:
            data['election_params'] = {
                'validators_elected_for': self.election_params.validators_elected_for,
                'elections_start_before': self.election_params.elections_start_before,
                'elections_end_before': self.election_params.elections_end_before,
                'stake_held_for': self.election_params.stake_held_for
            }
        return data

    def __str__(self):
        return "[{}] [{}] {}".format(self.election_id, self.get_state(), self.elector_addr)

    def __repr__(self):
        return str(self)
