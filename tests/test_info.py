import synpp
from pytest import raises

def test_info(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    result = synpp.run([
        { "descriptor": "tests.fixtures.info2" }
    ], working_directory = working_directory, verbose = True)

    assert "tests.fixtures.info1" in result["stale"]
    assert "tests.fixtures.info2" in result["stale"]
    assert result["info"]["abc"] == "123"
    assert result["info"]["uvw"] == "789"
    assert result["info"]["concat"] == "123789"

    result = synpp.run([
        { "descriptor": "tests.fixtures.info2" }
    ], working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.info1" in result["stale"]
    assert "tests.fixtures.info2" in result["stale"]
    assert result["info"]["abc"] == "123"
    assert result["info"]["uvw"] == "789"
    assert result["info"]["concat"] == "123789"
