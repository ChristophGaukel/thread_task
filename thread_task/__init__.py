#!/usr/bin/env python3
'''organize and run thread tasks,
which can be stopped, continued and restarted.
'''

from copy import copy
from typing import Callable
from threading import Thread, Lock, Condition, current_thread
from numbers import Number
from time import time

from .constants import (
    STATE_INIT,
    STATE_TO_START,
    STATE_STARTED,
    STATE_TO_STOP,
    STATE_STOPPED,
    STATE_TO_CONTINUE,
    STATE_FINISHED,
    ACTIVITY_BUSY,
    ACTIVITY_JOIN,
    ACTIVITY_NONE,
    ACTIVITY_SLEEP
)

__all__ = [
    'Task',
    'Sleep',
    'Periodic',
    'Repeated',
    'STATE_INIT',
    'STATE_TO_START',
    'STATE_STARTED',
    'STATE_TO_STOP',
    'STATE_STOPPED',
    'STATE_TO_CONTINUE',
    'STATE_FINISHED',
    'ACTIVITY_BUSY',
    'ACTIVITY_JOIN',
    'ACTIVITY_NONE',
    'ACTIVITY_SLEEP',
    'concat'
]


def _copy_task(task: 'Task') -> 'Task':
    """
    copies a task
    """
    assert task._root is task, 'copying root tasks only'

    # copy root task
    root = copy(task)
    root._root = root
    root._state = STATE_INIT
    root._activity = ACTIVITY_NONE
    root._current = None
    root._current_scheduled = None
    root._parent = None

    # copy chain links and build linked list of tasks
    previous = root
    while previous._next is not None:
        # copy chain link
        current = copy(previous._next)
        current._root = root
        # use old links to identify last chain link
        if root._last is previous._next:
            root._last = current
        previous._next = current  # replace link
        previous = current  # one step forewards

    return root


def concat(*tasks: 'Task', copy: bool = False) -> 'Task':
    """
    Concats a number of Task objects and returns a chain of tasks.
    This modifies the Task objects. If you need them unchanged,
    set the copy flag.

    Positional Arguments:
        tasks:
            any number of Task objects

    Keyword Arguments:
        copy:
            Flag, if resulting Task objects will be copied
    """
    if not copy:
        return tasks[0].append(
            *tasks[1:],
            copy=copy
        )
    else:
        return _copy_task(
            tasks[0]
        ).append(
            *tasks[1:],
            copy=copy
        )


class Task:
    """
    Uses multithreading for tasks or chains of tasks.
    The most simple case is a callable object.
    Subsequent tasks or chains of tasks can be added with method append().
    """

    # register with all parent-child relations of currently executed childs
    #   key: root task of the child
    #   value: root task of the parent
    _parents = {}

    def __init__(self, action: Callable, **kwargs):
        """
        Positional Arguments:
            action:
                object which will be executed (f.i. a function).

        Keyword Arguments:
            args: tuple=()
                argument list of action
            kwargs: dict={}
                keyword arguments of action
            action_start: typing.Callable=None
                object (f.i. a function),
                which is called when task is started.
            args_start: tuple=()
                argument list of action_start
            kwargs_start: dict={}
                keyword arguments of action_start
            action_stop: typing.Callable=None
                object (f.i. a function),
                which is called when task is stopped.
            args_stop: tuple=()
                argument list of action_stop
            kwargs_stop: dict={}
                keyword arguments of action_stop
            action_cont: typing.Callable=None
                object (f.i. a function),
                which is called when task is continued.
            args_cont: tuple=()
                argument list of action_cont
            kwargs_cont: dict={}
                keyword arguments of action_cont
            action_final: typing.Callable=None
                object (f.i. a function),
                which is called when task is finished.
            args_final: tuple=()
                argument list of action_final
            kwargs_final: dict={}
                keyword arguments of action_final
            duration: Number=None
                duration of task (if action returns earlier, task will wait)
            join: bool=False
                flag, if child will be joined
            exc_handler: typing.Callable=None
                user defined handler of exceptions
        """
        self._action = action
        self._args = kwargs.pop('args', ())
        self._kwargs = kwargs.pop('kwargs', {})
        self._duration = kwargs.pop('duration', None)
        self._duration_rest: bool = False  # stopped while sleeping
        self._join: bool = kwargs.pop('join', False)
        self._gap = None  # stopped while sleeping
        self._num = kwargs.pop('num', None)
        self._exc_handler = kwargs.pop('exc_handler', None)

        self._next = None  # next Task in linked list
        self._root = self  # root Task
        self._netto_time = False
        self._cnt = 0  # number of action executions

        # the following are root only attributes
        self._action_start = kwargs.pop('action_start', None)
        self._args_start = kwargs.pop('args_start', ())
        self._kwargs_start = kwargs.pop('kwargs_start', {})
        self._action_stop = kwargs.pop('action_stop', None)
        self._args_stop = kwargs.pop('args_stop', ())
        self._kwargs_stop = kwargs.pop('kwargs_stop', {})
        self._action_cont = kwargs.pop('action_cont', None)
        self._args_cont = kwargs.pop('args_cont', ())
        self._kwargs_cont = kwargs.pop('kwargs_cont', {})
        self._action_final = kwargs.pop('action_final', None)
        self._args_final = kwargs.pop('args_final', ())
        self._kwargs_final = kwargs.pop('kwargs_final', {})

        self._state = STATE_INIT
        self._activity = ACTIVITY_NONE
        self._thread = None
        self._thread_start = None
        self._thread_cont = None
        self._restart = False
        self._lock = Lock()
        self._cond = Condition(self._lock)
        self._current = None  # current Task object
        self._current_scheduled = None  # scheduled time
        self._last = None  # last Task object in chain
        self._time_called_start = None  # time of last starting
        self._time_called_cont = None  # time of last continuing
        self._time_called_stop = None  # time of last stopping
        self._contained = []  # child tasks
        self._cont_join = None
        self._exc = None  # exception occured
        self._delay = None  # additional timespan in start or cont

        assert isinstance(self._action, Callable), \
            "action needs to be a callable"
        assert isinstance(self._args, tuple), 'args needs to be a tuple'
        assert not kwargs, 'unknown keyword arguments: ' + str(kwargs.keys())
        assert isinstance(self._kwargs, dict), \
            'kwargs needs to be a dictionary'

        assert (
            self._action_start is None or
            isinstance(self._action_start, Callable)
        ), "action_start needs to be a callable"
        assert isinstance(self._args_start, tuple), \
            'args_start needs to be a tuple'
        assert isinstance(self._kwargs_start, dict), \
            'kwargs_start needs to be a dictionary'

        assert (
            self._action_stop is None or
            isinstance(self._action_stop, Callable)
        ), "action_stop needs to be a callable"
        assert isinstance(self._args_stop, tuple), \
            'args_stop needs to be a tuple'
        assert isinstance(self._kwargs_stop, dict), \
            'kwargs_stop needs to be a dictionary'

        assert (
            self._action_cont is None or
            isinstance(self._action_cont, Callable)
            ), "action_cont needs to be a callable"
        assert isinstance(self._args_cont, tuple), \
            'args_cont needs to be a tuple'
        assert isinstance(self._kwargs_cont, dict), \
            'kwargs_cont needs to be a dictionary'

        assert (
            self._action_final is None or
            isinstance(self._action_final, Callable)
            ), "action_final needs to be a callable"
        assert isinstance(self._args_final, tuple), \
            'args_final needs to be a tuple'
        assert isinstance(self._kwargs_final, dict), \
            'kwargs_final needs to be a dictionary'

        assert isinstance(self._join, bool), \
            'join needs to be a bool value'
        assert not self._join or hasattr(self._action, '__self__'), \
            'only bounded methods can be joined'
        assert not self._join or isinstance(self._action.__self__, Task), \
            'only instances of Task can be joined'
        assert not self._join or self._action.__name__ in ('start', 'cont'), \
            'only methods start or cont can be joined'

        assert (
            self._duration is None or
            isinstance(self._duration, Number)
        ), 'duration needs to be a number'
        assert self._duration is None or self._duration >= 0, \
            'duration needs to be positive'

        assert self._num is None or isinstance(self._num, int), \
            'num must be an integer'
        assert self._num is None or self._num > 0, 'num must be positive'

        assert (
            self._exc_handler is None or
            isinstance(self._exc_handler, Callable)
        ), 'exc needs to be a callable'

    def _handle_exc(self, exc: Exception) -> None:
        '''This is the default exception handler and setting exc_handler
        replaces it. It calls method stop, then raises the
        exception. In linked Tasks, the default exception handler of
        the root is called. In tree structured Tasks, the default
        exception handler of the parent is called.

        Positional argument:
            exc:
                exception, which occured, but yet was not raised

        '''
        # called with unlocked self._root._lock

        if self._exc_handler is not None:
            # call own exception handler
            self._exc_handler(exc)
        elif self._root is not self:
            # let root task handle the exception
            self._root._handle_exc(exc)
        elif self in self._parents:
            # let parent task handle the exception
            self._parents[self]._handle_exc(exc)
        else:
            self.stop()
            raise exc

    def append(self, *tasks, copy=False) -> 'Task':
        """appends a task or a chain of tasks (both must be root tasks)"""
        assert self._root is self, 'appending to root tasks only'
        assert self._state in (
            STATE_INIT,
            STATE_FINISHED,
            STATE_STOPPED
        ), 'root task is currently executed'

        for task in tasks:
            assert task._root is task, 'append root tasks only'
            assert task._state in (
                STATE_INIT,
                STATE_FINISHED,
                STATE_STOPPED
            ), 'appended task is currently executed'
            assert self is not task or self._last is not task._last, \
                'never append tasks to themselves'

            if copy:
                to_append = Task._copy_task(task)
            else:
                to_append = task
            to_append.root = self  # recursive property
            if self._last is None and to_append._last is None:
                # neither self nor task are chains
                self._last = to_append
                self._next = to_append
            elif self._last is None:
                # self is no chain but task
                self._next = to_append
                self._last = to_append._last
                to_append._last = None
            elif to_append._last is None:
                # self is a chain, task is not
                self._last._next = to_append
                self._last = to_append
            else:
                # self and task, both are chains
                self._last._next = to_append
                self._last = to_append._last
                to_append._last = None
        return self

    def start(self, delay: Number = None) -> 'Task':
        """
        starts execution of task
        (finished or stopped tasks may be started again)

        Keyword Arguments:
            delay:
                sets the waiting time, before start occurs (in seconds)

        """
        # waits for lock, returns unlocked

        self._lock.acquire()
        assert delay is None or isinstance(delay, Number), \
            'delay needs to be a number'
        assert delay is None or delay > 0, 'delay needs to be positive'
        assert self._root is self, 'only root tasks can be started'
        assert self._state not in (
            STATE_TO_START,
            STATE_STARTED,
            STATE_TO_CONTINUE
        ), "can't start from state " + self._state
        assert self._thread_start is None, \
            "starting is already in progress"
        assert self._thread_cont is None, \
            "continuation is already in progress"

        self._delay = delay
        self._time_called_start = time()
        self._exc = None

        # start thread to do the rest
        self._thread_start = Thread(
            target=self._start2
        )
        self._thread_start.start()

        return self

    def _start2(self) -> None:
        assert current_thread() == self._thread_start, \
            '_start2 runs in unexpected thread'
        assert self._lock.locked(), \
            '_start has been called unlocked'
        # returns unlocked

        if self._state == STATE_TO_STOP:
            # wait until stopping has finished
            self._activity = ACTIVITY_JOIN
            if self._thread_cont is not None:
                self._lock.release()
                try:
                    self._thread_cont.join()
                except Exception:
                    pass
                self._lock.acquire()
            if self._thread is not None:
                self._lock.release()
                try:
                    self._thread.join()
                except Exception:
                    pass
                self._lock.acquire()
            self._activity = ACTIVITY_NONE
            if (
                self._state in (STATE_STOPPED, STATE_FINISHED) and
                self._thread_start is current_thread()
            ):
                if self._state == STATE_STOPPED:
                    if self._current is not None:
                        self._current._cnt = 0
                        self._current._duration_rest = False
                        self._current._gap = None
                        self._current = None
                        self._current_scheduled = None
            else:
                # TODO: explicit handling
                raise RuntimeError('concurrent method calling')

        self._state = STATE_TO_START

        # delay
        if self._delay is not None:
            delay_rest = self._delay - time() + self._time_called_start
            if delay_rest <= 0:
                self._delay = None
            else:
                self._activity = ACTIVITY_SLEEP
                self._cond.wait(self._delay)
                self._activity = ACTIVITY_NONE
                if (
                    self._state == STATE_TO_START and
                    current_thread() is self._thread_start
                ):
                    self._delay = None
                elif self._state == STATE_TO_STOP:
                    self._final()
                    return
                else:
                    # TODO: explicit handling
                    raise RuntimeError('concurrent method calling')

        # execution
        self._restart = False
        if self._action_start is not None:
            self._action_start(*self._args_start, **self._kwargs_start)
        self._state = STATE_STARTED
        self._time_called_stop = None

        self._current = self
        self._current_scheduled = time()

        self._thread = self._thread_start
        self._thread_start = None

        self._execute()

    def join(self) -> 'Task':
        """
        joins the thread of the task

        """
        # does not care about locking

        assert self._root is self, "only root tasks can be joined"
        assert self._state != STATE_INIT, \
            "can't join tasks in state " + str(self._state)

        try:
            self._thread_start.join()
        except Exception:
            pass

        try:
            self._thread_cont.join()
        except Exception:
            pass

        try:
            self._thread.join()
        except Exception:
            pass

        return self

    def stop(self) -> 'Task':
        """Stops execution as fast as possible.  Allows to continue with
        method ``cont()`` or restart with method ``start()``.  Already
        finished tasks silently do nothing

        """
        # waits for lock, returns unlocked
        self._lock.acquire()

        assert self is self._root, 'only root tasks can be stopped'
        assert self._state not in (
            STATE_INIT,
            STATE_STOPPED
        ), "can't stop from state: " + self._state

        self._time_called_stop = time()

        # old stopping still in progress
        if self._state == STATE_TO_STOP:
            self._lock.release()
            return self

        # already finished
        if self._state == STATE_FINISHED:
            self._lock.release()
            return self

        # interrupt sleeping
        if self._activity is ACTIVITY_SLEEP:
            self._cond.notify()

        # manage contained tasks
        not_stopped = []
        for task in self._contained:
            if (
                task not in self._parents or
                self._parents[task] is not self
            ):
                continue
            task.lock.acquire()
            if task._state in (
                    STATE_TO_START,
                    STATE_STARTED,
                    STATE_TO_CONTINUE
            ):
                not_stopped.append(task)
            task.lock.release()
        for task in not_stopped:
            task.stop()

        self._state = STATE_TO_STOP

        self._lock.release()
        return self

    def cont(self, delay: Number = None) -> 'Task':
        """
        continues a stopped task (must be a root task)

        Keyword Arguments:
            delay:
                sets waiting time for next action execution (in seconds)
        """
        # waits for lock, returns unlocked
        self._lock.acquire()

        assert self is self._root, 'only root tasks can be continued'
        assert delay is None or isinstance(delay, Number), \
            'delay needs to be a number'
        assert delay is None or delay > 0, 'delay needs to be positive'
        assert self._state in (
            STATE_STOPPED,
            STATE_TO_STOP,
            STATE_FINISHED
        ), "can't continue from state: {} (task: {})".format(
            self._state,
            self
        )
        assert self._exc is None, \
            "last execution stopped with an exception"

        # if regularly finished: silently do nothing
        if self._state == STATE_FINISHED:
            self._lock.release()
            return self

        self._time_called_cont = time()

        if delay is not None:
            self._delay = delay
            if self._current_scheduled is not None:
                self._current_scheduled += (
                    self._time_called_cont -
                    self._time_called_stop +
                    delay
                )
        elif self._current_scheduled is not None:
            self._current_scheduled += (
                self._time_called_cont -
                self._time_called_stop
            )

        self._thread_cont = Thread(
            target=self._cont2
        )
        self._thread_cont.start()

        return self

    def _cont2(self) -> None:
        assert current_thread() == self._thread_cont, \
            '_cont2 runs in unexpected thread'
        assert self._lock.locked(), '_cont2 has been called unlocked'

        if (
                self._current is None and not self._contained or
                self._restart
        ):
            self._time_called_start = self._time_called_cont
            self._time_called_cont = None
            self._thread_start = self._thread_cont
            self._thread_cont = None
            self._start2()
            return

        # STATE_TO_CONTINUE and waiting on stopping
        if self._state == STATE_STOPPED:
            self._state = STATE_TO_CONTINUE
        else:
            # wait until current stopping process has finished
            self._activity = ACTIVITY_JOIN
            self._lock.release()
            self._thread.join()
            self._lock.acquire()
            self._activity = ACTIVITY_NONE
            if (
                self._state == STATE_FINISHED and
                self._thread_cont is current_thread()
            ):
                # already finished, nothing to continue
                self._lock.release()
                return
            elif (
                self._state == STATE_STOPPED and
                self._thread_cont is current_thread()
            ):
                self._state = STATE_TO_CONTINUE
            else:
                # TODO: explicit handling
                raise RuntimeError('concurrent method calling')

        # delay
        if self._delay is not None:
            delay_rest = self._delay - time() + self._time_called_cont
            if delay_rest <= 0:
                self._delay = None
            else:
                self._activity = ACTIVITY_SLEEP
                self._cond.wait(delay_rest)
                self._activity = ACTIVITY_NONE
                self._lock.release()
                self._lock.acquire()
                if (
                    self._state == STATE_TO_CONTINUE and
                    current_thread() is self._thread_cont
                ):
                    self._delay = None
                elif (
                    self._state == STATE_TO_STOP and
                    current_thread() is self._thread_cont
                ):
                    self._final()
                    return
                else:
                    # TODO: explicit handling
                    raise RuntimeError('concurrent method calling')

        if self._action_cont is not None:
            self._action_cont(*self._args_cont, **self._kwargs_cont)

        self._state = STATE_STARTED
        self._time_called_stop = None
        self._thread = self._thread_cont
        self._thread_cont = None

        # continue the contained tasks
        if self._contained is not None:
            for task in self._contained:

                if task._state == STATE_FINISHED:
                    continue

                if (
                    task not in self._parents or
                    self._parents[task] is not self
                ):
                    continue

                task.cont()
            if self._cont_join is not None:
                self._activity = ACTIVITY_JOIN
                self._lock.release()
                self._cont_join.join()
                self._lock.acquire()
                self._activity = ACTIVITY_NONE
                if (
                    self._state != STATE_STARTED or
                    current_thread() is not self._thread_cont
                ):
                    self._final()
                    return

        if self._current is None:
            self._final()
        else:
            self._current._execute()

    def _execute(self) -> None:
        '''recusively executes one chain link
        '''
        assert current_thread() == self._root._thread, \
            '_execute runs in unexpected thread'
        assert self._root._lock.locked(), '_execute has been called unlocked'
        # returns unlocked

        if not self._duration_rest:
            pass
            # action_scheduled = self._root._current_scheduled

        while True:

            if self._root._state != STATE_STARTED:
                # someone called stop
                self._final()
                return

            if self._duration_rest:
                # no actions, only sleeping
                break

            if self._gap is not None:
                time_gap_started = time()
                self._root._activity = ACTIVITY_SLEEP
                self._root._cond.wait(self._gap)
                self._root._activity = ACTIVITY_NONE
                if self._root._state == STATE_STARTED:
                    # full sleeping done
                    self._gap = None
                else:
                    # sleeping has been interrupted
                    self._gap -= time() - time_gap_started
                    if self._gap < 0:
                        self._gap = None
                    self._final()
                    return

            time_action_started = time()
            try:
                gap = self._wrapper()
            except Exception as exc:
                if self._root._lock.locked():
                    self._root._lock.release()
                self._root._exc = exc
                self._handle_exc(exc)
                # maybe _handle_exc didn't raise an exception
                gap = -1
                self._root._exc = None
                self._root._lock.acquire()

            self._cnt += 1

            # action is done
            if (
                    gap == -1 or
                    (self._num is not None and self._cnt >= self._num)
            ):
                self._gap = None
                break

            # immediately call action again
            if gap == 0:
                self._gap = None
                continue

            if self._netto_time:
                self._gap = gap
            else:
                self._gap = gap - time() + time_action_started

        self._cnt = 0

        # duration
        if self._duration is not None:
            duration_rest = (
                self._duration -
                time() +
                self._root._current_scheduled
            )
            if duration_rest > 0:
                self._root._activity = ACTIVITY_SLEEP
                self._root._cond.wait(duration_rest)
                self._root._activity = ACTIVITY_NONE
                if self._root._state == STATE_STARTED:
                    # full sleeping done
                    self._duration_rest = False
                else:
                    # sleeping has been interrupted
                    duration_rest = (
                        self._duration -
                        time() +
                        self._root._current_scheduled
                    )
                    if duration_rest > 0:
                        self._duration_rest = True
                    else:
                        self._duration_rest = False
                    self._final()
                    return

        # next chain link
        if self._next:
            self._root._current = self._next
            if self._duration is not None:
                self._root._current_scheduled += self._duration
            else:
                self._root._current_scheduled = time()
            self._next._execute()
        else:
            self._final()

    def _wrapper(self) -> int:
        '''runs wrapper_before, action, wrapper_after
        returns -1 (no repeated calling)
        '''
        assert current_thread() == self._root._thread, \
            '_wrapper runs in unexpected thread'
        assert self._root._lock.locked(), '_wrapper has been called unlocked'

        self._wrapper_before()
        self._action(*self._args, **self._kwargs)
        self._wrapper_after()
        return -1

    def _wrapper_before(self) -> None:
        '''adds child task to _contained,
        guaranties, that contunuation will finish joining,
        sets parent link,
        manages lock and activity
        '''
        assert current_thread() == self._root._thread, \
            '_wrapper_before runs in unexpected thread'
        assert self._root._lock.locked(), \
            '_wrapper_before has been called unlocked'
        # returns unlocked

        is_task = (
            hasattr(self._action, '__self__') and
            isinstance(self._action.__self__, Task)
        )
        name = self._action.__name__

        if is_task:
            task = self._action.__self__
            if name == 'join' and task in self._root._contained:
                self._root._cont_join = task
            elif name in ('start', 'cont'):
                if self._join:
                    self._root._cont_join = task
                if task not in self._root._contained:
                    self._root._contained.append(task)
                self._parents.update({task: self._root})

        # action may be long lasting
        if (
            not is_task or
            name not in ('start', 'cont')
        ):
            if is_task and name == 'join':
                self._root._activity = ACTIVITY_JOIN
            else:
                self._root._activity = ACTIVITY_BUSY
            self._root._lock.release()

    def _wrapper_after(self) -> None:
        '''does joining,
        manages lock and activity
        '''
        assert current_thread() == self._root._thread, \
            '_wrapper_after runs in unexpected thread'
        # returns locked

        is_task = (
            hasattr(self._action, '__self__') and
            isinstance(self._action.__self__, Task)
        )
        name = self._action.__name__

        # action may be long lasting
        if self._join:
            self._root._activity = ACTIVITY_JOIN
            self._root._lock.release()
            self._action.__self__.join()
            self._root._lock.acquire()
            self._root._activity = ACTIVITY_NONE
        elif (
            not is_task or
            name not in ('start', 'cont')
        ):
            self._root._lock.acquire()
            self._root._activity = ACTIVITY_NONE

        assert self._root._lock.locked(), \
            '_wrapper_after must be locked'

        # ???
        if (is_task and name in ('start', 'stop', 'cont', 'join')):
            task = self._action.__self__
            state = task.state
            if (
                    self._root._cont_join and
                    (
                        self._root._state == STATE_STARTED or
                        state == STATE_FINISHED
                    )
            ):
                self._root._cont_join = None

            if (
                    (state == STATE_FINISHED or name == 'stop') and
                    task in self._root._contained
            ):
                self._root._contained.remove(task)

            if (
                    name == "stop" and
                    task in self._parents
            ):
                self._parents.pop(task)

    def _final(self, outstand=False) -> None:
        assert self._root._lock.locked(), \
            '_final has been called unlocked'
        assert self._root._state in (STATE_STARTED, STATE_TO_STOP), \
            '_final has been called in incorrect state: ' + \
            self._root._state
        # returns unlocked

        self._root._contained = self._join_contained()

        # regularly finished
        if self._root._state == STATE_STARTED:
            self._root._state = STATE_FINISHED

        # stopped in starting process
        elif self._root._thread_start is not None:
            self._root._delay -= time() - self._root._time_called_start
            if self._root._delay < 0:
                self._root._delay = None
            self._root._state = STATE_STOPPED

        # stopped in continuation process
        elif self._root._thread_cont is not None:
            # self._root._current = self
            self._root._delay -= time() - self._root._time_called_cont
            if self._root._delay < 0:
                self._root._delay = None
            self._root._state = STATE_STOPPED

        # stopped, but already finished
        elif (
                self._next is None and
                not self._root._contained and
                not self._duration_rest and
                self._gap is None and
                (self._num is None or self._cnt == self._num)
        ):
            self._root._state = STATE_FINISHED

        # stopped and at least one action done
        else:
            # all done but unfinished children
            if (
                self._next is None and
                not self._duration_rest and
                self._gap is None and
                (self._num is None or self._cnt == self._num)
            ):
                self._root._current = None
                self._root._current_scheduled = None

            if self._root._action_stop is not None:
                self._root._action_stop(
                    *self._root._args_stop,
                    **self._root._kwargs_stop
                )
            self._root._state = STATE_STOPPED

        if self._root._state == STATE_FINISHED:
            if self._root._action_final is not None:
                self._root._action_final(
                    *self._root._args_final,
                    **self._root._kwargs_final
                )
            if self._root in self._parents:
                self._parents.pop(self._root)
            self._root._thread = None
            self._root._thread_start = None
            self._root._thread_cont = None
            self._root._current = None
            self._root._current_scheduled = None
            self._root._delay = None
        self._root._lock.release()

    def _join_contained(self) -> list:
        '''
        waits until all contained tasks stop running

        Returns:
            list of all contained taskes, which did not end in STATE_FINISHED
        '''
        assert self._root._lock.locked(), \
            '_final has been called unlocked'
        # returns locked

        contained = self._root._contained
        self._root._activity = ACTIVITY_JOIN
        self._root._lock.release()

        not_finished = []
        for task in contained:
            if (
                    task not in self._parents or
                    self._parents[task] is not self._root
            ):
                continue
            task.join()
            if task.state != STATE_FINISHED:
                not_finished.append(task)

        self._root._lock.acquire()
        self._root._activity = ACTIVITY_NONE
        return not_finished

    @property
    def lock(self) -> Lock:
        """
        the tasks lock
        """
        assert self._root is self, \
            "only root tasks can be asked about their lock"
        return self._lock

    @property
    def state(self) -> str:
        """
        current state of the task (or chain of tasks)
        """
        with self._lock:
            value = self.state_no_lock
        return value

    @property
    def state_no_lock(self) -> str:
        """
        current state of the task (or chain of tasks)
        """
        assert self._root is self, \
            "only root tasks can be asked about their state"
        return self._state

    @property
    def root(self):
        """
        root task of the chain.
        A root task returns itself
        """
        return self._root

    @root.setter
    def root(self, task):
        assert isinstance(task, Task), 'root needs to be a Task'
        assert task._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        self._root = task
        if self._next:
            self._next.root = task

    @property
    def activity(self) -> str:
        """
        current activity
        """
        self._root._lock.acquire()
        assert self._root is self, \
            'only root tasks can be asked about their activity'
        value = self.activity_no_lock
        self._root._lock.release()
        return value

    @property
    def activity_no_lock(self) -> str:
        """
        current activity
        """
        return self._activity

    @property
    def action_start(self):
        """
        callable, which is called when starting the task
        """
        assert self._root is self, \
            'only root tasks can be asked about their action_start'
        return self._action_start

    @action_start.setter
    def action_start(self, value: Callable):
        self._root._lock.acquire()
        assert value is None or isinstance(value, Callable), \
            'action_start needs to be None or a callable'
        assert self._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        assert self._root is self, \
            'only root tasks allow to set their action_start'
        self._action_start = value
        self._root._lock.release()

    @property
    def action_stop(self):
        """
        callable, which is called in case of stopping the task
        """
        assert self._root is self, \
            'only root tasks can be asked about their action_stop'
        return self._action_stop

    @action_stop.setter
    def action_stop(self, value: Callable):
        self._root._lock.acquire()
        assert value is None or isinstance(value, Callable), \
            'action_stop needs to be None or a callable'
        assert self._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        assert self._root is self, \
            'only root tasks allow to set their action_stop'
        self._action_stop = value
        self._root._lock.release()

    @property
    def action_cont(self):
        """
        callable, which is called in case of continuing the task
        """
        assert self._root is self, \
            'only root tasks can be asked about their action_cont'
        return self._action_cont

    @action_cont.setter
    def action_cont(self, value: Callable):
        self._root._lock.acquire()
        assert value is None or isinstance(value, Callable), \
            'action_cont needs to be None or a callable'
        assert self._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        assert self._root is self, \
            'only root tasks allow to set their action_cont'
        self._action_cont = value
        self._root._lock.release()

    @property
    def action_final(self):
        """
        callable, which is called when finishing the task
        """
        assert self._root is self, \
            'only root tasks can be asked about their action_final'
        return self._action_final

    @action_final.setter
    def action_final(self, value: Callable):
        self._root._lock.acquire()
        assert value is None or isinstance(value, Callable), \
            'action_final needs to be None or a callable'
        assert self._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        assert self._root is self, \
            'only root tasks allow to set their action_final'
        self._action_final = value
        self._root._lock.release()

    @property
    def args_start(self):
        """
        arguments of action_start,
        which is called when starting the task
        """
        assert self._root is self, \
            'only root tasks can be asked about their args_start'
        return self._args_start

    @args_start.setter
    def args_start(self, value: tuple):
        self._root._lock.acquire()
        assert isinstance(value, tuple), 'args_start needs to be a tuple'
        assert self._root._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        assert self._root is self, \
            'only root tasks allow to set their args_start'
        self._args_start = value
        self._root._lock.release()

    @property
    def args_stop(self):
        """
        arguments of action_stop, which is called in case of stopping the task
        """
        assert self._root is self, \
            'only root tasks can be asked about their args_stop'
        return self._args_stop

    @args_stop.setter
    def args_stop(self, value: tuple):
        self._root._lock.acquire()
        assert isinstance(value, tuple), 'args_stop needs to be a tuple'
        assert self._root._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        assert self._root is self, \
            'only root tasks allow to set their args_stop'
        self._args_stop = value
        self._root._lock.release()

    @property
    def args_cont(self):
        """
        arguments of action_cont,
        which is called in case of continuing the task
        """
        assert self._root is self, \
            'only root tasks can be asked about their args_cont'
        return self._args_cont

    @args_cont.setter
    def args_cont(self, value: tuple):
        self._root._lock.acquire()
        assert isinstance(value, tuple), 'args_cont needs to be a tuple'
        assert self._root._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        assert self._root is self, \
            'only root tasks allow to set their args_cont'
        self._args_cont = value
        self._root._lock.release()

    @property
    def args_final(self):
        """
        arguments of action_cont,
        which is called in case of continuing the task
        """
        assert self._root is self, \
            'only root tasks can be asked about their args_final'
        return self._args_final

    @args_final.setter
    def args_final(self, value: tuple):
        self._root._lock.acquire()
        assert isinstance(value, tuple), 'args_final needs to be a tuple'
        assert self._root._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        assert self._root is self, \
            'only root tasks allow to set their args_final'
        self._args_final = value
        self._root._lock.release()

    @property
    def kwargs_start(self):
        """
        keyword arguments of action_start,
        which is called when starting the task
        """
        assert self._root is self, \
            'only root tasks can be asked about their kwargs_start'
        return self._kwargs_start

    @kwargs_start.setter
    def kwargs_start(self, value: dict):
        self._root._lock.acquire()
        assert isinstance(value, dict), \
            'kwargs_start needs to be a dictionary'
        assert self._root._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        assert self._root is self, \
            'only root tasks allow to set their kwargs_start'
        self._kwargs_start = value
        self._root._lock.release()

    @property
    def kwargs_stop(self):
        """
        keyword arguments of action_stop,
        which is called in case of stopping the task
        """
        assert self._root is self, \
            'only root tasks can be asked about their kwargs_stop'
        return self._kwargs_stop

    @kwargs_stop.setter
    def kwargs_stop(self, value: dict):
        self._root._lock.acquire()
        assert isinstance(value, dict), \
            'kwargs_stop needs to be a dictionary'
        assert self._root._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        assert self._root is self, \
            'only root tasks allow to set their kwargs_stop'
        self._kwargs_stop = value
        self._root._lock.release()

    @property
    def kwargs_cont(self):
        """
        keyword arguments of action_cont,
        which is called in case of continuing the task
        """
        assert self._root is self, \
            'only root tasks can be asked about their kwargs_cont'
        return self._kwargs_cont

    @kwargs_cont.setter
    def kwargs_cont(self, value: dict):
        self._root._lock.acquire()
        assert isinstance(value, dict), \
            'kwargs_cont needs to be a dictionary'
        assert self._root._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        assert self._root is self, \
            'only root tasks allow to set their kwargs_cont'
        self._kwargs_cont = value
        self._root._lock.release()

    @property
    def kwargs_final(self):
        """
        keyword arguments of action_final,
        which is called when finishing the task
        """
        assert self._root is self, \
            'only root tasks can be asked about their kwargs_final'
        return self._kwargs_final

    @kwargs_final.setter
    def kwargs_final(self, value: dict):
        self._root._lock.acquire()
        assert isinstance(value, dict), \
            'kwargs_final needs to be a dictionary'
        assert self._root._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        assert self._root is self, \
            'only root tasks allow to set their kwargs_final'
        self._kwargs_final = value
        self._root._lock.release()

    @property
    def exc_default(self):
        """
        default exception
        """
        return self._exc_default

    @property
    def exc_handler(self):
        """
        exception handler
        """
        return self._exc_handler

    @exc_handler.setter
    def exc_handler(self, value: Callable, ):
        """
        exception handler
        """
        self._root._lock.acquire()
        assert value is None or isinstance(value, Callable), \
            'exc_handler needs to be None or a callable'
        assert self._state in (
            STATE_INIT,
            STATE_STOPPED,
            STATE_FINISHED
        ), 'task is currently executed'
        self._exc_handler = value
        self._root._lock.release()


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
        assert 'join' not in kwargs, \
            "no keyword argument 'join' for instances of class Periodic"
        if hasattr(action, '__self__') and \
           isinstance(action.__self__, Task) and \
           action.__name__ == "start":
            kwargs.update({'join': True})
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
        assert 'join' not in kwargs, \
            "no keyword argument 'join' for instances of class Periodic"
        if (
                hasattr(action, '__self__') and
                isinstance(action.__self__, Task) and
                action.__name__ == "start"
        ):
            kwargs.update({'join': True})
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


class Sleep(Task):
    """
    Sleeps and can be stopped
    """
    def __init__(self, seconds: Number, **kwargs):
        """
        Positional Arguments:
            seconds: duration of sleeping
        """
        assert 'join' not in kwargs, \
            "no keyword argument 'duration' for instances of class Sleep"
        super().__init__(self._do_nothing, duration=seconds, **kwargs)

    def _do_nothing(self): pass
