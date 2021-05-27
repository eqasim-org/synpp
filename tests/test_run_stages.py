import synpp
from pytest import raises

def test_sum_params():
    result = synpp.run([{
        "descriptor": "tests.fixtures.sum_config",
        "config": { "a": 5, "b": 9 }
    }])
    assert result[0] == 14

def test_sum_config():
    result = synpp.run([{
        "descriptor": "tests.fixtures.sum_config"
    }], config =  { "a": 5, "b": 11 })
    assert result[0] == 16

def test_cycle():
    with raises(synpp.PipelineError):
        synpp.run([{
            "descriptor": "tests.fixtures.cycle_stage_a"
        }])

def test_sum_stages_in_memory():
    result = synpp.run([{
        "descriptor": "tests.fixtures.sum_stages"
    }], config = { "a": 5, "b": 11 })

    assert result[0] == 11 + 16 + 10

def test_sum_stages_with_files(tmpdir):
    result = synpp.run([{
        "descriptor": "tests.fixtures.sum_stages"
    }], config = { "a": 5, "b": 11 }, working_directory = tmpdir.mkdir("sub"))

    assert result[0] == 11 + 16 + 10

def test_recursive(tmpdir):
    result = synpp.run([{
        "descriptor": "tests.fixtures.recursive",
        "config": { "a": 5 }
    }], working_directory = tmpdir.mkdir("sub"))

    assert result[0] == 15

def test_cache_path(tmpdir):
    result = synpp.run([{
        "descriptor": "tests.fixtures.cache_path_read"
    }], working_directory = tmpdir.mkdir("sub"))

    assert result[0] == "abc_uvw"

def test_rerun_required(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    results1 = synpp.run([{
        "descriptor": "tests.fixtures.sum_config",
        "config": {"a": 5, "b": 9}
    }], working_directory=working_directory)
    results2 = synpp.run([{
        "descriptor": "tests.fixtures.sum_config",
        "config": {"a": 5, "b": 9},
    }], working_directory=working_directory, rerun_required=False, verbose=True)
    assert results2['results'][0] == results1[0]
    assert len(results2['stale']) == 0

def test_wrapper(tmpdir):
    working_directory = tmpdir.mkdir("sub")
    wrapper = synpp.Synpp(config={'working_directory': working_directory})
    assert 14 == wrapper.run_single(descriptor="tests.fixtures.sum_config", config={"a": 5, "b": 9})
    res = wrapper.run_pipeline(definitions=[{"descriptor": "tests.fixtures.sum_config", "config": {"a": 5, "b": 9}}])
    assert len(res) == 1
    assert 14 == res[0]
