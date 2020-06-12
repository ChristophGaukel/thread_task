from thread_task import (
    Task,
    Sleep,
    Periodic,
    Repeated
)
import pytest


def test_unknown_argument():
    with pytest.raises(AssertionError) as exc:
        Task(
            print,
            args=('hello, world',),
            unknown='something'
        )
    assert exc.value.args[0] == \
        "unknown keyword arguments: dict_keys(['unknown'])"


def test_action():
    with pytest.raises(AssertionError) as exc:
        Task(
            'txt',
        )
    assert exc.value.args[0] == \
        "action needs to be a callable or a task"


def test_num(capsys):
    '''argument num only for Repeated and Periodic'''
    with pytest.raises(AssertionError) as exc:
        Task(
            print,
            num=2
        )
    assert exc.value.args[0] == \
        'no num for Task objects'

    with pytest.raises(AssertionError) as exc:
        Sleep(
            print,
            num=2
        )
    assert exc.value.args[0] == \
        'no num for Sleep objects'

    Periodic(
        1,
        print,
        num=2
    )
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == ''

    Repeated(
        print,
        num=2
    )
    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out == ''


def test_duration():
    '''no argument duration for Sleep'''
    with pytest.raises(AssertionError) as exc:
        Sleep(
            2,
            duration=2
        )
    assert exc.value.args[0] == \
        'no duration for Sleep objects'


def test_netto_time():
    '''no argument netto_time for Sleep and Task'''
    with pytest.raises(AssertionError) as exc:
        Sleep(
            2,
            netto_time=True
        )
    assert exc.value.args[0] == \
        'no netto_time for Sleep objects'

    with pytest.raises(AssertionError) as exc:
        Task(
            print,
            netto_time=True
        )
    assert exc.value.args[0] == \
        'no netto_time for Task objects'
