import importlib
import sys
import synpp

class ReplacementStage:
    def configure(self, context):
        pass

    def execute(self, context):
        return "replacement"

def test_without_alias(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    result = synpp.run([{
        "descriptor": "tests.fixtures.downstream.chain_d"
    }], working_directory = working_directory, verbose = True)

    assert result['results'][0] == 15

def test_with_alias(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    result = synpp.run([{
        "descriptor": "tests.fixtures.downstream.chain_d"
    }], working_directory = working_directory, verbose = True, aliases = {
        "tests.fixtures.downstream.chain_d": ReplacementStage
    })

    assert result['results'][0] == "replacement"
