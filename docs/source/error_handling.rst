==============
Error Handling
==============

Error handling in Task objects is a bit special and it's worth to take
some minutes to get the concept.

Exceptions are handled per thread
---------------------------------

Multithreading handles exceptions per thread! If an exception is raised in
one of the threads, this does not concern the other ones.

.. code:: python3

    from thread_task import Task
    
    
    def raise_error():
        raise RuntimeError
    
    
    t1 = Task(
        print,
        args=('t1 finished regularly',)
    )
    
    t2 = Task(raise_error)
    
    t1.start(1)
    t2.start()

This program starts two Tasks and one of them raises an
error. Raising RuntimeError will concern Task t2, but
not Task t1 nor the main program execution.

The output was:

::

   Exception in thread Thread-2:
    Traceback (most recent call last):
      File "/usr/lib/python3.6/threading.py", line 916, in _bootstrap_inner
        self.run()
      File "/usr/lib/python3.6/threading.py", line 864, in run
        self._target(*self._args, **self._kwargs)
      File "/home/christoph/.local/lib/python3.6/site-packages/thread_task/__init__.py", line 374, in _start2
        self._execute()
      File "/home/christoph/.local/lib/python3.6/site-packages/thread_task/__init__.py", line 641, in _execute
        self._handle_exc(exc)
      File "/home/christoph/.local/lib/python3.6/site-packages/thread_task/__init__.py", line 242, in _handle_exc
        raise exc
      File "/home/christoph/.local/lib/python3.6/site-packages/thread_task/__init__.py", line 639, in _execute
        gap = self._wrapper()
      File "/home/christoph/.local/lib/python3.6/site-packages/thread_task/__init__.py", line 696, in _wrapper
        self._action(*self._args, **self._kwargs)
      File "./test_error_01", line 8, in raise_error
        raise RuntimeError
    RuntimeError
    
    t1 finished regularly

Indeed, the main program execution and t1 finish regularly, even when
t2 raises an exception.

Default exception handler
-------------------------

Task objects have a default exception handler:

.. automethod:: thread_task.Task._handle_exc

The default exception handler calls method stop of the Task object
(later we will learn, which Task object), then raises the
exception. We demonstrate this by an example.

.. code:: python3

    from thread_task import Task


    def raise_error():
        raise RuntimeError
    
    
    Task(
        raise_error,
        action_stop=print,
        args_stop=('t has been stopped',)
    ).start()

produced this output:

::

    t has been stopped
    Exception in thread Thread-1:
    Traceback (most recent call last):
      File "/usr/lib/python3.6/threading.py", line 916, in _bootstrap_inner
        self.run()
      File "/usr/lib/python3.6/threading.py", line 864, in run
        self._target(*self._args, **self._kwargs)
      File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 377, in _start2
        self._execute()
      File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 649, in _execute
        self._handle_exc(exc)
      File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 244, in _handle_exc
        raise exc
      File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 647, in _execute
        gap = self._wrapper()
      File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 704, in _wrapper
        self._action(*self._args, **self._kwargs)
      File "./test_error_02", line 8, in raise_error
        raise RuntimeError
    RuntimeError
    
The first line shows, that method stop was called. The Task ends in
STATE_STOPPED. It can be restarted, but not continued.

If your Task object is structured as a chain or tree, the exception
handler with the highest priority will be called. We start with the
exception handler of the chain link, where the exception occured and
then recusively do:

- if there is an explicitly set exc_handler: call it
- else if the current chain link is not the root link of the chain: call
  the exception handler of the root link.
- else if the current Task is a child Task: call the exception
  handler of the parent Task's root link.
- else: call the default exception handler of the current chain link,
  which does stopping the current Task, then raises the
  exception.

In other words: It climbs up the hierarchy of the structure. If, on
its way, it finds an explicitly setted exc_handler, it calls it. If it
doesn't find any, then it calls the default exception handler at the
top of the hierarchy. The default exception handler calls method stop
and then raises the exception.

User defined exception handlers
-------------------------------

At any position in the hierarchical structure of a Task object, you
can implement your own exc_handler.

.. code:: python3

    from thread_task import Task, concat
    
    
    def raise_error():
        raise RuntimeError
    
    
    def my_exc_handler(exc: Exception):
        t_parent.stop()
        raise exc
    
    
    t_child = concat(
        Task(
            print,
            args=('t_child has been started',),
            action_stop=print,
            args_stop=('t_child has been stopped',)
        ),
        Task(
            raise_error
        ),
        Task(
            print,
            args=('t_child finished regularly',)
        )
    )
    
    t_parent = concat(
        Task(
            print,
            args=('t_parent has been started',),
            action_stop=print,
            args_stop=('t_parent has been stopped',),
            exc_handler=my_exc_handler
        ),
        Task(
            t_child.start,
            duration=.1
        ),
        Task(
            print,
            args=('t_parent finished regularly',)
        )
    ).start()

Here, **my_exc_handler** is placed on the top of the hierarchy, which
is the root link of the parent Task. The 2nd chain link of
**t_parent** starts **t_child** and the 2nd chain link of t_child
calls **raise_error**, which raises ``RuntimeError``. Setting a short
**duration** in the 2nd chain link of t_parent allows to stop t_parent
before it prints its final message.

The output:

::

   t_parent has been started
   t_child has been started
   t_child has been stopped
   Exception in thread Thread-2:
   Traceback (most recent call last):
     File "/usr/lib/python3.6/threading.py", line 916, in _bootstrap_inner
       self.run()
     File "/usr/lib/python3.6/threading.py", line 864, in run
       self._target(*self._args, **self._kwargs)
     File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 383, in _start2
       self._execute()
     File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 713, in _execute
       self._next._execute()
     File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 657, in _execute
       self._handle_exc(exc)
     File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 249, in _handle_exc
       self._root._handle_exc(exc)
     File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 252, in _handle_exc
       self._parents[self]._handle_exc(exc)
     File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 246, in _handle_exc
       self._exc_handler(exc)
     File "./test_error_03", line 13, in my_exc_handler
       raise exc
     File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 652, in _execute
       gap = self._wrapper()
     File "/home/christoph/src/python3/tmp/thread_task/__init__.py", line 724, in _wrapper
       self._action(*self._args, **self._kwargs)
     File "./test_error_03", line 8, in raise_error
       raise RuntimeError
   RuntimeError
   
   t_parent has been stopped

Thread-2 is the child's thread, where the exception occured. All the
error handling is done under control of this thread and raising the
exception ends only this thread.
   
Here, **my_exc_handler** does exactly, what the default exception
handler would have done. But setting an exc_handler allows to do
other things too, e.g. protocol into an error tracking tool.

If we want the Task stop silently, we replace my_exc_handler with:

.. code:: python3

    def my_exc_handler(exc: Exception):
        t_parent.stop()

and get this output:

::

   t_parent has been started
   t_child has been started
   t_child has been stopped
   t_parent has been stopped

We can even ignore the exception with:

.. code:: python3

    def my_exc_handler(exc: Exception):
        pass

If the exception handler does not raise an exception, t_child (which
is run by Thread-2) continues as if no exception occured. Here, it
waits until duration is over and then executes its next chain link.

The output was:

::
    
   t_parent has been started
   t_child has been started
   t_child finished regularly
   t_parent finished regularly

Threadless Tasks
----------------

If you start a Task with argument ``thread=False`` and
the Exception was raised by an action of this Task, the default error
handling becomes very familiar.

.. code:: python3

    from thread_task import Task


    def raise_error():
        raise RuntimeError
    
    
    Task(
        raise_error,
        action_stop=print,
        args_stop=('t has been stopped',)
    ).start(thread=False)

    print('regularly finished')

The output:

.. code-block:: none

  t has been stopped
  Traceback (most recent call last):
    File "./test_thread_task", line 14, in <module>
      ).start(thread=False)
    File "/home/christoph/src/python3/tmp/thread_task/task.py", line 723, in start
      self._start2(thread, _parent)
    File "/home/christoph/src/python3/tmp/thread_task/task.py", line 821, in _start2
      self._execute()
    File "/home/christoph/src/python3/tmp/thread_task/task.py", line 1175, in _execute
      self._handle_exc(exc)
    File "/home/christoph/src/python3/tmp/thread_task/task.py", line 619, in _handle_exc
      raise exc
    File "/home/christoph/src/python3/tmp/thread_task/task.py", line 1170, in _execute
      gap = self._wrapper()
    File "/home/christoph/src/python3/tmp/thread_task/task.py", line 1253, in _wrapper
      self._action(*self._args, **self._kwargs)
    File "./test_thread_task", line 7, in raise_error
      raise RuntimeError
  RuntimeError
  
The Task was executed by ``MainThread`` and when its action raised an
exception, the Task has been stopped, then it raised the exception.
The last command of the program was not executed because both, the
Task and the main program were executed by the same thread.
