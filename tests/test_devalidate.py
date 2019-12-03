import synpp
from pytest import raises

def test_devalidate_by_config(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    result = synpp.run([{
        "descriptor": "tests.fixtures.sum_stages"
    }], config = { "a": 1, "b": 1 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.sum_config" in result["stale"]
    assert "tests.fixtures.sum_stages" in result["stale"]
    assert "tests.fixtures.sum_params__e26a0ad06d9e0ed951e15f5e689b75fe" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.sum_stages"
    }], config = { "a": 1, "b": 1 }, working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.sum_config" in result["stale"]
    assert "tests.fixtures.sum_stages" in result["stale"]
    assert not "tests.fixtures.sum_params__e26a0ad06d9e0ed951e15f5e689b75fe" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.sum_stages"
    }], config = { "a": 2, "b": 2 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.sum_config" in result["stale"]
    assert "tests.fixtures.sum_stages" in result["stale"]
    assert not "tests.fixtures.sum_params__e26a0ad06d9e0ed951e15f5e689b75fe" in result["stale"]

def test_devalidate_by_parent(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    result = synpp.run([{
        "descriptor": "tests.fixtures.after_sum_stages"
    }], config = { "a": 1, "b": 1 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.sum_config" in result["stale"]
    assert "tests.fixtures.sum_stages" in result["stale"]
    assert "tests.fixtures.sum_params__e26a0ad06d9e0ed951e15f5e689b75fe" in result["stale"]
    assert "tests.fixtures.after_sum_stages" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.after_sum_stages"
    }], config = { "a": 1, "b": 1 }, working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.sum_config" in result["stale"]
    assert not "tests.fixtures.sum_stages" in result["stale"]
    assert not "tests.fixtures.sum_params__e26a0ad06d9e0ed951e15f5e689b75fe" in result["stale"]
    assert "tests.fixtures.after_sum_stages" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.sum_config"
    }], config = { "a": 1, "b": 1 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.sum_config" in result["stale"]
    assert not "tests.fixtures.sum_stages" in result["stale"]
    assert not "tests.fixtures.sum_params__e26a0ad06d9e0ed951e15f5e689b75fe" in result["stale"]
    assert not "tests.fixtures.after_sum_stages" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.after_sum_stages"
    }], config = { "a": 1, "b": 1 }, working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.sum_config" in result["stale"]
    assert "tests.fixtures.sum_stages" in result["stale"]
    assert not "tests.fixtures.sum_params__e26a0ad06d9e0ed951e15f5e689b75fe" in result["stale"]
    assert "tests.fixtures.after_sum_stages" in result["stale"]


def test_devalidate_descendants(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    result = synpp.run([{
        "descriptor": "tests.fixtures.after_sum_stages"
    }], config = { "a": 1, "b": 1 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.sum_config" in result["stale"]
    assert "tests.fixtures.sum_stages" in result["stale"]
    assert "tests.fixtures.sum_params__e26a0ad06d9e0ed951e15f5e689b75fe" in result["stale"]
    assert "tests.fixtures.after_sum_stages" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.after_sum_stages"
    }, {
        "descriptor": "tests.fixtures.sum_config"
    }], config = { "a": 1, "b": 1 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.sum_config" in result["stale"]
    assert "tests.fixtures.sum_stages" in result["stale"]
    assert not "tests.fixtures.sum_params__e26a0ad06d9e0ed951e15f5e689b75fe" in result["stale"]
    assert "tests.fixtures.after_sum_stages" in result["stale"]
