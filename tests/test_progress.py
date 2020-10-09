from synpp.progress import ProgressContext
import synpp
import time

def test_progress():
    with ProgressContext(total = 1000, label = "ABC") as progress:
        for i in range(1000):
            progress.update()

    with ProgressContext(label = "ABC") as progress:
        for i in range(1000):
            progress.update()

    with ProgressContext() as progress:
        for i in range(1000):
            progress.update()

def test_iterable():
    iterable = list(range(1000))
    result = [item for item in ProgressContext(iterable)]
    assert result == iterable

def test_generator():
    def gen():
        i = 0

        while i < 1000:
            yield i
            i += 1

    result = [item for item in ProgressContext(gen())]
    assert result == list(range(1000))

def test_progress_stage():
    synpp.run([
        { "descriptor": "tests.fixtures.progress_stage" }
    ])

def test_parallel_progress_stage():
    synpp.run([
        { "descriptor": "tests.fixtures.parallel_progress_stage" }
    ])
