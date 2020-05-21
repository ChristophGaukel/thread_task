#!/usr/bin/env python3
'''organize and run thread tasks,
which can be stopped, continued and restarted.
'''

from copy import copy
from threading import Lock, Condition

from .constants import (
    STATE_INIT,
    ACTIVITY_NONE
)


def _clean_link(task):
    '''
    erase root only attributes and data from last execution

    Returns
      Task
    '''
    # root only
    task._state = None
    task._activity = None
    task._current = None
    task._current_scheduled = None
    task._thread = None
    task._thread_start = None
    task._thread_cont = None
    task._restart = False
    task._lock = None
    task._cond = None
    task._current = None  # current Task object
    task._current_scheduled = None  # scheduled time
    task._time_called_start = None  # time of last starting
    task._time_called_cont = None  # time of last continuing
    task._time_called_stop = None  # time of last stopping
    task._children = []
    task._threadless_child = None
    task._cont_join = None
    task._parent = None
    task._exc = None  # exception occured
    task._delay = None  # additional timespan in start or cont

    # last execution
    task._duration_rest = None
    task._gap = None
    task._cnt = 0

    return task


def _copy_task(task):
    """
    copies a task

    Returns
      Task (copy of argument)
    """
    assert task._root is task, 'copying root tasks only'

    # copy root task
    root = _clean_link(copy(task))
    root._root = root
    root._state = STATE_INIT
    root._activity = ACTIVITY_NONE
    root._lock = Lock()
    root._cond = Condition(root._lock)

    # copy chain links and build linked list of tasks
    previous = root
    while previous._next is not None:
        # copy chain link
        current = _clean_link(copy(previous._next))
        current._root = root
        # use old links to identify last chain link
        if root._last is previous._next:
            root._last = current
        previous._next = current  # replace link
        previous = current  # one step forewards

    return root


def concat(*tasks, copy: bool = False):
    """
    Concats a number of Task objects and returns a chain of tasks.
    This modifies the Task objects. If you need them unchanged,
    set the copy flag.

    Positional Arguments
      tasks
        any number of Task objects

    Keyword Arguments
      copy
        flag, if Task links must be copied

    Returns
      concatenated chain of Task links
    """
    if not copy:
        return tasks[0].append(
            *tasks[1:],
            copy=False
        )
    else:
        return _copy_task(
            tasks[0]
        ).append(
            *tasks[1:],
            copy=True
        )
