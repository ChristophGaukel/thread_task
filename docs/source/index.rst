.. thread_task documentation master file, created by
   sphinx-quickstart on Wed Apr 22 12:59:19 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
   :maxdepth: 3
   :caption: Contents:


Readme
======
thread_task is built on top of
`threading <https://docs.python.org/3.8/library/threading.html>`_
and allows to organize tasks and run them parallel.

You can:

- build chains of tasks, which execute tasks sequentially in a single thread
- build parent child dependencies, which allows to construct trees of tasks
- stop tasks, which also stops the execution of child tasks
- continue tasks, which also continues the execution of child tasks
- restart finished or stopped tasks
- join tasks, which means waiting until the task and its children are finished

A thread_task is not like a function, it doesn't return results. Think
of it as an instruction to a reliable but independently acting
person. If feedback is needed, this can be done by callback
functions. You can also use mutable objects, which tasks get in
as arguments.

The following task types exist:

- Task: Executes a single task or a chain of tasks
- Repeated: Executes a task multiple times.
- Periodic: Executes a task periodically
- Sleep: sleeps for a given time, is similar to
  `time.sleep <https://docs.python.org/3.8/library/time.html#time.sleep>`_,
  but can be stopped and continued


Examples
===========

Wrapping a function into a Task object
--------------------------------------

**Task** allows to execute a function (or any other callable) in its own thread,
parallel to the commands of the main program.
Here, we define a funtion print_it. We wrap it into a Task object
and then call method start of the Task object.

.. code:: python

    from thread_task import Task
    from datetime import datetime
    

    def print_it():
        print(
            datetime.now().strftime('%H:%M:%S.%f'),
            'hello, world!'
        )
        

    Task(print_it).start(2)
    
    print(
        datetime.now().strftime('%H:%M:%S.%f'),
        'the last program statement'
    )

Method start has an optional argument **delay**, that
allows to add a timespan before the execution starts.
The program produced this output:

::

   15:48:11.626177 the last program statement
   15:48:13.626036 hello, world!

Indeed, function print_it is executed 2 sec. after the last program statement.
This could also be done with
`threading.Timer <https://docs.python.org/3.8/library/threading.html#threading.Timer>`_.

Building chains of tasks
------------------------

Task objects allow to append other Task objects and the result is also
a Task object. To be precise, Task objects are designed as linked
lists and the constructor returns the special case of a single chain
link. Appending modifies the Task object and adds one or multiple
chain links, but the result still is a Task object.  When a Task is
started, its chain links are executed one after the other.

.. code:: python

    from thread_task import Task
    from datetime import datetime
    
    
    def print_it(txt: str):
        print(
            datetime.now().strftime('%H:%M:%S.%f'),
            txt
        )
    
    
    Task(
        print_it,  # action
        args=('hello,',),
        duration=2
    ).append(
        Task(
            print_it,  # action
            args=('world!',)
        )
    ).start()

Here, we appended one Task object and built a chain of two tasks. The
first prints ``hello,``, the second prints ``world!``. We set the
first Task's **duration** to 2 sec.,  which sets a timespan between the
two printings. This example also shows, how positional arguments are
bount to the actions. This is done with keyword argument **args**,
which expects a tuple of values.

The output was:

::

   15:55:31.644113 hello,
   15:55:33.644894 world!


Stop and continue
-----------------
Task objects can be stopped and continued. Stopping means,
that method **stop** *tells* the Task to finish the current atom of execution, then stop.
The Task object will *know* its state and is ready to continue the execution, which is done by
method **cont**.

.. code:: python

   from thread_task import Task, Sleep, concat
   from datetime import datetime
   from time import sleep

   def print_it(txt: str):
       print(
           datetime.now().strftime('%H:%M:%S.%f'),
           txt
       )

   t = concat(
       Task(
           print_it,  # action
           args=('hello,',)
       ),
       Sleep(2),
       Task(
           print_it,  # action
           args=('world!',)
       )
   )
   t.action_stop = print_it
   t.args_stop = ('task has been stopped',)
   t.action_cont = print_it
   t.args_cont = ('task has been continued',)

   t.start()
   sleep(1)
   t.stop()
   sleep(4)
   t.cont()

The Task object itself is nearly the same as above. But we built it
with function **concat** instead of method append. This is just
another flavour and you can use the one, you prefer. Class **Sleep**
(a subclass of Task) is an alternative to setting a duration, but
Sleep sets an additional timespan of 2 sec., where duration adds a
waiting time after the execution of print_it to get 2
sec. alltogether. In our case of a short execution, this makes
practically no difference.
   
Here we did not use an anonymous Task object. We referenced it with
variable **t**. The reference allows us to get or set
arguments. Setting arguments modifies the Task. The reference is also
needed to stop or continue the Task object.

We use the attributes **action_stop** and **args_stop** to add special
logic for the the stopping process. action_stop must be a callable and
a third attribute kwargs_stop allows to set keyword arguments for
action_stop. action_stop could include some shutdown commands, here it
prints a message. The arguments **action_cont** and **args_cont**
(together with kwargs_cont) play the same role for the continuation
process.

Calling the methods **stop** and **cont** does the job of stopping and
continuing and the output shows, that class **Sleep** can be
interrupted (as duration would have too). In the middle of the sleeping,
the stopping takes place. When the Task is continued, it first ends
its sleeping, then it executes the next callable.

Our output was:

::

   16:04:25.626024 hello,
   16:04:26.627578 task has been stopped
   16:04:30.632176 task has been continued
   16:04:31.631967 world!

There were 1 sec. between starting and stopping and 4 sec. between stopping and continuing.
The task was designed for a timespan of 2 sec. between ``hello,`` and ``world!``,
which became 6 sec. with the additional delay between stopping and continuing.

Periodic actions
----------------

**Periodic** is another subclass of Task and allows to do things
periodically.  With **intervall**, it has one more positional argument,
which is the timespan between two executions of action. The
keyword argument **num** limits the number of
executions. Alternatively, the executions end, when action returns
``True``.

.. code:: python

    from thread_task import Task, Periodic

    # introduction
    print('Help me to give an enthusiastic welcome to our speaker.')

    # speech
    Periodic(
        2,  # intervall
        print,  # action
        args=('bla',),
        kwargs={'end': '', 'flush': True},
        num=3,
        duration=5
    ).append(
        Task(
            print,  # action
            duration=1
        )
    ).start(2).join()

    # reaction
    print('Warm applause.')
    
This program consists of three parts, the introduction of the speaker,
the speech und the reaction of the audience. The speech itself is a
chain of a Periodic and a Task object. It prints the string ``bla``
three times. Command print is called with two keyword arguments, end
and flush (see `print
<https://docs.python.org/3.8/library/functions.html#print>`_ for the
details). Between each call of print, there is a timespan of 2 sec. At
the end, print is called without any arguments, which prints a
newline. The Periodic is designed for a duration of 5 sec., the Task
for 1 sec. The speech is not only started, it also is joined. Method
**join** gives us back the well known chronology. This says, it makes
the program to wait until the task has finished, then it executes the
next command.

The output is:

::

    Help me, to give an enthusiastic welcome to our speaker.
    blablabla
    Warm applause.
    
The whole program was executed in 8 sec. After the introduction, there
was a delay of 2 sec. until the speach began and the speach needed 5
sec. for its three syllables (with newline). Setting a duration for
the Task made another delay before the audience reacted.

Repeated actions
----------------

**Repeated** is another subclass of Task and allows to do things
multiple times. Different from Periodic, here action is deciding if
and when to be called again. If action returns a positive number, this
will become the delay before the next execution. When it returns
``0``, it immediately will be called again and if it returns ``-1``,
the loop ends. action may also return a bool, then ``True`` is like
``-1`` and ends the loop, ``False`` is like ``0``, the next calling
will follow immediately. Also ``None`` is allowed to be returned and
has the meaning of ``0``. Like Periodic, you can limit the
number of executions with keyword argument **num**.

.. code:: python3

    from thread_task import Repeated
    from datetime import datetime
    
    
    class Accelerate:
        delay: int
    
        def __init__(self, delay):
            self.delay = delay + 1
    
        def step(self):
            print(
                datetime.now().strftime('%H:%M:%S.%f'),
                'Here I am'
            )
            self.delay -= 1
            return self.delay
    
    
    acc = Accelerate(5)
    Repeated(acc.step).start()

We define class Accelerate to demonstrate the functionality of
class Repeated. Accelerate has a method step, that returns
numbers, which become smaller and smaller in every calling.
Setting an initial value ``5`` means, that the first
calling of method step will return ``5``.

Repeated will call method step multiple times and it will react on its
return values. Per calling, the delay will become 1 sec. less.

The output was:

::

    17:15:35.719972 Here I am
    17:15:40.720291 Here I am
    17:15:44.720152 Here I am
    17:15:47.720289 Here I am
    17:15:49.720310 Here I am
    17:15:50.720290 Here I am
    17:15:50.720614 Here I am
    

Tree structured Tasks
---------------------

Task objects can not only be structured as chains, but also as
trees. Tree structures allow parallel execution inside of Tasks. When
a chain link of a Task object calls method **start** of another Task
object, this creates a parent-child dependency between them and forms
a tree structure of Task objects. The special benefit is, that any
call of parent's methods **stop** or **cont** will be passed to the
child. This allows to stop and continue the whole structure. We can
encapsulate complex dependencies behind a very simple API and we use
only four methods for its execution: start, stop, cont and join. All
of them we have seen already.

.. code:: python3

    from thread_task import Task, Periodic, concat
    from datetime import datetime
    from time import sleep
    
    
    def print_it(txt: str):
        print(
            datetime.now().strftime('%H:%M:%S.%f'),
            txt
        )
    
    
    data = {'switch': 'off'}
    
    
    def set_data(data: dict, value: str):
        data['switch'] = value
        print_it('set switch to ' + value)
    
    
    def get_data(data: dict) -> bool:
        value = data['switch']
        print_it('switch is ' + value)
        if value == 'on':
            return True
        else:
            return False
    
    
    t_set = concat(
        Task(
            set_data,
            args=(data, 'on'),
            action_stop=print_it,
            args_stop=('*** t_set has been stopped',),
            action_cont=print_it,
            args_cont=('*** t_set has been continued',)
        ),
        Task(
            print_it,
            args=('t_set has finished',)
        )
    )
    
    t = concat(
        Task(
            t_set.start,
            args=(4.5,),
            action_stop=print_it,
            args_stop=('*** t has been stopped',),
            action_cont=print_it,
            args_cont=('*** t has been continued',),
        ),
        Periodic(
            1,
            get_data,
            args=(data,)
        ),
        Task(
            print_it,
            args=('t has finished',)
        )
    )
    
    t.start()
    sleep(1.5)
    t.stop()
    sleep(3.5)
    t.cont()
    
This is a bit more complex than the other examples! We create 2 Task
objects **t_set**, and **t** and **t** becomes parent of **t_set**.

**data** is a mutable data object. We use it for the communication
between tasks. Function **set_data** writes values to the data
obeject, function **get_data** reads them.  In our case, get_data is
wrapped into a Periodic and will be called once per second.  If
get_data finds the value ``on``, it returns ``True``, which ends the
Periodic.  set_data is wrapped into t_set, a Task object that sets the
data object to ``on``.

t starts t_set with a delay of 4.5 sec. We added some text output to
the Task objects, which help us to understand, whats happening.

The output was:

::

    17:17:17.191292 switch is off
    17:17:18.191582 switch is off
    17:17:18.692961 *** t_set has been stopped
    17:17:18.693441 *** t has been stopped
    17:17:22.197571 *** t has been continued
    17:17:22.695968 switch is off
    17:17:23.695969 switch is off
    17:17:24.695989 switch is off
    17:17:25.196958 *** t_set has been continued
    17:17:25.197253 set switch to on
    17:17:25.197407 t_set has finished
    17:17:25.695987 switch is on
    17:17:25.696277 t has finished
    
The first two rows were printed by **get_data** and found the data
object in its initial state. As expected, there was a timespan of 1
sec. between these two printings.

1.5 sec. after starting **t**, we stopped it and **t** stopped its
child **t_set** before it stopped itself.  These two stoppings happend
within a very short time.

Another 3.5 sec. later we continued **t** and it continued its child.
**t** *remebers*, it was stopped in the middle of two actions of its
Periodic. This makes it to wait 0.5 sec. until its next call of
**get_data**.  **t_set** had a rest delay of 3 sec., which made it
answer this timespan after its continuation. Directly after this first
reaction, it called **set_data**, which changed the data object, then
it finished.

When **get_data** came to its next reading, it found the switch ``on``
and returned ``True``. This ended the Periodic and the final printing
came from the last chain link in **t**.


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

This program starts 2 Tasks and one of them raises an
error. Raising RuntimeError will concern Task t1, but
not Task t2 nor the main program execution.

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
t2 raised an exception.

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

If your Task object is structured as a chain or tree, the exception handler
with the highets priority will be called. We start with the exception handler of
the chain link, where the exception occured and then recusively do:

- if there is an explicitly setted exc_handler: call it
- if the current position is not the root link of a chain: call the exception handler of the root link.
- if the current position is a child Task: call the exception handler of the parent Task's root link.
- call the default exception handler of the current position, which does stopping at the current
  position, then raises the exception.

In other words: Climbs up the hierarchy of the structure. If, on
its way, it finds an explicitly setted exc_handler, it calls it. If it
doesn't find any, then it calls the default exception handler at the
top of the hierarchy, which does stopping at the top of the hierarchy
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

   
API documentation
=================
.. automodule:: thread_task

Static methods
--------------
.. autofunction:: thread_task.concat

Classes
-------

Task
~~~~

.. autoclass:: Task
   :members:

Sleep
~~~~~

.. autoclass:: Sleep
   :members:

Periodic
~~~~~~~~

.. autoclass:: Periodic
   :members:

Repeated
~~~~~~~~

.. autoclass:: Repeated
   :members:

      
Index
=====

* :ref:`genindex`
