from synpp import ConfigurationContext, PipelineError
from pytest import raises
import synpp

def test_config_option():
    context = ConfigurationContext({ "abc": "def" })

    assert context.config("abc") == "def"
    assert "abc" in context.required_config
    assert context.required_config["abc"] == "def"

    assert context.config("uvw", "xyz") == "xyz"
    assert "uvw" in context.required_config
    assert context.required_config["uvw"] == "xyz"

def test_missing_config_option():
    context = ConfigurationContext({})

    with raises(PipelineError):
        context.config("abc")

def test_duplicate_config_default():
    context = ConfigurationContext({})

    with raises(PipelineError):
        context.config("abc", "D1")
        context.config("abc", "D2")

def test_stage():
    context = ConfigurationContext({})

    context.stage("stage1")
    context.stage("stage2", { "uvw": "xyz" }, alias = "name1")
    context.stage("stage2", { "uvw": "xyz" }, alias = "name2")

    assert ({"descriptor": "stage1", "config": {}}) in context.required_stages
    assert ({"descriptor": "stage2", "config": { "uvw": "xyz" }}) in context.required_stages
    assert 2 == len(context.required_stages)

class ComplexStage:
    def configure(self, context):
        context.config("option")
        context.config("option.sub")

    def execute(self, context):
        pass

class ComplexStageMaster:
    def configure(self, context):
        context.stage(ComplexStage)

    def execute(self, context):
        pass

def test_complex_config(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    config = {
        "option": {
            "xyz": 123,
            "sub": {
                "xyz": 123
            }
        }
    }

    # First: Need to run stage

    result = synpp.run([{
        "descriptor": ComplexStageMaster,
        "config": config }], verbose = True, working_directory = working_directory)

    assert 2 == len(result["stale"])

    # Second: Stage is cached

    result = synpp.run([{
        "descriptor": ComplexStageMaster,
        "config": config }], verbose = True, working_directory = working_directory)

    assert 1 == len(result["stale"])

    # Third: Let's change the sub-value
    config["option"]["sub"]["new"] = 5

    result = synpp.run([{
        "descriptor": ComplexStageMaster,
        "config": config }], verbose = True, working_directory = working_directory)

    assert 2 == len(result["stale"])

    result = synpp.run([{
        "descriptor": ComplexStageMaster,
        "config": config }], verbose = True, working_directory = working_directory)

    assert 1 == len(result["stale"])

    # Fourth: Let's change the whole value
    config["option"] = {
        "sub": 123, "other": "test"
    }

    result = synpp.run([{
        "descriptor": ComplexStageMaster,
        "config": config }], verbose = True, working_directory = working_directory)

    assert 2 == len(result["stale"])

    result = synpp.run([{
        "descriptor": ComplexStageMaster,
        "config": config }], verbose = True, working_directory = working_directory)

    assert 1 == len(result["stale"])

    # Fifth: Let's remove the sub value to raise error
    del config["option"]["sub"]

    raised = False

    try:
        synpp.run([{
            "descriptor": ComplexStageMaster,
            "config": config }], verbose = True, working_directory = working_directory)
    except synpp.general.PipelineError:
        raised = True

    assert raised
