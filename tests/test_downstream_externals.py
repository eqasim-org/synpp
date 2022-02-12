import importlib
import sys
import synpp

def test_without_externals(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    result = synpp.run([{
        "descriptor": "tests.fixtures.downstream.chain_d"
    }], working_directory = working_directory, verbose = True)

    for x in result["stale"]:
        print(x)

    assert result['results'][0] == 15

def test_with_a(tmpdir):
    working_directory = tmpdir.mkdir("sub")
    
    externals = {
        "tests.fixtures.downstream.chain_a": "./tests/fixtures/externals/external_a.py"
    }

    for key in ["tests.fixtures.downstream.chain_a", "tests.fixtures.downstream.chain_b"]:
        if key in sys.modules:
            del sys.modules[key]

    result = synpp.run([{
        "descriptor": "tests.fixtures.downstream.chain_d"
    }], working_directory = working_directory, verbose = True, externals=externals)

    for x in result["stale"]:
        print(x)

    assert result['results'][0] == 300
    
def test_with_b(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    externals = {
        "tests.fixtures.downstream.chain_b": "./tests/fixtures/externals/external_b.py"
    }

    for key in ["tests.fixtures.downstream.chain_a", "tests.fixtures.downstream.chain_b"]:
        if key in sys.modules:
            del sys.modules[key]

    result = synpp.run([{
        "descriptor": "tests.fixtures.downstream.chain_d"
    }], working_directory = working_directory, verbose = True, externals=externals)

    for x in result["stale"]:
        print(x)

    assert result['results'][0] == 150

def test_with_a_b(tmpdir):
    working_directory = tmpdir.mkdir("sub")
    
    externals = {
        "tests.fixtures.downstream.chain_a": "./tests/fixtures/externals/external_a.py",
        "tests.fixtures.downstream.chain_b": "./tests/fixtures/externals/external_b.py"
    }

    for key in ["tests.fixtures.downstream.chain_a", "tests.fixtures.downstream.chain_b"]:
        if key in sys.modules:
            del sys.modules[key]

    result = synpp.run([{
        "descriptor": "tests.fixtures.downstream.chain_d"
    }], working_directory = working_directory, verbose = True, externals=externals)

    for x in result["stale"]:
        print(x)

    assert result['results'][0] == 3000