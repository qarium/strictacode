import pytest
from strictacode.calc.pressure.overengineering import (
    CalcResult,
    Metric,
    Score,
    Status,
    _centrality,
    _class_scores,
    _common_score,
    _depth_scores,
    _fan_in,
    _fan_out,
    _module_scores,
    _norm,
    _shortest_paths,
    calculate,
)
from strictacode.graph import DiGraph


class TestMetricStatus:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, Status.SIMPLE),
            (20, Status.SIMPLE),
            (21, Status.MODERATE),
            (40, Status.MODERATE),
            (41, Status.COMPLEX),
            (60, Status.COMPLEX),
            (61, Status.OVERENGINEERED),
            (80, Status.OVERENGINEERED),
            (81, Status.BLOATED),
        ],
    )
    def test_status_boundaries(self, value, expected):
        m = Metric(score=value)
        assert m.status == expected


class TestFanOut:
    def test_simple_graph(self, simple_graph):
        fout = _fan_out(simple_graph)
        assert fout == {"A": 2, "B": 0, "C": 0}

    def test_empty_graph(self):
        g = DiGraph()
        assert _fan_out(g) == {}

    def test_linear_chain(self):
        g = DiGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        fout = _fan_out(g)
        assert fout == {"A": 1, "B": 1, "C": 0}


class TestFanIn:
    def test_simple_graph(self, simple_graph):
        fin = _fan_in(simple_graph)
        assert fin == {"A": 0, "B": 1, "C": 1}

    def test_empty_graph(self):
        g = DiGraph()
        assert _fan_in(g) == {}

    def test_no_edges(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        assert _fan_in(g) == {"A": 0, "B": 0}


class TestShortestPaths:
    def test_single_node(self):
        g = DiGraph()
        g.add_node("A")
        assert _shortest_paths(g, "A") == {"A": 0}

    def test_linear_chain(self):
        g = DiGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        assert _shortest_paths(g, "A") == {"A": 0, "B": 1, "C": 2}

    def test_disconnected_graph(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        assert _shortest_paths(g, "A") == {"A": 0}

    def test_diamond(self):
        g = DiGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "D")
        paths = _shortest_paths(g, "A")
        assert paths["A"] == 0
        assert paths["B"] == 1
        assert paths["C"] == 1
        assert paths["D"] == 2

    def test_cyclic_graph(self):
        g = DiGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "A")
        paths = _shortest_paths(g, "A")
        assert paths["A"] == 0
        assert paths["B"] == 1
        assert paths["C"] == 2


class TestDepthScores:
    def test_single_node(self):
        g = DiGraph()
        g.add_node("A")
        assert _depth_scores(g) == {"A": 0}

    def test_linear_chain(self):
        g = DiGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        assert _depth_scores(g) == {"A": 2, "B": 1, "C": 0}

    def test_diamond(self):
        g = DiGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "D")
        depth = _depth_scores(g)
        assert depth["A"] == 2
        assert depth["B"] == 1
        assert depth["C"] == 1
        assert depth["D"] == 0


class TestCentrality:
    def test_single_node(self):
        g = DiGraph()
        g.add_node("A")
        assert _centrality(g) == {}

    def test_linear_chain(self):
        g = DiGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        cent = _centrality(g)
        assert "A" not in cent  # no node reaches A
        assert cent["B"] == 1  # reachable from A
        assert cent["C"] == 2  # reachable from A and B

    def test_star_graph(self):
        g = DiGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("A", "D")
        cent = _centrality(g)
        assert "A" not in cent  # center has no predecessors
        assert cent["B"] == 1
        assert cent["C"] == 1
        assert cent["D"] == 1

    def test_cyclic_graph(self):
        g = DiGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "A")
        cent = _centrality(g)
        # In a cycle, every node is reachable from every other node,
        # so each node accumulates centrality from all 3 BFS traversals.
        assert cent["A"] == 3
        assert cent["B"] == 3
        assert cent["C"] == 3


class TestNorm:
    @pytest.mark.parametrize(
        ("v", "t", "expected"),
        [
            (0, 10, 0.0),
            (5, 10, 0.5),
            (10, 10, 1.0),
            (15, 10, 1.0),
            (0, 1, 0.0),
        ],
    )
    def test_norm(self, v, t, expected):
        assert _norm(v, t) == expected

    def test_norm_zero_t_raises(self):
        with pytest.raises(ZeroDivisionError):
            _norm(5, 0)


class TestClassScores:
    def test_class_graph(self, class_graph):
        scores = _class_scores(class_graph)
        assert len(scores) == 3
        names = {s.name for s in scores}
        assert names == {"ClassA", "ClassB", "ClassC"}
        paths = {s.path for s in scores}
        assert paths == {"pkg/module.py", "pkg/other.py"}
        for s in scores:
            assert 0 <= s.value <= 100

    def test_nodes_without_colon_skipped(self):
        g = DiGraph()
        g.add_node("module.py:ClassA")
        g.add_node("util")  # no colon — should be skipped
        g.add_edge("module.py:ClassA", "util")
        scores = _class_scores(g)
        assert len(scores) == 1
        assert scores[0].name == "ClassA"

    def test_empty_graph(self):
        g = DiGraph()
        assert _class_scores(g) == []

    def test_single_class(self):
        g = DiGraph()
        g.add_node("pkg/mod.py:OnlyClass")
        scores = _class_scores(g)
        assert len(scores) == 1
        assert scores[0].path == "pkg/mod.py"
        assert scores[0].value >= 0


class TestModuleScores:
    def test_groups_by_path(self):
        cls_scores = [
            Score(path="pkg/a.py", name="ClassA", value=10.0),
            Score(path="pkg/a.py", name="ClassB", value=20.0),
            Score(path="pkg/b.py", name="ClassC", value=30.0),
        ]
        mod_scores = _module_scores(cls_scores)
        assert len(mod_scores) == 2
        by_path = {s.path: s for s in mod_scores}
        assert by_path["pkg/a.py"].value == 15.0  # (10+20)/2
        assert by_path["pkg/b.py"].value == 30.0

    def test_empty_input(self):
        assert _module_scores([]) == []

    def test_uses_basename_as_name(self):
        cls_scores = [
            Score(path="pkg/deep/module.py", name="X", value=10.0),
        ]
        mod_scores = _module_scores(cls_scores)
        assert mod_scores[0].name == "module.py"


class TestCommonScore:
    def test_empty_graph_no_classes(self):
        g = DiGraph()
        assert _common_score(g, []) == 0.0

    def test_single_node_no_edges(self):
        g = DiGraph()
        g.add_node("pkg/a.py:ClassA")
        cls_scores = _class_scores(g)
        score = _common_score(g, cls_scores)
        # coupling = 0/1 = 0, _norm(0, 4) = 0, so only avg_class contributes
        # ClassA has no edges: fout=0, fin=0, depth=0, centrality=0 -> value=0.0
        # avg_class = 0, coupling = 0 -> score = (0.4*0 + 0.6*0) * 100 = 0
        assert score == 0.0

    def test_dense_graph_high_score(self):
        g = DiGraph()
        # 4 nodes, 6 edges (fully connected directed)
        nodes = ["a:A", "a:B", "a:C", "a:D"]
        for n in nodes:
            g.add_node(n)
        for a in nodes:
            for b in nodes:
                if a != b:
                    g.add_edge(a, b)
        cls_scores = _class_scores(g)
        score = _common_score(g, cls_scores)
        # coupling = 12/4 = 3.0, _norm(3,4) = 0.75 — should push score up
        assert score > 0
        assert score > 40  # dense graph with high connectivity yields ~54


class TestCalculate:
    def test_class_graph(self, class_graph):
        result = calculate(class_graph)
        assert isinstance(result, CalcResult)
        assert isinstance(result.score, int)
        assert result.score >= 10  # class_graph produces score ~12
        assert len(result.classes) == 3
        assert len(result.modules) == 2  # module.py + other.py

    def test_empty_graph(self):
        g = DiGraph()
        result = calculate(g)
        assert result.score == 0
        assert result.classes == []
        assert result.modules == []

    def test_score_is_int(self):
        g = DiGraph()
        g.add_node("pkg/mod.py:ClassA")
        result = calculate(g)
        assert isinstance(result.score, int)

    def test_calc_result_rounds_score(self):
        # CalcResult.__post_init__ rounds to int
        result = CalcResult(score=45.7, classes=[], modules=[])
        assert result.score == 46
        result2 = CalcResult(score=45.3, classes=[], modules=[])
        assert result2.score == 45
