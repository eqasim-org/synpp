import synpp
from pytest import raises

def test_devalidate_by_config(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.B"
    }], config = { "a": 1 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.devalidation.A1__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert "tests.fixtures.devalidation.A2" in result["stale"]
    assert "tests.fixtures.devalidation.B__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.B"
    }], config = { "a": 1, "b": 1 }, working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.devalidation.A1__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert not "tests.fixtures.devalidation.A2" in result["stale"]
    assert "tests.fixtures.devalidation.B__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.B"
    }], config = { "a": 2 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.devalidation.A1__9f8a8e5ba8c70c774d410a9107e2a32b" in result["stale"]
    assert not "tests.fixtures.devalidation.A2" in result["stale"]
    assert "tests.fixtures.devalidation.B__9f8a8e5ba8c70c774d410a9107e2a32b" in result["stale"]

def test_devalidate_by_passed_on_config(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.A1"
    }], config = { "a": 1, "d": 5 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.devalidation.A1__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.D"
    }], config = { "a": 1, "d": 5 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.devalidation.A1__b1d43cd340a6b095b41ad645446b6800" in result["stale"]
    assert "tests.fixtures.devalidation.D__2ea707fadc0d136c95611cd3de856f0a" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.D"
    }], config = { "a": 1, "d": 10 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.devalidation.A1__798cc71deef8c6835483eb116d0ce9bd" in result["stale"]
    assert "tests.fixtures.devalidation.D__7532252d06e50cdf1ddbfe8269a47aa8" in result["stale"]

def test_devalidate_by_parent(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.C"
    }], config = { "a": 1 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.devalidation.A1__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert "tests.fixtures.devalidation.A2" in result["stale"]
    assert "tests.fixtures.devalidation.B__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert "tests.fixtures.devalidation.C__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.C"
    }], config = { "a": 1 }, working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.devalidation.A1__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert not "tests.fixtures.devalidation.A2" in result["stale"]
    assert not "tests.fixtures.devalidation.B__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert "tests.fixtures.devalidation.C__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.A2"
    }], config = { "a": 1 }, working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.devalidation.A1__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert "tests.fixtures.devalidation.A2" in result["stale"]
    assert not "tests.fixtures.devalidation.B__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert not "tests.fixtures.devalidation.C__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.C"
    }], config = { "a": 1 }, working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.devalidation.A1__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert not "tests.fixtures.devalidation.A2" in result["stale"]
    assert "tests.fixtures.devalidation.B__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert "tests.fixtures.devalidation.C__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]

def test_devalidate_descendants(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.C"
    }], config = { "a": 1 }, working_directory = working_directory, verbose = True)

    assert "tests.fixtures.devalidation.A1__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert "tests.fixtures.devalidation.A2" in result["stale"]
    assert "tests.fixtures.devalidation.B__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert "tests.fixtures.devalidation.C__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.C"
    }, {
        "descriptor": "tests.fixtures.devalidation.A2"
    }], config = { "a": 1 }, working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.devalidation.A1__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert "tests.fixtures.devalidation.A2" in result["stale"]
    assert "tests.fixtures.devalidation.B__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]
    assert "tests.fixtures.devalidation.C__42b7b4f2921788ea14dac5566e6f06d0" in result["stale"]

def test_devalidate_token(tmpdir):
    working_directory = tmpdir.mkdir("sub")
    path = "%s/test.fixture" % working_directory

    with open(path, "w+") as f:
        f.write("abcdef")

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.token_b"
    }], config = { "path": path }, working_directory = working_directory, verbose = True)

    name_a, name_b = None, None
    for name in result["stale"]:
        if "token_a" in name:
            name_a = name
        if "token_b" in name:
            name_b = name

    assert name_a in result["stale"]
    assert name_b in result["stale"]
    assert result["results"][0] == "abcdef"

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.token_b"
    }], config = { "path": path }, working_directory = working_directory, verbose = True)

    assert not name_a in result["stale"]
    assert name_b in result["stale"]
    assert result["results"][0] == "abcdef"

    with open(path, "w+") as f:
        f.write("uvwxyz")

    result = synpp.run([{
        "descriptor": "tests.fixtures.devalidation.token_b"
    }], config = { "path": path }, working_directory = working_directory, verbose = True)

    assert name_a in result["stale"]
    assert name_b in result["stale"]
    assert result["results"][0] == "uvwxyz"
