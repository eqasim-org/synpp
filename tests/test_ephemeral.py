import synpp

#
#  A <- B
#  A <- C <- (ephemeral) D
#

def test_non_ephemeral_B(tmpdir):
    working_directory = tmpdir.mkdir("cache")

    result = synpp.run([
        { "descriptor": "tests.fixtures.ephemeral.B" }
    ], working_directory = working_directory, verbose = True)

    assert "tests.fixtures.ephemeral.A" in result["stale"]
    assert "tests.fixtures.ephemeral.B" in result["stale"]
    assert not "tests.fixtures.ephemeral.C" in result["stale"]

    result = synpp.run([
        { "descriptor": "tests.fixtures.ephemeral.B" }
    ], working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.ephemeral.A" in result["stale"]
    assert "tests.fixtures.ephemeral.B" in result["stale"]
    assert not "tests.fixtures.ephemeral.C" in result["stale"]

def test_non_ephemeral_C(tmpdir):
    working_directory = tmpdir.mkdir("cache")

    result = synpp.run([
        { "descriptor": "tests.fixtures.ephemeral.C" }
    ], working_directory = working_directory, verbose = True)

    assert "tests.fixtures.ephemeral.A" in result["stale"]
    assert not "tests.fixtures.ephemeral.B" in result["stale"]
    assert "tests.fixtures.ephemeral.C" in result["stale"]

    result = synpp.run([
        { "descriptor": "tests.fixtures.ephemeral.C" }
    ], working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.ephemeral.A" in result["stale"]
    assert not "tests.fixtures.ephemeral.B" in result["stale"]
    assert "tests.fixtures.ephemeral.C" in result["stale"]

def test_ephemeral_D(tmpdir):
    working_directory = tmpdir.mkdir("cache")

    result = synpp.run([
        { "descriptor": "tests.fixtures.ephemeral.D" }
    ], working_directory = working_directory, verbose = True)

    assert "tests.fixtures.ephemeral.A" in result["stale"]
    assert not "tests.fixtures.ephemeral.B" in result["stale"]
    assert "tests.fixtures.ephemeral.C" in result["stale"]
    assert "tests.fixtures.ephemeral.D" in result["stale"]

    result = synpp.run([
        { "descriptor": "tests.fixtures.ephemeral.D" }
    ], working_directory = working_directory, verbose = True)

    assert "tests.fixtures.ephemeral.A" in result["stale"]
    assert not "tests.fixtures.ephemeral.B" in result["stale"]
    assert "tests.fixtures.ephemeral.C" in result["stale"]
    assert "tests.fixtures.ephemeral.D" in result["stale"]

def test_ephemeral_BD(tmpdir):
    working_directory = tmpdir.mkdir("cache")

    result = synpp.run([
        { "descriptor": "tests.fixtures.ephemeral.D" },
        { "descriptor": "tests.fixtures.ephemeral.B" }
    ], working_directory = working_directory, verbose = True)

    assert "tests.fixtures.ephemeral.A" in result["stale"]
    assert "tests.fixtures.ephemeral.B" in result["stale"]
    assert "tests.fixtures.ephemeral.C" in result["stale"]
    assert "tests.fixtures.ephemeral.D" in result["stale"]    

    result = synpp.run([
        { "descriptor": "tests.fixtures.ephemeral.D" }
    ], working_directory = working_directory, verbose = True)

    assert not "tests.fixtures.ephemeral.A" in result["stale"]
    assert not "tests.fixtures.ephemeral.B" in result["stale"]
    assert "tests.fixtures.ephemeral.C" in result["stale"]
    assert "tests.fixtures.ephemeral.D" in result["stale"]
