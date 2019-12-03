import synpp
from pytest import raises

def test_sum_params():
    result = synpp.run([{
        "descriptor": "tests.fixtures.sum_params",
        "parameters": { "a": 5, "b": 9 }
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
        "parameters": { "a": 5 }
    }], working_directory = tmpdir.mkdir("sub"))

    assert result[0] == 15
