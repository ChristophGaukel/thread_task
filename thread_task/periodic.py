#!/usr/bin/env python3
'''subclass of Task for periodic actions'''

from .repeated import Repeated
from typing import Callable
from numbers import Number


class Periodic(Repeated):
    """
    Uses multithreading for periodic actions.
    """

    def __init__(
            self,
            interval: Number,
            action: Callable,
            **kwargs
    ):
        """
        Positional Arguments
          interval
            interval between two calls of action (in seconds)
          action
            object, which is repeatedly called (e.g. a function)

            Must return a bool or None:
              True
                ends the loop
              False, None
                next call will follow (if not reached limit of num)

        Keyword Arguments
          args: tuple=()
            argument list of action
          kwargs: dict={}
            keyword arguments of action
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
          num: int
            number of iterations
          duration: Number=None
            duration of task (if action returns earlier, task will wait)
          netto_time: bool=False
            flag, that waiting is netto (execution of action counts extra)
          exc_handler: Callable=None
            user defined handler of exceptions
        """

        self._interval = interval
        assert isinstance(self._interval, Number), \
            'interval must be a number' + interval
        assert self._interval >= 0, 'interval must be positive'
        super().__init__(action, **kwargs)

    def _wrapper(self):
        self._wrapper_before()
        value = self._action(*self._args, **self._kwargs)
        assert (
            isinstance(value, Repeated) or
            isinstance(value, bool) or
            value is None
        ), 'action needs to return a task, a boolean or None'
        if value is True:
            rc = -1
        else:
            rc = self._interval
        self._wrapper_after()
        return rc
