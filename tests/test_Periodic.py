from thread_task import (
    Periodic,
    STATE_FINISHED
)
from time import time


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
        '{:3.2f}:{}'.format(
            ts.timespan(2),
            str
        ),
        end=' '
    )


def test_standard(capsys):

    ts = Timespan()

    t = Periodic(
        .01,
        print_it,
        args=(ts, 'hi'),
        num=3,
        action_start=print_it,
        args_start=(ts, 'started'),
        action_final=print_it,
        args_final=(ts, 'finished'),
    ).start().join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == \
        '0.00:started 0.00:hi 0.01:hi 0.02:hi 0.02:finished '
