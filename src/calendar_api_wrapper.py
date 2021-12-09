from typing import List, Dict

class CalendarAPIWrapper():
    """
    Class which handles all interaction with the Google APIs, retrieving events for users,
    getting details for events, and generating/storing OAuth
    """
    def __init__(self):
        pass

    def get_event_attributes(self, event_id: str) -> Dict:
        """
        Wraps Google's
        :param event_id:
        :return: Dict of event attributes
        """
        raise NotImplementedError()

    def get_events_for_user(self, email_address: str) -> List[Dict]:
        """ Get list of upcoming events for a user """
        raise NotImplementedError()