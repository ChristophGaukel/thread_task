#!/usr/bin/env python3
'''subclass of Task for sleeping'''

from numbers import Number
from .task import Task


class Sleep(Task):
    """
    Uses multithreading for Sleeping (can be stopped and continued)
    """
    def __init__(self, seconds: Number, **kwargs):
        """
        Positional Arguments
          seconds
            duration of sleeping

        Keyword Arguments
          action_start: Callable=None
            object (f.i. a function),
            which is called when task is started.
          args_start: tuple=()
            argument list of action_start
          kwargs_start: dict={}
            keyword arguments of action_start
          action_stop: Callable=None
            object (e.g. a function), called when task is stopped.
          args_stop: tuple=()
            argument list of action_stop
          kwargs_stop: dict={}
            keyword arguments of action_stop
          action_cont: Callable=None
            object (e.g. a function), called when task is continued.
          args_cont: tuple=()
            argument list of action_cont
          kwargs_cont: dict={}
            keyword arguments of action_cont
          action_final: Callable=None
            object (e.g. a function), called when task is finished.
          args_final: tuple=()
            argument list of action_final
          kwargs_final: dict={}
            keyword arguments of action_final
          exc_handler: Callable=None
            user defined handler of exceptions
        """
        assert 'action' not in kwargs, \
            'no action for Sleep objects'
        assert 'args' not in kwargs, \
            'no args for Sleep objects'
        assert 'kwargs' not in kwargs, \
            'no kwargs for Sleep objects'
        assert 'duration' not in kwargs, \
            'no duration for Sleep objects'
        assert 'num' not in kwargs, \
            'no num for Sleep objects'
        assert 'netto_time' not in kwargs, \
            'no netto_time for Sleep objects'
        super().__init__(self._do_nothing, duration=seconds, **kwargs)
        del self._action
        del self._args
        del self._kwargs

    def _do_nothing(self): pass

    def _wrapper(self) -> Number:
        return -1
