.. thread_task documentation master file, created by
   sphinx-quickstart on Wed Apr 22 12:59:19 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
   :maxdepth: 3
   :caption: Contents:

.. title:: thread_task


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
functions. You can also use mutable objects, which multiple tasks work
with.

The following task types exist:

- Task: Executes a single callable or a chain of callables.
- Repeated: Executes a callable multiple times.
- Periodic: Executes a callable periodically
- Sleep: Sleeps for a given time, is similar to
  `time.sleep <https://docs.python.org/3.8/library/time.html#time.sleep>`_,
  but can be stopped and continued


Examples
===========

Wrapping a function into a Task object
--------------------------------------

:py:class:`~thread_task.Task` allows to execute a function (or any
other callable) in its own thread, parallel to the commands of the
main program.  Here, we define a funtion :py:func:`print_it`. We wrap
it into a :py:class:`~thread_task.Task` object and then call its
method :py:meth:`~thread_task.Task.start`.

.. code:: python3

  from thread_task import Task
  from datetime import datetime
  from threading import current_thread
  
  
  def print_it():
      print(
          '{} {:10s}: {}'.format(
              datetime.now().strftime('%H:%M:%S.%f'),
              current_thread().name,
              'hello, world!'
          )
      )
  
  
  t = Task(print_it)
  t.start(2)
  
  print(
      '{} {:10s}: {}'.format(
          datetime.now().strftime('%H:%M:%S.%f'),
          current_thread().name,
          'last instruction'
      )
  )

:py:meth:`~thread_task.Task.start` has an optional argument **delay**, that
allows to set a timespan (in sec.) before the execution starts.
The program produced this output:

.. code-block:: none

  09:36:12.454089 MainThread: last instruction
  09:36:14.454512 Thread-1  : hello, world!

Indeed, function :py:func:`print_it` is called 2 sec. after the
execution of the last program statement.
:py:attr:`threading.current_thread().name` gave us the name of the
current thread and we see, that the execution of :py:func:`print_it`
was done in thread ``Thread-1`` while ``MainThread`` executed the main
program. Calling method start of a Task object creates a new thread and
this thread executes the Task's action.


Callables with arguments
~~~~~~~~~~~~~~~~~~~~~~~~

Our first attempt called a function without any arguments. This is a
bit too simple for real life. Let's go one step further and modify
:py:func:`print_it`. The new function gets a positional argument and
we also allow keyword arguments to demonstrate the mechanism. If you
want your action be called with positional arguments, then call the
constructor of :py:class:`~thread_task.Task` with its keyword argument
**args**, which holds the argument tuple for the callable's
invocation, it defaults to (). If you want your action be called with
keyword arguments, use **kwargs**, which holds a dictionary of keyword
arguments and defaults to {}.

.. code:: python3

  from thread_task import Task
  from datetime import datetime
  from threading import current_thread
  
  
  def print_it(txt: str, **kwargs):
      print(
          '{} {:10s}: {}'.format(
              datetime.now().strftime('%H:%M:%S.%f'),
              current_thread().name,
              txt,
              kwargs
          )
      )
  
  
  Task(
      print_it,
      args=('hello, world!',),
      kwargs={'flush': True}
  ).start(2)
  
  print_it('last instruction', flush=True)

The output of this variant is not different from the one above. The
comparison of the last two instructions shows, how positional and
keyword arguments are handled.

Up to now, :py:class:`~thread_task.Task` seems not that much
innovative. It looks like another flavour of `threading.Timer
<https://docs.python.org/3.8/library/threading.html#threading.Timer>`_,
which does the job as well, but thread_task is more than that.
  

Building chains of tasks
------------------------

Task objects allow to :py:meth:`~thread_task.Task.append` other Task
objects, but the result still is a Task object. To be precise, Task
objects are designed as linked lists and the constructor returns the
special case of a single chain link. Appending modifies the Task
object and adds one or multiple chain links. Starting a Task means
executing its chain links one after the other. Appended Task objects
loose most of their functionality. If you still have a reference and
you call their methods or use their arguments, this usually will raise
exceptions.

.. code:: python3

  from thread_task import Task
  from datetime import datetime
  from threading import current_thread
  
  
  def print_it(txt: str):
      print(
          '{} {:10s}: {}'.format(
              datetime.now().strftime('%H:%M:%S.%f'),
              current_thread().name,
              txt
          )
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

Here, we appended one Task object and built a chain of two
links. The first prints ``hello,``, the second prints ``world!``. We
set the first Task's **duration** to 2 sec., which sets a timespan
between the two printings.

The output was:

.. code-block:: none

   09:55:31.644113 Thread-1  : hello,
   09:55:33.644894 Thread-1  : world!

As you can see, both chain links were executed in thread ``Thread-1``.

Method :py:meth:`~thread_task.concat` is an alternative to append.
It's just another flavour and does the very same thing.

.. code:: python3

  from thread_task import Task, concat
  from datetime import datetime
  from threading import current_thread
  
  
  def print_it(txt: str):
      print(
          '{} {:10s}: {}'.format(
              datetime.now().strftime('%H:%M:%S.%f'),
              current_thread().name,
              txt
          )
      )
  
  
  concat(
      Task(
          print_it,  # action
          args=('hello,',),
          duration=2
      ),
      Task(
          print_it,  # action
          args=('world!',)
      )
  ).start()

The result is the same. In both cases the first Task is the one, which
has been modified and can be started. The following ones are
unusable. You can't start them because they `know`, that they became
links in a chain. If you prefer appending or concatenating, that's
your choice.


Stopping
--------

Task objects can be stopped. Stopping means, that method
:py:meth:`~thread_task.Task.stop` *tells* the Task to finish the
current atom of execution, then stop. The Task object always *knows*
its state and when the stopping process ended, the Task is ready to
be continued or started again.

To be precise: calling method stop changes the attribute
**Task.state** from **STATE_STARTED** to **STATE_TO_STOP**. This part
of the stopping process is fast and runs under control of the thread,
that called method stop. Internally, when the Task object realizes its
change of state, it does all the actions for a controlled
stopping. When all this is done, its state changes from STATE_TO_STOP to
state **STATE_STOPPED**. Then, the Task's thread ends.

.. _stopping_example:

.. code:: python3

  from thread_task import Task, concat
  from datetime import datetime
  from time import sleep
  from threading import current_thread
  
  
  def print_it(txt: str):
      print(
          '{} {:10s}: {}'.format(
              datetime.now().strftime('%H:%M:%S.%f'),
              current_thread().name,
              txt
          )
      )
  
  
  t = concat(
      Task(
          print_it,  # action
          args=('hello,',),
          duration=2
      ),
      Task(
          print_it,  # action
          args=('world!',)
      )
  )
  t.action_stop = print_it
  t.args_stop = ('has been stopped',)
  
  t.start()
  sleep(1)
  print_it(
      'current state is {}, current activity is {}'.format(
          t.state,
          t.activity
      )
  )
  
  t.stop()
  print_it(
      'current state is {}, current activity is {}'.format(
          t.state,
          t.activity
      )
  )
  
  t.join()
  print_it(
      'current state is {}, current activity is {}'.format(
          t.state,
          t.activity
      )
  )
  
The Task object itself is the same as above. Here we do not use it as an
anonymous Task object. We reference it with variable **t**. The
reference allows us to get or set arguments. Setting arguments
modifies the Task. The reference is also used to stop and join the
Task object (method :py:meth:`~thread_task.Task.join` waits until the
Task's thread ends).

The attributes **action_stop** and **args_stop** are used to add our
own logic to the the stopping process. action_stop must be a callable
and a third attribute **kwargs_stop** allows to set keyword arguments
for action_stop. action_stop could execute some shutdown commands,
here it prints a message.

The output was:

.. code-block:: none

  14:43:50.321930 Thread-1  : hello,
  14:43:51.325888 MainThread: current state is STARTED, current activity is SLEEP
  14:43:51.326266 MainThread: current state is TO_STOP, current activity is SLEEP
  14:43:51.326526 Thread-1  : has been stopped
  14:43:51.327260 MainThread: current state is STOPPED, current activity is NONE
          
Method stop was called from thread ``MainThread``, when the root link
of Task t already had processed its action and waited until its
duration ended (its activity was **ACTIVITY_SLEEP**). Calling method
stop (also from thread ``MainThread``) changed the state of Task t
(but didn't stop it) and interrupted the sleeping. The stopping was
done by thread ``Thread-1``. This thread called action_stop, this
thread changed Task t's state from STATE_TO_STOP to STATE_STOPPED and
this thread was joined, when ``MainThread`` joined Task t.

When ``MainThread`` interacts with Task t, it uses Task's public
API. Here all the calling of Task t's methods and all the asking
for its attributes was done from thread ``MainThread``.


Long lasting actions
~~~~~~~~~~~~~~~~~~~~

We modify the program and let the action do the waiting. Less logic
in the Task object, more in the action.

.. code:: python3

  from thread_task import Task
  from datetime import datetime
  from time import sleep
  from threading import current_thread
  
  
  def print_it(txt: str):
      print(
          '{} {:10s}: {}'.format(
              datetime.now().strftime('%H:%M:%S.%f'),
              current_thread().name,
              txt
          )
      )
  
  
  def do_it():
      print_it('hello,')
      sleep(2)
      print_it('world!')
  
  
  t = Task(do_it)
  t.action_stop = print_it
  t.args_stop = ('has been stopped',)
  
  t.start()
  sleep(1)
  print_it(
      'current state is {}, current activity is {}'.format(
          t.state,
          t.activity
      )
  )
  
  t.stop()
  print_it(
      'current state is {}, current activity is {}'.format(
          t.state,
          t.activity
      )
  )
  
  t.join()
  print_it(
      'current state is {}, current activity is {}'.format(
          t.state,
          t.activity
      )
  )
  
The Task's single action lasts 2 sec. Let's look, what happened, this
was the output:

.. code-block:: none

  14:47:31.869959 Thread-1  : hello,
  14:47:32.870432 MainThread: current state is STARTED, current activity is BUSY
  14:47:32.870739 MainThread: current state is TO_STOP, current activity is BUSY
  14:47:33.872388 Thread-1  : world!
  14:47:33.873112 MainThread: current state is FINISHED, current activity is NONE

There was no stopping! When the Task realized, that its state had
changed from STATE_STARTED to STATE_TO_STOP, its single action had
already been done and there was no more waiting, no more chain link,
there was nothing more to do. Consequently, the state changed from
STATE_TO_STOP to **STATE_FINISHED**.

Long lasting actions prevent the stopping. Setting a duration is
different from sleeping in an action. If you want your Tasks stop
fast, code short actions and let the Task objects do the timing. When
a Tasks object sleeps, this can be interrupted, but not when an action
sleeps.


Continue
--------

Any Task object in state STATE_STOPPED can be continued. You can even
continue a Task in state STATE_TO_STOP, then calling
:py:meth:`~thread_task.Task.cont` will internally join the currently
running thread until the state changes to STATE_STOPPED. Calling
method cont from STATE_FINISHED is also accepted. In this case, it
silently does nothing.

We append the following code to the :ref:`stopping <stopping_example>` example:

.. code:: python3

  t.action_cont = print_it
  t.args_cont = ('has been continued',)
  
  sleep(4)
  t.cont()
  print_it(
      'current state is {}, current activity is {}'.format(
          t.state,
          t.activity
      )
  )
  
  t.join()
  print_it(
      'current state is {}, current activity is {}'.format(
          t.state,
          t.activity
      )
  )
  
**action_cont** and **args_cont** add some special logic to the
continuation process of a Task object (as you will have expected,
there is a third one, **kwargs_cont**). The program sleeps 4
sec. after the end of the stopping, then it starts the continuation
process by calling method cont. As above, we are interested in Task
t's state, then we wait until Task t has finished. At the end, we
again ask for the current state of Task t.

From the appended code, we got this additional lines of output:

.. code-block:: none

  14:43:55.332318 Thread-2  : has been continued
  14:43:55.332877 MainThread: current state is STARTED, current activity is SLEEP
  14:43:56.328461 Thread-2  : world!
  14:43:56.329064 MainThread: current state is FINISHED, current activity is NONE
  
Continuing indeed took place 4 sec. after the end of the stopping
process. Calling method cont created a new thread and named it
``Thread-2``.

As with stopping, the continuation process does not run under control
of the thread that called method cont. Task t *remembered*, there was
a rest of about 1 sec. of its root link's duration. Therefore it sleeps
this time, then it executes the action of the next chain link, which
prints ``world!``. After this, thread ``Thread-2`` ended with Task t in the
state **STATE_FINISHED**.

Again we try to be precise! Continuation also changes the state of the
Task in two steps. Method cont changes from STATE_STOPPED to
**STATE_TO_CONTINUE** and starts the new thread (here
``Thread-2``). This new thread controls the continuation process and
at the end of the continuation process, it changes from
STATE_TO_CONTINUE to STATE_STARTED. In our case, there was no chance
for thread ``MainThread`` to see state STATE_TO_CONTINUE, because
there was no gap for interruption. Modify the program and add a delay,
when calling method cont and you will see STATE_TO_CONTINUE.


Periodic actions
----------------

**Periodic** is a subclass of Task and allows to do things
periodically.  With **intervall**, it has one more positional
argument, which is the timespan between two executions of action. The
keyword argument **num** limits the number of
executions. Alternatively, the executions end, when action returns
``True``.

.. code:: python

  from thread_task import concat, Task, Periodic
  
  
  concat(
      # introduction
      Task(
          print,  # action
          args=('Help me to give an enthusiastic welcome to our speaker.',),
          duration=2
      ),
  
      # speech
      Periodic(
          2,  # intervall
          print,  # action
          args=('bla',),
          kwargs={'end': '', 'flush': True},
          num=3
      ),
      Task(
          print,  # action
          duration=1
      ),
  
      # reaction
      Task(
          print,  # action
          args=('Warm applause.',),
      )
  ).start()
  
This Task object consists of three parts, the introduction of the
speaker, the speech and the reaction of the audience. All together is
a chain with four links, a Task, a Periodic and two more Task
objects. The Periodic prints the string ``bla`` three times. Command
print is called with two keyword arguments, end and flush (see `print
<https://docs.python.org/3.8/library/functions.html#print>`_ for the
details). Between each call of print, there is a timespan of 2
sec. The next chain link calls print without any arguments, which
prints a newline. Setting durations for all three Task objects adds
timespans between the three parts and another timespan at the end.

The output is:

::

  Help me, to give an enthusiastic welcome to our speaker.
  blablabla
  Warm applause.
    
The whole program was executed in 8 sec. After the introduction, there
was a delay of 2 sec. until the speech began and the speech needed 4
sec. for its three syllables (with newline). Setting a duration for
the last Task of the speech made another delay before the audience
reacted, which needed one second.


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

Our Repeated object calls Accelerate's method step multiple times and
its sleeping duration depends on the return values of method step. Per
call, the delay becomes 1 sec. less.

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

  from thread_task import concat, Task, Periodic
  from threading import current_thread
  from datetime import datetime
  from time import sleep
  
  
  def print_it(txt: str):
      print(
          '{} {:10s}: {}'.format(
              datetime.now().strftime('%H:%M:%S.%f'),
              current_thread().name,
              txt
          )
      )
  
  
  data = {'switch': False}
  
  
  def set_data(data: dict, value: bool):
      data['switch'] = value
      print_it('set switch to ' + str(value))
  
  
  def get_data(data: dict) -> bool:
      value = data['switch']
      print_it('switch is ' + str(value))
      return value
  
  
  t_child = Task(
      set_data,
      args=(data, True),
      action_start=print_it,
      args_start=('*** t_child has been started',),
      action_stop=print_it,
      args_stop=('*** t_child has been stopped',),
      action_cont=print_it,
      args_cont=('*** t_child has been continued',),
      action_final=print_it,
      args_final=('*** t_child has finished',)
  )
  
  t_parent = concat(
      Task(
          t_child.start,
          args=(4.5,),
          action_start=print_it,
          args_start=('*** t_parent has been started',),
          action_stop=print_it,
          args_stop=('*** t_parent has been stopped',),
          action_cont=print_it,
          args_cont=('*** t_parent has been continued',),
          action_final=print_it,
          args_final=('*** t_parent has finished',),
      ),
      Periodic(
          1,
          get_data,
          args=(data,)
      )
  )
  
  t_parent.start()
  sleep(1.5)
  t_parent.stop()
  sleep(3.5)
  t_parent.cont()
        
This is a bit more complex than the other examples! We create 2 Task
objects **t_child**, and **t_parent** and t_parent becomes parent of
t_child when starting it.

**data** is a mutable data object. We use it for the communication
between t_child and t_parent. Function **set_data** writes values into
the data object, function **get_data** reads them.  In our case,
get_data is wrapped into a Periodic and will be called once per
second.  Function get_data returns the value it finds, returning
``True`` ends the Periodic. Function set_data is wrapped into t_child,
a Task object that sets the data object to ``True``.

t_parent starts t_child with a delay of 4.5 sec. We added some text
output to the Task objects, which help us to understand, what happens.

The output was:

::

  17:21:50.419311 Thread-1  : *** t_parent has been started
  17:21:50.421131 Thread-1  : switch is False
  17:21:51.421496 Thread-1  : switch is False
  17:21:51.921677 Thread-1  : *** t_parent has been stopped
  17:21:55.425590 Thread-3  : *** t_parent has been continued
  17:21:56.013249 Thread-3  : switch is False
  17:21:57.013476 Thread-3  : switch is False
  17:21:58.013728 Thread-3  : switch is False
  17:21:58.425146 Thread-4  : *** t_child has been started
  17:21:58.425511 Thread-4  : set switch to True
  17:21:58.425682 Thread-4  : *** t_child has finished
  17:21:59.013946 Thread-3  : switch is True
  17:21:59.014254 Thread-3  : *** t_parent has finished
      
The first row tells us, that starting Task t_parent created
``Thread-1``. The next two rows were printed by get_data and found the
data object in its initial state. As expected, there was a timespan of
1 sec. between these two printings.

We don't find a message about stopping and continuing Task t_child and
the message about its starting appears late. This is because of the
delay. Task t_child has to start 4.5 sec. after Task t_parent. And
what about ``Thread-2``, did it exist? Yes it did! With starting
t_child it was created, directly after ``Thread-1``, but after its
creation it had to wait and nothing else. When Task t was told to
stop, it directly called method stop of Task t_child and t_child
directly ended its waiting. Task t_child *knew*, that it had not yet
started and therefore it *knew*, there was nothing to stop.

3.5 sec. after its stopping, we continued t_parent and it continued
its child.  t_parent *remebered*, it was stopped in the middle of two
actions of its Periodic. This made it to wait 0.5 sec. until its next
call of get_data. t_child had a rest delay of 3 sec., which made it
answer this timespan after its continuation. Directly after this first
reaction, it called set_data, which changed the data object, then it
finished.

When get_data came to its next reading, it found the switch ``True``
and returned this value. This ended the Periodic and the final
printing came from the finishing process of Task t_parent.


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

- if there is an explicitly setted exc_handler: call it
- else if the current position is not the root link of a chain: call
  the exception handler of the root link.
- else if the current position is a child Task: call the exception
  handler of the parent Task's root link.
- else: call the default exception handler of the current position,
  which does stopping at the current position, then raises the
  exception.

In other words: It climbs up the hierarchy of the structure. If, on
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
