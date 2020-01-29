import synpp

def test_ephemeral_stages(tmpdir):
    working_directory = tmpdir.mkdir("cache")

    result = synpp.run([
        { "descriptor": "tests.fixtures.ephemeral.B" }
    ], working_directory = working_directory, verbose = True)

    assert "tests.fixtures.ephemeral.A" in result["stale"]
    assert "tests.fixtures.ephemeral.B" in result["stale"]
    assert not "tests.fixtures.ephemeral.C" in result["stale"]
    assert not "tests.fixtures.ephemeral.C" in result["stale"]

    result = synpp.run([
        { "descriptor": "tests.fixtures.ephemeral.C" }
    ], working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.ephemeral.A" in result["stale"]
    assert "tests.fixtures.ephemeral.B" in result["stale"]
    assert "tests.fixtures.ephemeral.C" in result["stale"]
    assert not "tests.fixtures.ephemeral.D" in result["stale"]

    result = synpp.run([
        { "descriptor": "tests.fixtures.ephemeral.C" }
    ], working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.ephemeral.A" in result["stale"]
    assert "tests.fixtures.ephemeral.B" in result["stale"]
    assert "tests.fixtures.ephemeral.C" in result["stale"]
    assert not "tests.fixtures.ephemeral.D" in result["stale"]

    result = synpp.run([
        { "descriptor": "tests.fixtures.ephemeral.D" }
    ], working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.ephemeral.A" in result["stale"]
    assert not "tests.fixtures.ephemeral.B" in result["stale"]
    assert not "tests.fixtures.ephemeral.C" in result["stale"]
    assert "tests.fixtures.ephemeral.D" in result["stale"]
