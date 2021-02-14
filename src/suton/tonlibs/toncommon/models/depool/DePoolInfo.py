from dataclasses import dataclass
from typing import List


@dataclass
class DePoolInfo(object):
    pool_closed: bool
    proxies: List[str]
    validator_wallet: str
    participant_reward_fraction: str
