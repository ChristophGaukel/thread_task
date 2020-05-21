#!/usr/bin/env python3

from typing import Callable
from numbers import Number
from .task import Task


class Repeated(Task):
    """
    Organizes repeated actions with multithreading
    """
    def __init__(self, action: Callable, **kwargs):
        """
        Positional Arguments:
            action:
                callable object, which is repeatedly called (f.i. a function).

                Must return a number, a bool or None:
                    True, -1:
                        end the loop
                    False, None:
                        next call follows directly (if limit num not reached)
                    positive number:
                        time gap between the current and the next call

        Keyword Arguments:
            args: tuple=()
                argument list of action
            kwargs: dict={}
                keyword arguments of action
            action_stop: Callable=None
                object (f.i. a function), is called when task is stopped.
            args_stop: tuple=()
                argument list of action_stop
            kwargs_stop: dict={}
                keyword arguments of action_stop
            action_cont: Callable=None
                object (f.i. a function), is called when task is continued.
            args_cont: tuple=()
                argument list of action_cont
            kwargs_cont: dict={}
                keyword arguments of action_cont
            duration: Number=None
                duration of task (if action returns earlier, task will wait)
            netto_time: bool=False
                flag, that waiting is netto (execution of action counts extra)
        """

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
        assert isinstance(self._netto_time, bool), \
            'netto_time must be a bool value'

    def _wrapper(self):
        self._wrapper_before()
        value = self._action(*self._args, **self._kwargs)

        assert (
            isinstance(value, Task) or
            isinstance(value, Number) or
            isinstance(value, bool) or
            value is None
        ), 'action needs to return a number, a boolean or None'
        assert (
            not isinstance(value, Number) or
            value == -1 or
            value >= 0
        ), (
            'if action returns a number, ' +
            'it must be positive or 0 or -1, but is ' +
            str(value)
        )

        if value is True:
            rc = -1
        elif isinstance(value, Task) or value is False or value is None:
            rc = 0
        else:
            rc = value
        self._wrapper_after()
        return rc
