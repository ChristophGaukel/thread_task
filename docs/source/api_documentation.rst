=================
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

Wrapping callables into Task objects is the base step for
multithreading with chains of Tasks or trees of Tasks, which can be
stopped or continued.

Instead of a callable, you can also wrap a thread_task (Task, Periodic
or Repeated) into a Task. It will be executed as a threadless child.

.. autoclass:: thread_task.Task
   :members:

Periodic
~~~~~~~~

Periodic allows to execute a callable multiple times. It sets a fixed
interval between two executions.

Instead of a callable, you can also wrap a thread_task (Task, Periodic
or Repeated) into a Periodic. It will be executed as a threadless
child.

.. autoclass:: thread_task.Periodic
   :members:

Repeated
~~~~~~~~

Repeated is the baseclass of Task and Periodic. It allows to execute a
callable multiple times. In case of Periodic, the callable sets the
timing with its return value.

Instead of a callable, you can also wrap a thread_task (Task, Periodic
or Repeated) into a Repeated. It will be executed as a threadless
child.

.. autoclass:: thread_task.Repeated
   :members:

Sleep
~~~~~

Sleep is a subclass of Task and allows to place a timespan into a chain
of executables, which can be interrupted.

.. autoclass:: thread_task.Sleep
   :members:
