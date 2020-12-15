import json

from toncommon.models.depool.DePoolEvent import DePoolEvent


class DePoolElectionEvent(DePoolEvent):

    election_id = None
    proxy = None

    def _init(self, raw_data: str):
        data = json.loads(raw_data)
        self.election_id = str(self._hex_to_int(data.get("electionId")))
        self.proxy = data.get("proxy")

    def __str__(self):
        return f"Election {self.election_id}, {self.proxy}"

