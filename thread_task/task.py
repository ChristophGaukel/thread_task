#!/usr/bin/env python3
'''organize thread tasks, which can be stopped, continued and restarted.'''

from typing import Callable
from .repeated import Repeated


class Task(Repeated):
    """
    Uses multithreading for tasks or chains of tasks.
    The most simple case is a callable object.
    Subsequent tasks or chains of tasks can be added with method append().
    """

    def __init__(self, action: Callable, **kwargs):
        """
        Positional Arguments
          action
            object which will be executed (e.g. a function).

        Keyword Arguments
          args: tuple=()
            argument list of action
          kwargs: dict={}
            keyword arguments of action
          action_start: Callable=None
            object (f.i. a function), called when task is started.
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
          duration: Number=None
            duration of task (if action returns earlier, task will wait)
          exc_handler: Callable=None
            user defined handler of exceptions
        """

        assert 'num' not in kwargs, \
            'no num for Task objects'
        assert 'netto_time' not in kwargs, \
            'no netto_time for Task objects'
        super().__init__(action, **kwargs)

    def _wrapper(self) -> int:
        '''runs wrapper_before, then action, then wrapper_after
        returns -1 (no repeated calling)
        '''
        # assert current_thread() == self._root._thread, \
        #     '_wrapper runs in unexpected thread'
        # assert self._root._lock.locked(), '_wrapper has been called unlocked'

        self._wrapper_before()
        self._action(*self._args, **self._kwargs)
        self._wrapper_after()
        return -1
