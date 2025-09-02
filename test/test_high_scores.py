import ast
import types
import json
from pathlib import Path
import pytest


@pytest.fixture()
def hs_module():
    """Load high score helpers from axolotl_dash without importing pygame."""
    path = Path(__file__).resolve().parent.parent / "axolotl_dash.py"
    source = path.read_text()
    tree = ast.parse(source)
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id in {"HIGH_SCORES_FILE", "MAX_HIGH_SCORES"} for t in node.targets):
                nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in {"load_high_scores", "save_high_scores", "submit_high_score"}:
            nodes.append(node)
    module = types.ModuleType("hs_module")
    module.__dict__["json"] = json
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "hs_module", "exec"), module.__dict__)
    return module


def test_submit_high_score_sorted_and_rank(hs_module):
    scores = [50, 200, 100]
    updated, qualifies, rank = hs_module.submit_high_score(scores, 150)
    assert updated == [200, 150, 100, 50]
    assert rank == 2
    assert qualifies


def test_submit_high_score_limits_top_10(hs_module):
    scores = [1000, 900, 800, 700, 600, 500, 400, 300, 200, 100]
    updated, qualifies, rank = hs_module.submit_high_score(scores, 650)
    assert updated == [1000, 900, 800, 700, 650, 600, 500, 400, 300, 200]
    assert len(updated) == 10
    assert rank == 5
    assert qualifies


def test_submit_high_score_persistence(tmp_path, hs_module, monkeypatch):
    temp_file = tmp_path / "scores.json"
    monkeypatch.setattr(hs_module, "HIGH_SCORES_FILE", temp_file)
    initial = [1000, 900, 800, 700, 600, 500, 400, 300, 200, 100]
    hs_module.save_high_scores(initial)
    loaded = hs_module.load_high_scores()
    assert loaded == initial
    updated, qualifies, rank = hs_module.submit_high_score(loaded, 750)
    hs_module.save_high_scores(updated)
    reloaded = hs_module.load_high_scores()
    assert reloaded == [1000, 900, 800, 750, 700, 600, 500, 400, 300, 200]
    assert len(reloaded) == 10
    assert rank == 4
    assert qualifies
