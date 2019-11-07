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

    assert context.param("abc") == "def"
    assert "abc" in context.required_params
    assert context.required_params["abc"] == "def"

    assert context.param("uvw", "xyz") == "xyz"
    assert "uvw" in context.required_params
    assert context.required_params["uvw"] == "xyz"

def test_missing_parameter():
    context = ConfigurationContext({}, {})

    with raises(PipelineError):
        context.param("abc")

def test_duplicate_parameter_default():
    context = ConfigurationContext({}, {})

    with raises(PipelineError):
        context.param("abc", "D1")
        context.param("abc", "D2")

def test_stage():
    context = ConfigurationContext({}, {})

    context.stage("stage1")
    context.stage("stage2", { "uvw": "xyz" }, alias = "name1")
    context.stage("stage2", { "uvw": "xyz" }, alias = "name2")

    assert ("stage1", {}) in context.required_stages
    assert ("stage2", { "uvw": "xyz" }) in context.required_stages
    assert 2 == len(context.required_stages)
