import synpp
import json


def test_visualize_stages_results():

    result = synpp.run([{
        "descriptor": "tests.fixtures.visualization.stage_3"
    }], dryrun = True)

    assert result['nodes'] == [{"id": "tests.fixtures.visualization.stage_3"},
                               {"id": "tests.fixtures.visualization.stage_1"},
                               {"id": "tests.fixtures.visualization.stage_2"}]

    assert result['links'] == [{'source': 'tests.fixtures.visualization.stage_1',
                                'target': 'tests.fixtures.visualization.stage_3',
                                'key': 0},
                               {'source': 'tests.fixtures.visualization.stage_1',
                                'target': 'tests.fixtures.visualization.stage_2',
                                'key': 0},
                               {'source': 'tests.fixtures.visualization.stage_2',
                                'target': 'tests.fixtures.visualization.stage_3',
                                'key': 0}]