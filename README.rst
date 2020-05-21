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

Read
`thread-task.readthedocs.io <https://thread-task.readthedocs.io/en/latest/>`_
for more details.
