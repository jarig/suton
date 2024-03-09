import dataclasses


@dataclasses.dataclass
class DePoolSyncStatus:
    time_diff: int
    sync_status: str