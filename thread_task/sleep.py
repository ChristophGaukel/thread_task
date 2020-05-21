#!/usr/bin/env python3
'''subclass of Task for sleeping'''

from numbers import Number
from .task import Task


class Sleep(Task):
    """
    Sleeps and can be stopped
    """
    def __init__(self, seconds: Number, **kwargs):
        """
        Positional Arguments:
            seconds: duration of sleeping
        """
        super().__init__(self._do_nothing, duration=seconds, **kwargs)

    def _do_nothing(self): pass
