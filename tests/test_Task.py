from thread_task import (
    concat,
    Task,
    STATE_TO_START,
    STATE_STARTED,
    STATE_STOPPED,
    STATE_FINISHED,
    ACTIVITY_SLEEP,
    ACTIVITY_NONE
)
from time import sleep, time


def test_standard(capsys):
    t = Task(
        print,
        args=('hello, world!',),
        kwargs={'end': ''}
    ).start()
    t.join()
    assert t.state == STATE_FINISHED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == 'hello, world!'


def test_action_start(capsys):
    # without delay
    t = Task(
        print,
        args=('hello, world!',),
        kwargs={'end': ''},
        action_start=print,
        args_start=('started',),
        kwargs_start={'end': ' '},
        action_stop=print,
        args_stop=(' stopped',),
        kwargs_stop={'end': ''}
    ).start()
    t.join()
    assert t.state == STATE_FINISHED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == 'started hello, world!'

    # with delay
    t.start(.1)
    sleep(.05)
    assert t.state == STATE_TO_START
    t.stop().join()
    assert t.state == STATE_STOPPED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == ''
    t.cont().join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == 'started hello, world!'


def test_action_final(capsys):
    t = Task(
        print,
        args=('hello, world!',),
        kwargs={'end': ''},
        action_final=print,
        args_final=(' finished',),
        kwargs_final={'end': ''}
    ).start()
    t.join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == 'hello, world! finished'


def test_action_stop(capsys):
    t = Task(
        print,
        args=('hello, world!',),
        kwargs={'end': ''},
        duration=.1,
        action_stop=print,
        args_stop=(' stopped',),
        kwargs_stop={'end': ''},
        action_final=print,
        args_final=(' finished',),
        kwargs_final={'end': ''}
    ).start()
    sleep(.05)
    t.stop()
    t.join()
    captured = capsys.readouterr()
    assert t.state == STATE_STOPPED
    assert captured.err == ''
    assert captured.out == 'hello, world! stopped'


def test_action_cont(capsys):
    # with duration
    t = Task(
        print,
        args=('hello, world!',),
        kwargs={'end': ''},
        duration=.1,
        action_stop=print,
        args_stop=(' stopped',),
        kwargs_stop={'end': ''},
        action_cont=print,
        args_cont=(' continued',),
        kwargs_cont={'end': ''},
        action_final=print,
        args_final=(' finished',),
        kwargs_final={'end': ''}
    )
    t.start().stop()
    t.join()
    assert t.state == STATE_STOPPED
    t.cont().join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == 'hello, world! stopped continued finished'

    # without duration
    t = Task(
        print,
        args=('hello, world!',),
        kwargs={'end': ''},
        action_stop=print,
        args_stop=(' stopped',),
        kwargs_stop={'end': ''},
        action_cont=print,
        args_cont=(' continued',),
        kwargs_cont={'end': ''},
        action_final=print,
        args_final=(' finished',),
        kwargs_final={'end': ''}
    )
    t.start().stop()
    t.join()
    assert t.state == STATE_FINISHED
    t.cont().join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == 'hello, world! finished'


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


def test_timing_00(capsys):

    ts = Timespan()

    t = Task(
        print_it,
        args=(ts, 'hello'),
        action_start=print_it,
        args_start=(ts, 'started'),
        action_final=print_it,
        args_final=(ts, 'finished'),
        duration=.1
    ).start(.1).join()
    captured = capsys.readouterr()
    assert t.state == STATE_FINISHED
    assert captured.err == ''
    assert captured.out == '0.1:started 0.1:hello 0.2:finished '


def test_timing_01(capsys):
    '''stopping in state TO_START (in delay, before started)'''

    ts = Timespan()

    t = Task(
        print_it,
        args=(ts, 'hello'),
        action_start=print_it,
        args_start=(ts, 'started'),
        action_final=print_it,
        args_final=(ts, 'finished'),
        duration=.1
    )
    t.start(.2)
    sleep(.1)
    assert t.state == STATE_TO_START

    t.stop().join()
    assert t.state == STATE_STOPPED

    sleep(.1)
    t.cont().join()
    assert t.state == STATE_FINISHED
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.3:started 0.3:hello 0.4:finished '


def test_timing_02(capsys):
    '''stopping in state STARTED after action'''

    ts = Timespan()

    t = Task(
        print_it,
        args=(ts, 'hello'),
        action_start=print_it,
        args_start=(ts, 'started'),
        action_stop=print_it,
        args_stop=(ts, 'stopped'),
        action_cont=print_it,
        args_cont=(ts, 'continued'),
        action_final=print_it,
        args_final=(ts, 'finished'),
        duration=.2
    )
    t.start(.1)
    sleep(.2)
    assert t.state == STATE_STARTED
    assert t.activity == ACTIVITY_SLEEP

    t.stop().join()
    assert t.state == STATE_STOPPED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.1:started 0.1:hello 0.2:stopped '

    sleep(.1)
    t.cont().join()
    assert t.state == STATE_FINISHED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.3:continued 0.4:finished '


def test_timing_03(capsys):
    '''stopping in state STARTED after first action (chain)'''

    ts = Timespan()

    t = concat(
        Task(
            print_it,
            args=(ts, 'hi_1'),
            action_start=print_it,
            args_start=(ts, 'started'),
            action_stop=print_it,
            args_stop=(ts, 'stopped'),
            action_cont=print_it,
            args_cont=(ts, 'continued'),
            action_final=print_it,
            args_final=(ts, 'finished'),
            duration=.2
        ),
        Task(
            print_it,
            args=(ts, 'hi_2'),
            duration=.1
        )
    )
    t.start(.1)
    sleep(.05)
    assert t.state == STATE_TO_START
    assert t.activity == ACTIVITY_SLEEP

    sleep(.1)
    assert t.state == STATE_STARTED
    assert t.activity == ACTIVITY_SLEEP
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.1:started 0.1:hi_1 '

    sleep(.05)
    t.stop().join()
    assert t.state == STATE_STOPPED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.2:stopped '

    sleep(.1)
    t.cont().join()
    assert t.state == STATE_FINISHED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == '0.3:continued 0.4:hi_2 0.5:finished '


def test_add(capsys):
    '''overloaded add operator'''
    t1 = Task(print, args=('hello,',))
    t2 = Task(print, args=('world!',))
    t = t1 + t2
    t.start(thread=False)
    assert t.state == STATE_FINISHED
    assert t.activity == ACTIVITY_NONE
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == 'hello,\nworld!\n'
