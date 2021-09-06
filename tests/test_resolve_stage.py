import synpp
from pytest import raises
import tests.test_resolve_stage, tests.fixtures.fixture_stage

class TestStage:
    def execute(self, context):
        return "result"

def test_resolve_module():
    assert synpp.resolve_stage(tests.fixtures.fixture_stage).execute(None) == "result"

def test_resolve_class():
    assert synpp.resolve_stage(tests.test_resolve_stage.TestStage).execute(None) == "result"

def test_resolve_object():
    assert synpp.resolve_stage(tests.test_resolve_stage.TestStage()).execute(None) == "result"

def test_resolve_module_string():
    assert synpp.resolve_stage("tests.fixtures.fixture_stage").execute(None) == "result"

def test_resolve_class_string():
    assert synpp.resolve_stage("tests.fixtures.fixture_stage.SubStage").execute(None) == "result"

def test_resolve_decorated_function():
    @synpp.stage
    def stage_func():
        return "result"
    assert synpp.resolve_stage(stage_func).execute(None) == "result"
