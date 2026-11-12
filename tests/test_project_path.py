from pathlib import Path

import pytest

from synpp.pipeline import ExecuteContext, ValidateContext, apply_project_path


@pytest.mark.parametrize("as_path", [False, True], ids=["string", "path"])
@pytest.mark.parametrize("absolute", [False, True], ids=["relative", "absolute"])
@pytest.mark.parametrize("with_project", [False, True], ids=["no-project", "project"])
def test_apply_project_path(tmp_path, as_path, absolute, with_project):
    project_path = tmp_path / "project" if with_project else None
    path = tmp_path / "absolute.csv" if absolute else Path("folder/myfile.csv")
    path = path if as_path else str(path)

    expected = project_path / path if with_project and not absolute else path

    assert apply_project_path(path, project_path) == expected


@pytest.fixture(params=[ValidateContext, ExecuteContext])
def context(request, tmp_path):
    project_path = tmp_path / "project"

    if request.param is ValidateContext:
        return ValidateContext({}, None, project_path)

    return ExecuteContext(
        required_config={}, required_stages=[], aliases={}, working_directory=None,
        dependencies=[], cache_path=None, project_path=project_path,
        pipeline_config={}, logger=None, cache={}, dependency_info={})


def test_context_project_path(context, tmp_path):
    assert context.project_path() == tmp_path / "project"


@pytest.mark.parametrize("as_path", [False, True], ids=["string", "path"])
@pytest.mark.parametrize("absolute", [False, True], ids=["relative", "absolute"])
def test_context_project_path_suffix(context, tmp_path, as_path, absolute):
    path = tmp_path / "absolute.csv" if absolute else Path("folder/myfile.csv")
    path = path if as_path else str(path)

    expected = path if absolute else tmp_path / "project" / path

    assert context.project_path(path) == expected
