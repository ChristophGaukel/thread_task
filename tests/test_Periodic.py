from thread_task import (
    Periodic,
    Task,
    STATE_FINISHED
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


def print_it_long_lasting(ts, str):
    print(
        '{:2.1f}:{}'.format(
            ts.timespan(1),
            str
        ),
        end=' '
    )
    sleep(.1)


def test_standard(capsys):

    ts = Timespan()

    t = Task(
        print_it,
        args=(ts, 'started')
    ) + Periodic(
        .1,
        print_it,
        args=(ts, 'hi'),
        num=3,
    ) + Task(
        print_it,
        args=(ts, 'finished')
    )
    t.start().join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == \
        '0.0:started 0.0:hi 0.1:hi 0.2:hi 0.2:finished '


def test_threadless(capsys):

    ts = Timespan()

    t = Task(
        print_it,
        args=(ts, 'started')
    ) + Periodic(
        .1,
        print_it,
        args=(ts, 'hi'),
        num=3
    ) + Task(
        print_it,
        args=(ts, 'finished')
    )
    t.start(thread=False)
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == \
        '0.0:started 0.0:hi 0.1:hi 0.2:hi 0.2:finished '


def test_threadless_child(capsys):

    ts = Timespan()

    t = Task(
        print_it,
        args=(ts, 'started')
    ) + Periodic(
        .1,
        Task(print_it, args=(ts, 'hi')),
        num=3
    ) + Task(
        print_it,
        args=(ts, 'finished')
    )
    t.start(thread=False)
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == \
        '0.0:started 0.0:hi 0.1:hi 0.2:hi 0.2:finished '


def test_long_lasting(capsys):

    ts = Timespan()

    t = Task(
        print_it,
        args=(ts, 'started')
    ) + Periodic(
        .1,
        print_it_long_lasting,
        args=(ts, 'hi'),
        num=3
    ) + Task(
        print_it,
        args=(ts, 'finished')
    )
    t.start().join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == \
        '0.0:started 0.0:hi 0.1:hi 0.2:hi 0.3:finished '


def test_netto_time(capsys):

    ts = Timespan()

    t = Task(
        print_it,
        args=(ts, 'started')
    ) + Periodic(
        .1,
        print_it_long_lasting,
        args=(ts, 'hi'),
        num=3,
        netto_time=True
    ) + Task(
        print_it,
        args=(ts, 'finished')
    )
    t.start().join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == \
        '0.0:started 0.0:hi 0.2:hi 0.4:hi 0.5:finished '
