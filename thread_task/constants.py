'''constants of package thread_task'''

STATE_INIT = 'INIT'
STATE_TO_START = 'TO_START'
STATE_STARTED = 'STARTED'
STATE_TO_STOP = 'TO_STOP'
STATE_STOPPED = 'STOPPED'
STATE_TO_CONTINUE = 'TO_CONTINUE'
STATE_FINISHED = 'FINISHED'

ACTIVITY_NONE = 'NONE'
ACTIVITY_BUSY = 'BUSY'
ACTIVITY_SLEEP = 'SLEEP'
ACTIVITY_JOIN = 'JOIN'

__all__ = [
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
]
