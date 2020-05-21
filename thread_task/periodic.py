#!/usr/bin/env python3
'''subclass of Task for periodic actions'''

from thread_task import Task
from typing import Callable
from numbers import Number


class Periodic(Task):
    """
    Uses multithreading for periodic actions (control comes back immediately).
    """

    def __init__(
            self,
            intervall: Number,
            action: Callable,
            **kwargs
    ):
        """
        Positional Arguments:
            intervall:
                intervall between two calls of action (in seconds)
            action:
                object, which is repeatedly called (f.i. a function)

                Must return a bool or None:
                    True:
                        ends the loop
                    False, None:
                        next call will follow
                        (if not reached limit of num)

        Keyword Arguments:
            args: tuple=()
                argument list of action
            kwargs: dict={}
                keyword arguments of action
            action_stop: typing.Callable=None
                object (f.i. a function), which is called when task is stopped.
            args_stop: tuple=()
                argument list of action_stop
            kwargs_stop: dict={}
                keyword arguments of action_stop
            action_cont: typing.Callable=None
                object (f.i. a function), is called when task is continued.
            args_cont: tuple=()
                argument list of action_cont
            kwargs_cont: dict={}
                keyword arguments of action_cont
            duration: Number=None
                duration of task, if action returns earlier, task will wait
            netto_time: bool=False
                flag, that waiting is netto (execution of action counts extra)
        """

        self._intervall = intervall
        self._netto_time = kwargs.pop('netto_time', False)
        if (
            hasattr(action, '__self__') and
            isinstance(action.__self__, Task) and
            action.__name__ == "start" and
            ('kwargs' not in kwargs or kwargs['kwargs']['thread'])
        ):
            if 'kwargs' not in kwargs:
                kwargs['kwargs'] = {'thread': False}
            else:
                kwargs['kwargs'].update({'thread': False})
        super().__init__(action, **kwargs)
        assert isinstance(self._intervall, Number), \
            'intervall must be a number' + intervall
        assert self._intervall >= 0, 'intervall must be positive'
        assert isinstance(self._netto_time, bool), \
            'netto_time must be a bool value'

    def _wrapper(self):
        self._wrapper_before()
        value = self._action(*self._args, **self._kwargs)
        assert (
            isinstance(value, Task) or
            isinstance(value, bool) or
            value is None
        ), 'action needs to return a Task, a boolean or None'
        if value is True:
            rc = -1
        else:
            rc = self._intervall
        self._wrapper_after()
        return rc
