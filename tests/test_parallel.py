from synpp.parallel import ParallelMasterContext, ParalelMockMasterContext
import synpp

def sum_up(context, argument):
    return context.data("xyz") + context.config("uvw") + context.config("hij") + argument

def test_parallel():
    data = { "xyz": 1200 }
    config = { "uvw": 40, "hij": 5 }

    arguments = [1000000, 2000000, 3000000]

    with ParallelMasterContext(data, config, 3, None, None) as parallel:
        result = parallel.map(sum_up, arguments)

    assert result == [1001245, 2001245, 3001245]

    with ParallelMasterContext(data, config, 3, None, None) as parallel:
        result = parallel.map_async(sum_up, arguments).get()

    assert result == [1001245, 2001245, 3001245]

    with ParallelMasterContext(data, config, 3, None, None) as parallel:
        result = list(parallel.imap(sum_up, arguments))

    assert result == [1001245, 2001245, 3001245]

    with ParallelMasterContext(data, config, 3, None, None) as parallel:
        result = list(parallel.imap_unordered(sum_up, arguments))

    assert 1001245 in result
    assert 2001245 in result
    assert 3001245 in result


def test_mock():
    data = { "xyz": 1200 }
    config = { "uvw": 40, "hij": 5 }

    arguments = [1000000, 2000000, 3000000]

    with ParalelMockMasterContext(data, config, 3) as parallel:
        result = parallel.map(sum_up, arguments)

    assert result == [1001245, 2001245, 3001245]

    #with ParalelMockMasterContext(data, config, 3) as parallel:
    #    result = parallel.map_async(sum_up, arguments).get()

    #assert result == [1001245, 2001245, 3001245]

    with ParalelMockMasterContext(data, config, 3) as parallel:
        result = list(parallel.imap(sum_up, arguments))

    assert result == [1001245, 2001245, 3001245]

    with ParalelMockMasterContext(data, config, 3) as parallel:
        result = list(parallel.imap_unordered(sum_up, arguments))

    assert 1001245 in result
    assert 2001245 in result
    assert 3001245 in result

def test_parallel_stage():
    result = synpp.run([
        { "descriptor": "tests.fixtures.parallel_stage" }
    ])[0]

    assert result == [1321, 2321, 3321, 4321, 5321]
