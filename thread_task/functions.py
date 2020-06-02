#!/usr/bin/env python3
'''organize and run thread tasks,
which can be stopped, continued and restarted.
'''


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
    if copy:
        return tasks[0]._copy().append(
            *tasks[1:],
            copy=True
        )
    else:
        return tasks[0].append(
            *tasks[1:],
            copy=False
        )
