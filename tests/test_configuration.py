from synpp import ConfigurationContext, PipelineError
from pytest import raises

def test_config_option():
    context = ConfigurationContext({ "abc": "def" }, {})

    assert context.config("abc") == "def"
    assert "abc" in context.required_config
    assert context.required_config["abc"] == "def"

    assert context.config("uvw", "xyz") == "xyz"
    assert "uvw" in context.required_config
    assert context.required_config["uvw"] == "xyz"

def test_missing_config_option():
    context = ConfigurationContext({}, {})

    with raises(PipelineError):
        context.config("abc")

def test_duplicate_config_default():
    context = ConfigurationContext({}, {})

    with raises(PipelineError):
        context.config("abc", "D1")
        context.config("abc", "D2")

def test_parameter():
    context = ConfigurationContext({}, { "abc": "def" })

    assert context.parameter("abc") == "def"
    assert "abc" in context.required_parameters
    assert context.required_parameters["abc"] == "def"

    assert context.parameter("uvw", "xyz") == "xyz"
    assert "uvw" in context.required_parameters
    assert context.required_parameters["uvw"] == "xyz"

def test_missing_parameter():
    context = ConfigurationContext({}, {})

    with raises(PipelineError):
        context.parameter("abc")

def test_duplicate_parameter_default():
    context = ConfigurationContext({}, {})

    with raises(PipelineError):
        context.parameter("abc", "D1")
        context.parameter("abc", "D2")

def test_stage():
    context = ConfigurationContext({}, {})

    context.stage("stage1")
    context.stage("stage2", { "uvw": "xyz" }, alias = "name1")
    context.stage("stage2", { "uvw": "xyz" }, alias = "name2")

    assert ({"descriptor": "stage1", "parameters": {}}) in context.required_stages
    assert ({"descriptor": "stage2", "parameters": { "uvw": "xyz" }}) in context.required_stages
    assert 2 == len(context.required_stages)
