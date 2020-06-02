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

.. autoclass:: thread_task.Task
   :members:

Periodic
~~~~~~~~

Periodic is a subclass of Task and allows to execute a callable
multiple times. It sets a fixed interval between two executions. 

.. autoclass:: thread_task.Periodic
   :members:

Repeated
~~~~~~~~

Repeated is a subclass of Task and allows to execute a callable
multiple times. It's the callable that sets the timing with its return
value.

.. autoclass:: thread_task.Repeated
   :members:

Sleep
~~~~~

Sleep is a subclass of Task and allows to place a timespan into a chain
of executables, which can be interrupted.

.. autoclass:: thread_task.Sleep
   :members:
