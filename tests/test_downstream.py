import synpp

def test_devalidate_by_downstream_config(tmpdir):
    working_directory = tmpdir.mkdir("sub")

    result = synpp.run([{
        "descriptor": "tests.fixtures.downstream.chain_d"
    }], working_directory = working_directory, verbose = True)

    for x in result["stale"]:
        print(x)

    assert "tests.fixtures.downstream.chain_a__b1d43cd340a6b095b41ad645446b6800" in result["stale"]
    assert "tests.fixtures.downstream.chain_a__798cc71deef8c6835483eb116d0ce9bd" in result["stale"]
    assert "tests.fixtures.downstream.chain_b__b1d43cd340a6b095b41ad645446b6800" in result["stale"]
    assert "tests.fixtures.downstream.chain_b__798cc71deef8c6835483eb116d0ce9bd" in result["stale"]
    assert "tests.fixtures.downstream.chain_c__b1d43cd340a6b095b41ad645446b6800" in result["stale"]
    assert "tests.fixtures.downstream.chain_c__798cc71deef8c6835483eb116d0ce9bd" in result["stale"]
    assert "tests.fixtures.downstream.chain_d" in result["stale"]
