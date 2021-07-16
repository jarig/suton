import logging
from toncommon.serialization.json import JsonAware

log = logging.getLogger("")


class PrudentElectionSettings(JsonAware):
    DESERIALIZE_VIA_CONSTRUCTOR = True

    def __init__(self, election_end_join_offset=None, join_threshold=0):
        """
        :param election_end_join_offset: Defines time offset when to join elections before election end.
        So for example, if you define 600 - then stake will be made in 10 or less minutes before election ends.
        Defined in seconds.
        :param join_threshold: Percentage that defines election join condition, based on the current number of stakes
        their min_value and stake you can/want to make. Threshold = participants_with_lower_than_your_stake / first_N_participants
        So for example, if you define 10, then elections will be taken if at least 10% of valid participants (who potentially can join)
         has lower stake than yours at a moment in time when election join attempt is made (which regulated by election_end_join_offset param)
        """
        self.election_end_join_offset = election_end_join_offset
        self.join_threshold = join_threshold

    def __str__(self):
        return f"Prudent Settings: {self.election_end_join_offset} {self.join_threshold}"
