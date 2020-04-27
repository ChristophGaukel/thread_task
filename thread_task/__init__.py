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
        \*tasks:
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
            join: bool=False
                flag if contained task will be joined
            duration: Number=None
                duration of task (if action returns earlier, task will wait)
            exc_handler: typing.Callable=None
                user defined handler of exceptions
        """
        self._action = action
        self._args = kwargs.pop('args', ())
        self._kwargs = kwargs.pop('kwargs', {})
        self._join = kwargs.pop('join', False)
        self._duration = kwargs.pop('duration', None)
        self._num = kwargs.pop('num', 0)

        self._next = None  # next Task in linked list
        self._root = self  # root Task
        self._time_end = None  # scheduled ending time
        self._netto_time = False
        self._cnt = 0  # number of action executions

        # the following are root only attributes
        self._state = STATE_INIT
        self._activity = ACTIVITY_NONE
        self._thread = None
        self._thread_start = None
        self._thread_cont = None
        self._restart = False
        self._lock = Lock()
        self._cond = Condition(self._lock)
        self._current = None  # current Task object
        self._last = None  # last Task object in chain
        self._time_called_start = None  # time of last starting
        self._time_called_cont = None  # time of last continuing
        self._time_called_stop = None  # time of last stopping
        self._time_action = None  # scheduled time of next action
        self._contained = []  # child tasks
        self._cont_join = None
        self._action_stop = kwargs.pop('action_stop', None)
        self._args_stop = kwargs.pop('args_stop', ())
        self._kwargs_stop = kwargs.pop('kwargs_stop', {})
        self._action_cont = kwargs.pop('action_cont', None)
        self._args_cont = kwargs.pop('args_cont', ())
        self._kwargs_cont = kwargs.pop('kwargs_cont', {})
        self._exc_handler = kwargs.pop('exc_handler', None)
        self._delay = None  # additional timespan in start or cont

        assert not kwargs, 'unknown keyword arguments: ' + str(kwargs.keys())
        assert isinstance(self._action, Callable), \
            "action needs to be a callable"
        assert isinstance(self._args, tuple), 'args needs to be a tuple'
        assert isinstance(self._kwargs, dict), \
            'kwargs needs to be a dictionary'
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
        assert isinstance(self._join, bool), \
            'join needs to be a bool value'
        assert not self._join or hasattr(self._action, '__self__'), \
            'only bounded methods can be joined'
        assert not self._join or isinstance(self._action.__self__, Task), \
            'only instances of Task can be joined'
        assert not self._join or self._action.__name__ in ["start", "cont"], \
            'only methods start or cont can be joined'
        assert (
            self._duration is None or
            isinstance(self._duration, Number)
        ), 'duration needs to be a number'
        assert self._duration is None or self._duration >= 0, \
            'duration needs to be positive'
        assert isinstance(self._num, int), 'num must be an integer'
        assert self._num >= 0, 'num must be positive'
        assert (
            self._exc_handler is None or
            isinstance(self._exc_handler, Callable)
        ), 'exc needs to be a callable'

    def _handle_exc(self, exc: Exception) -> None:
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
            # stop
            self.stop()
            raise exc

    def append(self, *tasks, copy=False) -> 'Task':
        """appends a task or a chain of tasks (both must be root tasks)"""
        try:
            assert self._root is self, 'appending to root tasks only'
            assert self._state in [
                STATE_INIT,
                STATE_FINISHED,
                STATE_STOPPED
            ], 'root task is currently executed'
        except Exception as exc:
            self._handle_exc(exc)

        for task in tasks:
            try:
                assert task._root is task, 'append root tasks only'
                assert task._state in [
                    STATE_INIT,
                    STATE_FINISHED,
                    STATE_STOPPED
                ], 'appended task is currently executed'
                assert self is not task or self._last is not task._last, \
                    'never append tasks to themselves'
            except Exception as exc:
                self._handle_exc(exc)

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
        self._root._lock.acquire()
        try:
            assert delay is None or isinstance(delay, Number), \
                'delay needs to be a number'
            assert delay is None or delay > 0, 'delay needs to be positive'
            assert self._root is self, 'only root tasks can be started'
            assert self._state not in [
                STATE_TO_START,
                STATE_STARTED,
                STATE_TO_CONTINUE
            ], "can't start from state " + self._state
            assert self._thread_start is None, \
                "starting is already in progress"
            assert self._thread_cont is None, \
                "continuation is already in progress"
        except Exception as exc:
            self._handle_exc(exc)

        self._delay = delay
        self._time_called_start = time()

        # start thread to do the rest
        self._thread_start = Thread(
            target=self._start2
        )
        self._thread_start.start()

        return self

    def _start2(self) -> None:
        '''runs in thread self._thread_start with lock acquired
        '''

        if self._state != STATE_TO_STOP:
            self._state = STATE_TO_START

        # delay
        if self._delay is not None:
            self._activity = ACTIVITY_SLEEP
            self._cond.wait(self._delay)
            self._activity = ACTIVITY_NONE
            if current_thread() is not self._thread_start:
                self._lock.release()
                return

        # wait until current stopping process has finished
        if self._state == STATE_TO_STOP:
            self._lock.release()
            self._thread.join()
            self._lock.acquire()
        if self._state in [STATE_STOPPED, STATE_FINISHED]:
            self._state = STATE_TO_START

        if self._state != STATE_TO_START:
            # maybe we will have start(), stop(), then cont(),
            # all of them in STATE_TO_STOP,
            # here we tell cont(), there was a restart
            self._restart = True
            self._thread_start = None
        else:
            # execution
            self._restart = False
            self._state = STATE_STARTED
            self._time_called_stop = None
            self._current = self
            self._cnt = 0
            self._time_action = time()
            if self._duration is not None:
                self._time_end = self._time_action + self._duration
            self._thread = self._thread_start
            self._thread_start = None
            self._execute()

    def join(self) -> None:
        """
        joins the thread of the task
        """
        try:
            assert self._root is self, "only root tasks can be joined"
            assert self._state != STATE_INIT, \
                "can't join tasks in state " + str(self._state)
        except Exception as exc:
            self._handle_exc(exc)
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

    def stop(self) -> None:
        """Stops execution as fast as possible.  Allows to continue with
        method ``cont()`` or restart with method ``start()``.  Already
        finished tasks silently do nothing

        """
        self._root._lock.acquire()

        try:
            assert self is self._root, 'only root tasks can be stopped'
            assert self._state not in [
                STATE_INIT,
                STATE_STOPPED
            ], "can't stop from state: " + self._state
        except Exception as exc:
            self._root._lock.release()
            self._handle_exc(exc)

        # old stopping still in progress
        if self._state == STATE_TO_STOP:
            self._root._lock.release()
            return

        # already finished
        if self._state == STATE_FINISHED:
            self._root._lock.release()
            return

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
            if task._state in [
                    STATE_TO_START,
                    STATE_STARTED,
                    STATE_TO_CONTINUE
            ]:
                not_stopped.append(task)
            task.lock.release()
        for task in not_stopped:
            task.stop()

        # handle delay
        self._time_called_stop = time()
        if self._state == STATE_TO_START and self._delay is not None:
            delay_rest = (
                self._delay +
                self._time_called_start -
                self._time_called_stop
            )
            if delay_rest > 0:
                self._delay = delay_rest
            else:
                self._delay = None
        elif self._state == STATE_TO_CONTINUE and self._delay is not None:
            delay_rest = (
                self._delay +
                self._time_called_cont -
                self._time_called_stop
            )
            if delay_rest > 0:
                self._delay = delay_rest
            else:
                self._delay = None
        else:
            self._delay = None

        if self._state == STATE_STARTED:
            self._state = STATE_TO_STOP  # stop when action is finished
            self._root._lock.release()
        elif self._state == STATE_TO_START:
            self._thread_start = None
            self._final(outstand=True)
        elif self._state == STATE_TO_CONTINUE:
            self._thread_cont = None
            self._final(outstand=True)

    def cont(self, delay: Number = None) -> 'Task':
        """
        continues a stopped task (must be a root task)

        Keyword Arguments:
            delay:
                sets waiting time for next action execution (in seconds)
        """
        self._lock.acquire()

        try:
            assert self is self._root, 'only root tasks can be continued'
            assert delay is None or isinstance(delay, Number), \
                'delay needs to be a number'
            assert delay is None or delay > 0, 'delay needs to be positive'
            assert self._state in [
                STATE_STOPPED,
                STATE_TO_STOP,
                STATE_FINISHED
            ], "can't continue from state: {} (task: {})".format(
                self._state,
                self
            )
            assert self._thread_start is None, \
                "starting is already in progress"
            assert self._thread_cont is None, \
                "continuation is already in progress"
        except Exception as exc:
            self._root._lock.release()
            self._handle_exc(exc)

        # if regularly finished: silently do nothing
        if self._state == STATE_FINISHED:
            self._lock.release()
            return self

        if delay is not None:
            self._delay = delay
        self._time_called_cont = time()

        self._thread_cont = Thread(
            target=self._cont2
        )
        self._thread_cont.start()
        return self

    def _cont2(self) -> None:
        '''runs in thread self._thread_cont with lock acquired'''

        if self._restart:
            self._thread_start = self._thread_cont
            self._thread_start = None
            self._start2()
            return

        if self._state != STATE_TO_STOP:
            self._state = STATE_TO_CONTINUE

        # delay
        if self._delay is not None:
            self._activity = ACTIVITY_SLEEP
            self._cond.wait(self._delay)
            self._activity = ACTIVITY_NONE
            if current_thread() is not self._thread_cont:
                self._lock.release()
                return

        # wait until current stopping process has finished
        if self._state == STATE_TO_STOP:
            self._lock.release()
            self._thread.join()
            self._lock.acquire()
        if self._state == STATE_STOPPED:
            self._state = STATE_TO_CONTINUE

        # corrections of absolute times
        time_delta = time() - self._time_called_stop
        if self._current:
            if self._time_action:
                self._time_action += time_delta
            if self._current._time_end:
                self._current._time_end += time_delta
        elif self._time_end:
            self._time_end += time_delta

        if self._state != STATE_TO_CONTINUE:
            return
        else:
            if self._action_cont:
                self._action_cont(*self._args_cont, **self._kwargs_cont)
            self._state = STATE_STARTED
            self._time_called_stop = None
            self._thread = self._thread_cont
            self._thread_cont = None
            if self._contained:
                for task in self._contained:

                    if task._state == STATE_FINISHED:
                        continue

                    if (
                        task not in self._parents or
                        self._parents[task] is not self
                    ):
                        continue

                    task.cont()
                    # task._lock.acquire()
                    # task._thread_cont = threading.Thread(
                    #     target=task._cont2
                    # )
                    # task._thread_cont.start()
                if self._cont_join is not None:
                    self._activity = ACTIVITY_JOIN
                    self._lock.release()
                    self._cont_join.join()
                    self._lock.acquire()
                    self._activity = ACTIVITY_NONE
                    if self._state != STATE_STARTED:
                        self._final()
                        return

            if self._current:
                if self._time_action:
                    gap = self._time_action - time()
                    if gap > 0:
                        self._activity = ACTIVITY_SLEEP
                        self._cond.wait(gap)
                        self._activity = ACTIVITY_NONE
                        # did someone change the state?
                        if self._state != STATE_STARTED:
                            self._final()
                            return
                self._current._execute()
            else:
                if self._time_end is not None:
                    gap = self._time_end - time()
                    if gap > 0:
                        self._activity = ACTIVITY_SLEEP
                        self._cond.wait(gap)
                        self._activity = ACTIVITY_NONE
                        # did someone change the state?
                        if self._state != STATE_STARTED:
                            self._final()
                            return
                self._time_end = None
                self._final()

    def _execute(self) -> None:
        while True:
            if self._root._state != STATE_STARTED:
                self._final(outstand=True)
                return
            try:
                gap = self._wrapper()
            except Exception as exc:
                self._handle_exc(exc)
            try:
                self._cnt += 1
                if gap == -1 or self._num > 0 and self._cnt >= self._num:
                    self._root._time_action = time()
                    break
                if gap == 0:
                    self._root._time_action = time()
                    continue
                if self._netto_time:
                    self._root._time_action = time() + gap
                    real_gap = gap
                else:
                    self._root._time_action += gap
                    real_gap = self._root._time_action - time()
            except Exception as exc:
                self._handle_exc(exc)
            if real_gap > 0:
                if self._root._state != STATE_STARTED:
                    self._final(outstand=True)
                    return
                self._root._activity = ACTIVITY_SLEEP
                self._root._cond.wait(real_gap)
                self._root._activity = ACTIVITY_NONE
        if self._time_end:
            self._root._time_action = self._time_end
            gap = self._root._time_action - time()
            if self._root._state == STATE_STARTED and gap > 0:
                self._root._activity = ACTIVITY_SLEEP
                self._root._cond.wait(gap)
                self._root._activity = ACTIVITY_NONE
            if self._root._state == STATE_STARTED:
                self._time_end = None
            elif self is not self._root:
                self._root._time_end = self._time_end
                self._time_end = None
        else:
            self._root._time_action = time()
        if self._next:
            self._root._current = self._next
            self._next._cnt = 0
            self._root._time_end = None
            if self._next._duration is not None:
                self._next._time_end = (
                    self._root._time_action + self._next._duration
                )
            self._next._execute()
        else:
            self._final()

    def _wrapper(self) -> int:
        '''runs wrapper1, action, wrapper2
        returns -1 (no repeated calling)
        '''
        self._wrapper1()
        self._action(*self._args, **self._kwargs)
        self._wrapper2()
        return -1

    def _wrapper1(self) -> None:
        '''adds child task to _contained,
        guaranties, that contunuation will finish joining,
        sets parent link,
        manages lock and activity
        '''
        if (
            hasattr(self._action, '__self__') and
            isinstance(self._action.__self__, Task) and
            self._action.__name__ in ["start", "cont", "join"]
        ):
            task = self._action.__self__
            name = self._action.__name__
            if (self._join or name == "join"):
                self._root._cont_join = task
            if name in ["start", "cont"]:
                if task not in self._root._contained:
                    self._root._contained.append(task)
                self._parents.update({task: self._root})
        if (
            not hasattr(self._action, '__self__') or
            not isinstance(self._action.__self__, Task) or
            self._action.__name__ not in ["start", "cont"] or
            self._action.__name__ == "start" and self._join
        ):
            self._root._activity = ACTIVITY_BUSY
            self._root._lock.release()

    def _wrapper2(self) -> None:
        '''does joining,
        manages lock and activity
        '''
        if self._join:
            self._action.__self__._thread.join()
        if (
                not hasattr(self._action, '__self__') or
                not isinstance(self._action.__self__, Task) or
                self._action.__name__ not in ["start", "cont"] or
                self._action.__name__ == "start" and self._join
        ):
            self._root._lock.acquire()
            self._root._activity = ACTIVITY_NONE
        if (
                hasattr(self._action, '__self__') and
                isinstance(self._action.__self__, Task) and
                self._action.__name__ in ["start", "stop", "cont", "join"]
        ):
            task = self._action.__self__
            name = self._action.__name__
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
                    (state == STATE_FINISHED or name == "stop") and
                    task in self._root._contained
            ):
                self._root._contained.remove(task)

            if (
                    name == "stop" and
                    task in self._parents
            ):
                self._parents.pop(task)

    def _final(self, outstand=False) -> None:
        self._root._contained = self._join_contained()
        # regularly finished
        if self._root._state == STATE_STARTED:
            self._root._state = STATE_FINISHED
        # in starting process
        elif self._root._state == STATE_TO_START:
            self._root._current = self
            if self._root._action_stop:
                self._root._action_stop(
                    *self._root._args_stop,
                    **self._root._kwargs_stop
                )
            self._root._state = STATE_STOPPED
        # in continuation process
        elif self._root._state == STATE_TO_CONTINUE:
            self._root._current = self
            if self._root._action_stop:
                self._root._action_stop(
                    *self._root._args_stop,
                    **self._root._kwargs_stop
                )
            self._root._state = STATE_STOPPED
        # in stopping process
        elif self._root._state == STATE_TO_STOP:
            # all done
            if (
                not self._next and
                not self._root._contained and
                not self._root._time_end and
                not outstand
            ):
                self._root._state = STATE_FINISHED
            # really stopped
            elif self._root._action_stop:
                self._root._action_stop(
                    *self._root._args_stop,
                    **self._root._kwargs_stop
                )

        if self._root._state == STATE_FINISHED:
            if self._root in self._parents:
                self._parents.pop(self._root)
            self._root._thread_cont = None
            self._root._current = None
            self._root._time_action = None
            self._root._delay = None
        else:
            if not self._next and not outstand:
                self._root._current = None
                self._root._time_action = None
            if self._root._thread_start:
                self._root._current = None
                self._root._time_action = None
                self._root._state = STATE_TO_START
            elif self._root._thread_cont:
                self._root._state = STATE_TO_CONTINUE
            else:
                self._root._state = STATE_STOPPED
        if self._root._time_action and self._root._time_action < time():
            self._root._time_action = None
        self._root._lock.release()

    def _join_contained(self) -> list:
        '''
        waits until all contained tasks stop running

        Returns:
        list of all contained taskes, which did not end in STATE_FINISHED
        '''
        contained = self._root._contained
        self._root._activity = ACTIVITY_JOIN
        self._root._lock.release()
        not_finished = []
        for task in contained:
            if (
                    task not in self._parents or
                    self._parents[task] is not self
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
        try:
            assert self._root is self, \
                "only root tasks can be asked about their lock"
        except Exception as exc:
            self._handle_exc(exc)
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
        try:
            assert self._root is self, \
                "only root tasks can be asked about their state"
        except Exception as exc:
            self._handle_exc(exc)
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
        try:
            assert isinstance(task, Task), 'root needs to be a Task'
            assert task._state in [
                STATE_INIT,
                STATE_STOPPED,
                STATE_FINISHED
            ], 'task is actually executed'
        except Exception as exc:
            self._handle_exc(exc)
        self._root = task
        if self._next:
            self._next.root = task

    @property
    def time_action(self) -> Number:
        """
        time of current (activity is ACTIVITY_BUSY) or next action,
        is in the format of time.time()
        """
        self._root._lock.acquire()
        try:
            assert self._root is self, \
                'only root tasks can be asked about their time_action'
        except Exception as exc:
            self._root._lock.release()
            self._handle_exc(exc)
        value = self.time_action_no_lock
        self._root._lock.release()
        return value

    @property
    def time_action_no_lock(self) -> Number:
        """
        time of current (activity is ACTIVITY_BUSY) or next action,
        is in the format of time.time()
        """
        min = self._time_action
        for task in self._contained:
            if (
                    task not in self._parents or
                    self._parents[task] is not self
            ):
                continue

            act = task.time_action
            if min is None or \
               act is not None and act < min:
                min = act
        return min

    @property
    def activity(self) -> str:
        """
        actual activity
        """
        self._root._lock.acquire()
        try:
            assert self._root is self, \
                'only root tasks can be asked about their activity'
        except Exception as exc:
            self._root._lock.release()
            self._handle_exc(exc)
        value = self.activity_no_lock
        self._root._lock.release()
        return value

    @property
    def activity_no_lock(self) -> str:
        """
        actual activity
        """
        return self._activity

    @property
    def action_stop(self):
        """
        callable, which is called in case of stopping the task
        """
        return self._action_stop

    @action_stop.setter
    def action_stop(self, value: Callable):
        self._root._lock.acquire()
        try:
            assert value is None or isinstance(value, Callable), \
                'action_stop needs to be None or a callable'
            assert self._state in [
                STATE_INIT,
                STATE_STOPPED,
                STATE_FINISHED
            ], 'task is actually executed'
        except Exception as exc:
            self._root._lock.release()
            self._handle_exc(exc)
        self._action_stop = value
        self._root._lock.release()

    @property
    def action_cont(self):
        """
        callable, which is called in case of continuing the task
        """
        try:
            assert self._root is self, \
                'only root tasks can be asked about their action_cont'
        except Exception as exc:
            self._handle_exc(exc)
        return self._action_cont

    @action_cont.setter
    def action_cont(self, value: Callable):
        self._root._lock.acquire()
        try:
            assert value is None or isinstance(value, Callable), \
                'action_cont needs to be None or a callable'
            assert self._state in [
                STATE_INIT,
                STATE_STOPPED,
                STATE_FINISHED
            ], 'task is actually executed'
        except Exception as exc:
            self._root._lock.release()
            self._handle_exc(exc)
        self._action_cont = value
        self._root._lock.release()

    @property
    def args_stop(self):
        """
        arguments of action_stop, which is called in case of stopping the task
        """
        return self._args_stop

    @args_stop.setter
    def args_stop(self, value: tuple):
        self._root._lock.acquire()
        try:
            assert isinstance(value, tuple), 'args_stop needs to be a tuple'
            assert self._root._state in [
                STATE_INIT,
                STATE_STOPPED,
                STATE_FINISHED
            ], 'task is actually executed'
        except Exception as exc:
            self._root._lock.release()
            self._handle_exc(exc)
        self._args_stop = value
        self._root._lock.release()

    @property
    def args_cont(self):
        """
        arguments of action_cont,
        which is called in case of continuing the task
        """
        return self._args_cont

    @args_cont.setter
    def args_cont(self, value: tuple):
        self._root._lock.acquire()
        try:
            assert isinstance(value, tuple), 'args_cont needs to be a tuple'
            assert self._root._state in [
                STATE_INIT,
                STATE_STOPPED,
                STATE_FINISHED
            ], 'task is actually executed'
        except Exception as exc:
            self._root._lock.release()
            self._handle_exc(exc)
        self._args_cont = value
        self._root._lock.release()

    @property
    def kwargs_stop(self):
        """
        keyword arguments of action_stop,
        which is called in case of stopping the task
        """
        return self._kwargs_stop

    @kwargs_stop.setter
    def kwargs_stop(self, value: dict):
        self._root._lock.acquire()
        try:
            assert isinstance(value, dict), \
                'kwargs_stop needs to be a dictionary'
            assert self._root._state in [
                STATE_INIT,
                STATE_STOPPED,
                STATE_FINISHED
            ], 'task is actually executed'
        except Exception as exc:
            self._root._lock.release()
            self._handle_exc(exc)
        self._kwargs_stop = value
        self._root._lock.release()

    @property
    def kwargs_cont(self):
        """
        keyword arguments of action_cont,
        which is called in case of continuing the task
        """
        return self._kwargs_cont

    @kwargs_cont.setter
    def kwargs_cont(self, value: dict):
        self._root._lock.acquire()
        try:
            assert isinstance(value, dict), \
                'kwargs_cont needs to be a dictionary'
            assert self._root._state in [
                STATE_INIT,
                STATE_STOPPED,
                STATE_FINISHED
            ], 'task is actually executed'
        except Exception as exc:
            self._root._lock.release()
            self._handle_exc(exc)
        self._kwargs_cont = value
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
        try:
            assert value is None or isinstance(value, Callable), \
                'exc_handler needs to be None or a callable'
            assert self._state in [
                STATE_INIT,
                STATE_STOPPED,
                STATE_FINISHED
            ], 'task is actually executed'
        except Exception as exc:
            self._root._lock.release()
            self._handle_exc(exc)
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
        else:
            kwargs.update({'join': False})
        super().__init__(action, **kwargs)
        assert isinstance(self._intervall, Number), \
            'intervall must be a number' + intervall
        assert self._intervall >= 0, 'intervall must be positive'
        assert isinstance(self._netto_time, bool), \
            'netto_time must be a bool value'

    def _wrapper(self):
        self._wrapper1()
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
        self._wrapper2()
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
        else:
            kwargs.update({'join': False})
        super().__init__(action, **kwargs)
        assert isinstance(self._netto_time, bool), \
            'netto_time must be a bool value'

    def _wrapper(self):
        self._wrapper1()
        value = self._action(*self._args, **self._kwargs)
        assert (
            isinstance(value, Task) or
            isinstance(value, Number) or
            isinstance(value, bool) or
            value is None
        ), 'action needs to return a number, a boolean or None'
        if (
            isinstance(value, Number) and
            value != -1 and
            value < 0
        ):
            err = RuntimeError(
                'if action returns a number, ' +
                'it must be positive or 0 or -1, but is ' +
                str(value)
            )
            self._handle_exc(err)
        if value is True:
            rc = -1
        elif isinstance(value, Task) or value is False or value is None:
            rc = 0
        else:
            rc = value
        self._wrapper2()
        return rc


class Sleep(Task):
    """
    Sleeps and can be stopped
    """
    def __init__(self, seconds: Number):
        """
        Positional Arguments:
            seconds: duration of sleeping
        """
        super().__init__(self._do_nothing, duration=seconds)

    def _do_nothing(self): pass
