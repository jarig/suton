from dataclasses import dataclass
from typing import List


@dataclass
class ElectionMember(object):
    stake: int
    timestamp: int
    max_factor: int
    addr: str


@dataclass
class ElectionData(object):
    election_open: bool
    members: List[ElectionMember]
