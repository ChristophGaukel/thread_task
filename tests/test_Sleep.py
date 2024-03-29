from thread_task import (
    Sleep,
    Task,
    concat,
    STATE_STARTED,
    STATE_STOPPED,
    STATE_FINISHED,
    ACTIVITY_SLEEP,
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


def print_it(ts, str):
    print(
        '{:2.1f}:{}'.format(
            ts.timespan(1),
            str
        ),
        end=' '
    )


def test_standard(capsys):

    ts = Timespan()

    t = Task(
        print_it,
        args=(ts, 'started')
    ) + Sleep(
        .1
    ) + Task(
        print_it,
        args=(ts, 'finished')
    )
    t.start().join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == '0.0:started 0.1:finished '


def test_concat(capsys):

    ts = Timespan()

    t = concat(
        Task(
            print_it,
            args=(ts, 'started')
        ),
        Sleep(
            .1
        ),
        Task(
            print_it,
            args=(ts, 'hello')
        ),
        Sleep(.1),
        Task(
            print_it,
            args=(ts, 'world')
        ),
        Task(
            print_it,
            args=(ts, 'finished')
        )
    ).start(.1).join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == '0.1:started 0.2:hello 0.3:world 0.3:finished '


def test_cont(capsys):

    ts = Timespan()

    t = concat(
        Task(
                print_it,
                args=(ts, 'started')
        ),
        Sleep(
                .2,
                action_stop=print_it,
                args_stop=(ts, '1st sleep stopped'),
                action_cont=print_it,
                args_cont=(ts, '1st sleep continued')
        ),
        Task(
                print_it,
                args=(ts, 'hello'),
                action_stop=print_it,
                args_stop=(ts, 'hello stopped'),
                action_cont=print_it,
                args_cont=(ts, 'hello continued')
        ),
        Sleep(
                .2,
                action_stop=print_it,
                args_stop=(ts, '2nd sleep stopped'),
                action_cont=print_it,
                args_cont=(ts, '2nd sleep continued')
        ),
        Task(
                print_it,
                args=(ts, 'world'),
                action_stop=print_it,
                args_stop=(ts, 'world stopped'),
                action_cont=print_it,
                args_cont=(ts, 'world continued')
        ),
        Task(
                print_it,
                args=(ts, 'finished')
        )
    ).start(.1).stop().join()
    assert t.state == STATE_STOPPED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == ''

    t.cont(.1)
    sleep(.2)
    assert t.state == STATE_STARTED
    assert t.activity == ACTIVITY_SLEEP
    t.stop().join()
    assert t.state == STATE_STOPPED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.1:started 0.2:1st sleep stopped '

    # restart from STATE_STOPPED
    t.start()
    sleep(.201)
    assert t.state == STATE_STARTED
    assert t.activity == ACTIVITY_SLEEP
    t.stop().join()
    assert t.state == STATE_STOPPED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.2:started 0.4:hello 0.4:2nd sleep stopped '

    t.cont().join()
    assert t.state == STATE_FINISHED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.4:2nd sleep continued 0.6:world 0.6:finished '

    # restart from STATE_FINISHED
    t.start().join()
    assert t.state == STATE_FINISHED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.6:started 0.8:hello 1.0:world 1.0:finished '
