"""Keep broad official season windows out of scheduled match activity."""

import datetime


def reviewable_window_start(start, end, today, review_end):
    """A short event may appear once on opening day, never daily for its season."""
    return (isinstance(start, datetime.date) and isinstance(end, datetime.date)
            and start <= end and (end - start).days <= 7
            and today <= start <= review_end)
