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


def test_visualize_stages_io(tmpdir):

    flowchart_path = tmpdir.mkdir("sub") + "/data.json"

    synpp.run([{
        "descriptor": "tests.fixtures.visualization.stage_3"
    }], dryrun = True, flowchart_path=flowchart_path)

    with open(flowchart_path) as json_file:
        data = json.load(json_file)

    assert data['nodes'] == [{"id": "tests.fixtures.visualization.stage_3"},
                             {"id": "tests.fixtures.visualization.stage_1"},
                             {"id": "tests.fixtures.visualization.stage_2"}]

    assert data['links'] == [{'source': 'tests.fixtures.visualization.stage_1',
                              'target': 'tests.fixtures.visualization.stage_3',
                              'key': 0},
                             {'source': 'tests.fixtures.visualization.stage_1',
                              'target': 'tests.fixtures.visualization.stage_2',
                              'key': 0},
                             {'source': 'tests.fixtures.visualization.stage_2',
                              'target': 'tests.fixtures.visualization.stage_3',
                              'key': 0}]