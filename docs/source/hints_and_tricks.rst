================
Hints and Tricks
================

After the first own experience, it may be helpfull to get some hints.

Wrapping a Task into a Task
---------------------------

Tasks lose most of their special behaviour, when they are appended to
other tasks. Sometimes this is a real pity, e.g. if there is special
logic for stopping and continuing. Subclasses with modified methods
start, stop or cont will also be destroyed if they become a chain link
of another task.

Wrapping a task into a default Task object is the solution of
choice. Then the default Task becomes the chain link and the modified
task becomes a child. If this child is started with *thread=False*, it
behaves like a chain link but keeps all its special behaviour.

.. code:: python3

  from thread_task import Task, concat
  
  
  class MyTask(Task):
      def start(self, *args, **kwargs):
          print('this is the special start behaviour of MyTask')
          super().start(*args, **kwargs)
  
  
  t = concat(
      Task(
          print,
          args=("I'm the root task",)
      ),
      Task(MyTask(
          print,
          args=("I'm of type Myclass",)
      )),
      Task(
          print,
          args=("I'm the last chain link",)
      )
  ).start()

It's syntactic sugar, that wrapping a Task into another Task is that
simple. The standard formulation of this would be:

.. code:: python3

  from thread_task import Task, concat
  
  
  class MyTask(Task):
      def start(self, *args, **kwargs):
          print('this is the special start behaviour of MyTask')
          super().start(*args, **kwargs)
  
  
  t = concat(
      Task(
          print,  # action
          args=("I'm the root task",)
      ),
      Task(
          MyTask(
              print,  # action
              args=("I'm of type MyTask",)
          ).start,
          kwargs={'thread': False}
      ),
      Task(
          print,
          args=("I'm the last chain link",)
      ),
  ).start()

Method *start* of the MyTask object becomes the standard Task's action
and starting it threadless prevents parallel execution, which makes it
behave like a chain link. Both variants write this output:

.. code-block:: none

  I'm the root task
  this is the special start behaviour of MyTask
  I'm of type MyTask
  I'm the last chain link


Prevent long lasting actions
----------------------------

We can also do the timing in an action instead of doing it in the
Task. Less logic in the Task object, more in the action. At the first
glance, both variants seem to be equivalent.

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
  
The Task's single action lasts 2 sec. This was the output:

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

Long lasting actions prevent or retard the stopping. Setting a
duration is different from sleeping in an action. If you want your
Tasks stop fast, code short actions and let the Task objects do the
timing. When a Tasks object sleeps, this can be interrupted, but not
when an action sleeps.


Never join a threadless child
-----------------------------

Joining a threadless child does not do the expeted. Joining targets
the thread and not the task, but the thread is the one of the parent!
Therefore joining a threadless child joins its parent.

.. code:: python3

  from thread_task import Task, concat
  from time import sleep
  
  
  def do_nothing(): pass
  
  
  t_child = Task(do_nothing, duration=1)
  t_parent = concat(
      Task(do_nothing, duration=1),
      Task(t_child),
      Task(do_nothing, duration=1)
  )
  t_parent.start()
  sleep(1.5)
  t_child.stop().join()
  print(t_parent.state)

The output comes after 2.5 sec and is:

.. code-block:: none

  FINISHED

Instead of waiting until the stopping of the child Task has finished,
the program waits until the parent Task has finished.

If you absolutely need to join a task, that has to be operated like a
threadless child, then replace:

.. code-block:: python3

      Task(t_child),

by:

.. code-block:: python3

      Task(t_child.start),
      Task(t_child.join),

This variant runs *t_child* in its own thread and allows to wait until
the stopping has finished. The joining realizes the same behaviour as
a threadless child.

We modify the program:

.. code:: python3

  from thread_task import Task, concat
  from time import sleep
  
  
  def do_nothing(): pass
  
  
  t_child = Task(do_nothing, duration=1)
  t_parent = concat(
      Task(do_nothing, duration=1),
      Task(t_child.start),
      Task(t_child.join),
      Task(do_nothing, duration=1)
  )
  t_parent.start()
  sleep(1.5)
  t_child.stop().join()
  print(t_parent.state)

and get the following output after 1.5 sec:

.. code-block:: none

  STARTED
