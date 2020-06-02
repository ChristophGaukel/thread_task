from thread_task import (
    Repeated,
    Task,
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


def print_it(ts: Timespan, str):
    print(
        '{:2.1f}:{}'.format(
            ts.timespan(1),
            str
        ),
        end=' '
    )


def print_it_long_lasting(ts, str):
    print(
        '{:2.1f}:{}'.format(
            ts.timespan(1),
            str
        ),
        end=' '
    )
    sleep(.1)
    return 0.1


class Accelerate:
    delay: int

    def __init__(self, ts: Timespan, delay):
        self.delay = delay + 0.1
        self.ts = ts

    def step(self):
        print_it(self.ts, 'hi')
        self.delay = round(self.delay - 0.1, 1)
        if self.delay >= 0:
            return self.delay
        else:
            return -1


def test_standard(capsys):

    ts = Timespan()
    acc = Accelerate(ts, 0.3)

    t = Repeated(
        acc.step,
        action_start=print_it,
        args_start=(ts, 'started'),
        action_stop=print_it,
        args_stop=(ts, 'stopped'),
        action_cont=print_it,
        args_cont=(ts, 'continued'),
        action_final=print_it,
        args_final=(ts, 'finished')
    ).start()
    sleep(.4)
    assert t.state == STATE_STARTED
    assert t.activity == ACTIVITY_SLEEP
    t.stop().join()
    assert t.state == STATE_STOPPED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == \
        '0.0:started 0.0:hi 0.3:hi 0.4:stopped '

    t.cont(.1).join()
    assert t.state == STATE_FINISHED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.out == \
        '0.5:continued 0.6:hi 0.7:hi 0.7:hi ' + \
        '0.7:finished '


def test_num(capsys):

    ts = Timespan()

    t = Repeated(
        print_it,
        args=(ts, 'hi'),
        num=2,
        duration=.1,
        action_start=print_it,
        args_start=(ts, 'started'),
        action_final=print_it,
        args_final=(ts, 'finished')
    ).start().join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == '0.0:started 0.0:hi 0.0:hi 0.1:finished '


def test_long_lasting(capsys):

    ts = Timespan()

    t = Repeated(
        print_it_long_lasting,
        args=(ts, 'hi'),
        num=2,
        duration=.3,
        action_start=print_it,
        args_start=(ts, 'started'),
        action_final=print_it,
        args_final=(ts, 'finished')
    ).start().join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == '0.0:started 0.0:hi 0.1:hi 0.3:finished '


def test_netto_time(capsys):

    ts = Timespan()

    t = Repeated(
        print_it_long_lasting,
        args=(ts, 'hi'),
        num=2,
        duration=.3,
        netto_time=True,
        action_start=print_it,
        args_start=(ts, 'started'),
        action_final=print_it,
        args_final=(ts, 'finished')
    ).start(thread=False)
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == '0.0:started 0.0:hi 0.2:hi 0.3:finished '


def test_threadless_child(capsys):

    ts = Timespan()

    t = Task(Repeated(
        print_it_long_lasting,
        args=(ts, 'hi'),
        num=2,
        duration=.3,
        netto_time=True,
        action_start=print_it,
        args_start=(ts, 'started'),
        action_final=print_it,
        args_final=(ts, 'finished')
    )).start(thread=False)
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == '0.0:started 0.0:hi 0.2:hi 0.3:finished '


def test_threadless_child_02(capsys):

    ts = Timespan()

    t = Repeated(
        Task(print_it_long_lasting, args=(ts, 'hi')),
        num=2,
        duration=.3,
        action_start=print_it,
        args_start=(ts, 'started'),
        action_final=print_it,
        args_final=(ts, 'finished')
    ).start(thread=False)
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == '0.0:started 0.0:hi 0.1:hi 0.3:finished '
