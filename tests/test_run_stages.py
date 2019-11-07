import synpp
from pytest import raises

def test_sum_params():
    result = synpp.run([("tests.fixtures.sum_params", { "a": 5, "b": 9 })])
    assert result[0] == 14

def test_sum_config():
    result = synpp.run([("tests.fixtures.sum_config", {})], { "a": 5, "b": 11 })
    assert result[0] == 16

def test_cycle():
    with raises(synpp.PipelineError):
        synpp.run([("tests.fixtures.cycle_stage_a", {})], {})

def test_sum_stages():
    result = synpp.run([("tests.fixtures.sum_stages", {})], { "a": 5, "b": 11 })
#    assert result[0] == 11 + 16 + 10
