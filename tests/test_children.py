from thread_task import (
    concat,
    Task,
    Periodic,
    Repeated,
    STATE_TO_START,
    STATE_STARTED,
    STATE_TO_STOP,
    STATE_STOPPED,
    STATE_FINISHED,
    ACTIVITY_SLEEP,
    ACTIVITY_JOIN,
    ACTIVITY_NONE
)
from time import time, sleep


class Timespan(object):
    def __init__(self):
        self.init_time = time()

    def timespan(self, ndigits=0):
        return round(
            time() - self.init_time,
            ndigits
        )


def print_it(ts: Timespan, str):
    print(
        '{:2.1f}:{}'.format(
            ts.timespan(1),
            str
        ),
        end=' '
    )


def test_standard(capsys):

    ts = Timespan()

    t = concat(
        Task(
            Task(
                print_it,
                args=(ts, 'child'),
                duration=.4,
                action_start=print_it,
                args_start=(ts, 'child_started'),
                action_stop=print_it,
                args_stop=(ts, 'child_stopped'),
                action_cont=print_it,
                args_cont=(ts, 'child_continued'),
                action_final=print_it,
                args_final=(ts, 'child_finished')
            ).start,
            duration=.2,
            action_start=print_it,
            args_start=(ts, 'parent_started'),
            action_final=print_it,
            args_final=(ts, 'parent_finished')
        ),
        Task(
            print_it,
            args=(ts, 'parent'),
            duration=.1
        )
    ).start()
    sleep(.1)
    assert t.state == STATE_STARTED
    assert t.activity == ACTIVITY_SLEEP

    t.stop().join()
    assert t.state == STATE_STOPPED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == \
        '0.0:parent_started 0.0:child_started 0.0:child 0.1:child_stopped '

    t.cont(.1).join()
    assert t.state == STATE_FINISHED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == \
        '0.2:child_continued 0.3:parent ' + \
        '0.5:child_finished 0.5:parent_finished '


def test_periodic(capsys):

    ts = Timespan()

    t = Periodic(
        .1,
        Task(
            print_it,
            args=(ts, 'child'),
            action_start=print_it,
            args_start=(ts, 'child_started'),
            action_stop=print_it,
            args_stop=(ts, 'child_stopped'),
            action_cont=print_it,
            args_cont=(ts, 'child_continued'),
            action_final=print_it,
            args_final=(ts, 'child_finished')
        ).start,
        args=(.2,),
        num=2
    )
    t.action_start = print_it
    t.args_start = (ts, 'parent_started')
    t.action_stop = print_it
    t.args_stop = (ts, 'parent_stopped')
    t.action_cont = print_it
    t.args_cont = (ts, 'parent_continued')
    t.action_final = print_it
    t.args_final = (ts, 'parent_finished')

    t.start()
    sleep(.3)
    assert t.state == STATE_STARTED
    assert t.activity == ACTIVITY_JOIN
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == \
        '0.0:parent_started 0.2:child_started 0.2:child ' + \
        '0.2:child_finished '

    t.stop().join()
    assert t.state == STATE_STOPPED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == \
        '0.3:parent_stopped '

    sleep(.1)
    t.cont().join()
    assert t.state == STATE_FINISHED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == \
        '0.4:parent_continued 0.5:child_started 0.5:child ' + \
        '0.5:child_finished 0.5:parent_finished '


def test_repeated(capsys):

    ts = Timespan()

    t = Repeated(
        Task(
            print_it,
            duration=.2,
            args=(ts, 'child'),
            action_start=print_it,
            args_start=(ts, 'child_started'),
            action_stop=print_it,
            args_stop=(ts, 'child_stopped'),
            action_cont=print_it,
            args_cont=(ts, 'child_continued'),
            action_final=print_it,
            args_final=(ts, 'child_finished')
        ).start,
        num=2
    )
    t.action_start = print_it
    t.args_start = (ts, 'parent_started')
    t.action_stop = print_it
    t.args_stop = (ts, 'parent_stopped')
    t.action_cont = print_it
    t.args_cont = (ts, 'parent_continued')
    t.action_final = print_it
    t.args_final = (ts, 'parent_finished')

    t.start()
    sleep(.3)
    assert t.state == STATE_STARTED
    assert t.activity == ACTIVITY_JOIN

    t.stop().join()
    assert t.state == STATE_STOPPED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == \
        '0.0:parent_started 0.0:child_started 0.0:child ' + \
        '0.2:child_finished 0.2:child_started 0.2:child ' + \
        '0.3:child_stopped 0.3:parent_stopped '

    sleep(.1)
    t.cont().join()
    assert t.state == STATE_FINISHED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == \
        '0.4:parent_continued 0.4:child_continued ' + \
        '0.5:child_finished 0.5:parent_finished '


def test_join_01(capsys):
    '''joining a task, that is no child'''

    ts = Timespan()

    t1 = Task(
        print_it,
        duration=.3,
        args=(ts, 't1'),
        action_start=print_it,
        args_start=(ts, 't1_started'),
        action_stop=print_it,
        args_stop=(ts, 't1_stopped'),
        action_cont=print_it,
        args_cont=(ts, 't1_continued'),
        action_final=print_it,
        args_final=(ts, 't1_finished')
    )
    t2 = concat(
        Task(
            print_it,
            args=(ts, 't2'),
            action_start=print_it,
            args_start=(ts, 't2_started'),
            action_stop=print_it,
            args_stop=(ts, 't2_stopped'),
            action_cont=print_it,
            args_cont=(ts, 't2_continued'),
            action_final=print_it,
            args_final=(ts, 't2_finished')
        ),
        Task(t1.join)
    )
    t1.start()
    t2.start(.1)
    sleep(.001)
    assert t1.state == STATE_STARTED
    assert t1.activity == ACTIVITY_SLEEP
    assert t2.state == STATE_TO_START
    assert t2.activity == ACTIVITY_SLEEP
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.0:t1_started 0.0:t1 '

    t2.stop().join()
    assert t1.state == STATE_STARTED
    assert t2.state == STATE_STOPPED

    t2.cont()
    sleep(.1)
    assert t1.state == STATE_STARTED
    assert t2.state == STATE_STARTED
    assert t2.activity == ACTIVITY_JOIN
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.1:t2_started 0.1:t2 '

    t2.stop()
    sleep(.01)
    assert t1.state == STATE_STARTED
    assert t2.state == STATE_TO_STOP

    t2.join()
    assert t1.state == STATE_FINISHED
    assert t2.state == STATE_FINISHED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.3:t1_finished 0.3:t2_finished '


def test_join_02(capsys):
    '''joining a task, that is a child'''

    ts = Timespan()

    t1 = Task(
        print_it,
        args=(ts, 't1'),
        duration=.2,
        action_start=print_it,
        args_start=(ts, 't1_started'),
        action_stop=print_it,
        args_stop=(ts, 't1_stopped'),
        action_cont=print_it,
        args_cont=(ts, 't1_continued'),
        action_final=print_it,
        args_final=(ts, 't1_finished')
    )
    t2 = concat(
        Task(
            t1.start,
            duration=.1,
            action_start=print_it,
            args_start=(ts, 't2_started'),
            action_stop=print_it,
            args_stop=(ts, 't2_stopped'),
            action_cont=print_it,
            args_cont=(ts, 't2_continued'),
            action_final=print_it,
            args_final=(ts, 't2_finished')
        ),
        Task(
            print_it,
            args=(ts, 't2')
        ),
        Task(t1.join)
    )
    t2.start()
    sleep(.001)
    assert t1.state == STATE_STARTED
    assert t1.activity == ACTIVITY_SLEEP
    assert t2.state == STATE_STARTED
    assert t2.activity == ACTIVITY_SLEEP
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.0:t2_started 0.0:t1_started 0.0:t1 '

    t2.stop().join()
    assert t1.state == STATE_STOPPED
    assert t2.state == STATE_STOPPED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.0:t1_stopped 0.0:t2_stopped '

    t2.cont()
    sleep(.1)
    assert t1.state == STATE_STARTED
    assert t2.state == STATE_STARTED
    assert t2.activity == ACTIVITY_JOIN
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.0:t2_continued 0.0:t1_continued 0.1:t2 '

    t2.stop().join()
    assert t1.state == STATE_STOPPED
    assert t2.state == STATE_STOPPED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.1:t1_stopped 0.1:t2_stopped '

    t2.cont()
    sleep(.001)
    assert t1.state == STATE_STARTED
    assert t1.activity == ACTIVITY_SLEEP
    assert t2.state == STATE_STARTED
    assert t2.activity == ACTIVITY_JOIN
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.1:t2_continued 0.1:t1_continued '

    t2.join()
    assert t1.state == STATE_FINISHED
    assert t2.state == STATE_FINISHED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.2:t1_finished 0.2:t2_finished '


def test_cont(capsys):
    '''stopping and continuing a child'''

    ts = Timespan()

    t1 = Task(
        print_it,
        args=(ts, 't1'),
        duration=.2
    )
    t1.action_start = print_it
    t1.args_start = (ts, 't1_started')
    t1.action_stop = print_it
    t1.args_stop = (ts, 't1_stopped')
    t1.action_cont = print_it
    t1.args_cont = (ts, 't1_continued')
    t1.action_final = print_it
    t1.args_final = (ts, 't1_finished')

    t2 = concat(
        Task(
            t1.start,
            duration=.1
        ),
        Task(
            t1.stop,
            duration=.1
        ),
        Task(
            t1.cont
        )
    )
    t2.action_start = print_it
    t2.args_start = (ts, 't2_started')
    t2.action_stop = print_it
    t2.args_stop = (ts, 't2_stopped')
    t2.action_cont = print_it
    t2.args_cont = (ts, 't2_continued')
    t2.action_final = print_it
    t2.args_final = (ts, 't2_finished')

    t2.start().join()
    assert t1.state == STATE_FINISHED
    assert t1.activity == ACTIVITY_NONE
    assert t2.state == STATE_FINISHED
    assert t2.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == \
        '0.0:t2_started 0.0:t1_started 0.0:t1 ' + \
        '0.1:t1_stopped 0.2:t1_continued 0.3:t1_finished 0.3:t2_finished '

    t2.start()
    sleep(.001)
    assert t1.state == STATE_STARTED
    assert t1.activity == ACTIVITY_SLEEP
    assert t2.state == STATE_STARTED
    assert t2.activity == ACTIVITY_SLEEP
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.3:t2_started 0.3:t1_started 0.3:t1 '

    t2.stop().join()
    assert t1.state == STATE_STOPPED
    assert t1.activity == ACTIVITY_NONE
    assert t2.state == STATE_STOPPED
    assert t2.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.3:t1_stopped 0.3:t2_stopped '

    sleep(.1)

    t2.cont()
    sleep(.001)
    assert t1.state == STATE_STARTED
    assert t1.activity == ACTIVITY_SLEEP
    assert t2.state == STATE_STARTED
    assert t2.activity == ACTIVITY_SLEEP
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.4:t2_continued 0.4:t1_continued '

    sleep(.1)
    assert t1.state == STATE_STOPPED
    assert t1.activity == ACTIVITY_NONE
    assert t2.state == STATE_STARTED
    assert t2.activity == ACTIVITY_SLEEP
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.5:t1_stopped '

    sleep(.1)
    assert t1.state == STATE_STARTED
    assert t1.activity == ACTIVITY_SLEEP
    assert t2.state == STATE_STARTED
    assert t2.activity == ACTIVITY_JOIN
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.6:t1_continued '

    t2.stop().join()
    assert t1.state == STATE_STOPPED
    assert t1.activity == ACTIVITY_NONE
    assert t2.state == STATE_STOPPED
    assert t2.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.6:t1_stopped 0.6:t2_stopped '

    sleep(.1)

    t2.cont()
    sleep(.001)
    assert t1.state == STATE_STARTED
    assert t2.state == STATE_STARTED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.7:t2_continued 0.7:t1_continued '

    t2.join()
    assert t1.state == STATE_FINISHED
    assert t2.state == STATE_FINISHED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.8:t1_finished 0.8:t2_finished '
