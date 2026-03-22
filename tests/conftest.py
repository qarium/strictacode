import textwrap

import pytest
from strictacode.graph import DiGraph


@pytest.fixture
def simple_graph():
    g = DiGraph()
    g.add_node("A")
    g.add_node("B")
    g.add_node("C")
    g.add_edge("A", "B")
    g.add_edge("A", "C")
    return g


@pytest.fixture
def class_graph():
    """DiGraph with class-qualified nodes ('pkg/file.py:Class'). Used in test_overengineering.py."""
    g = DiGraph()
    g.add_node("pkg/module.py:ClassA")
    g.add_node("pkg/module.py:ClassB")
    g.add_node("pkg/other.py:ClassC")
    g.add_edge("pkg/module.py:ClassA", "pkg/module.py:ClassB")
    g.add_edge("pkg/module.py:ClassA", "pkg/other.py:ClassC")
    return g


@pytest.fixture
def tmp_py_file(tmp_path):
    """Temporary .py file with known content. Used in test_utils.py and test_source.py."""
    filepath = tmp_path / "sample.py"
    filepath.write_text(textwrap.dedent("""\
        # comment
        def foo():
            x = 1
            return x

        def bar():
            y = 2
            if y > 0:
                return y
            return 0
    """))
    return str(filepath)


@pytest.fixture
def tmp_project_with_gitignore(tmp_path):
    """Project dir with .gitignore and dist/build subdirs. Used in test_utils.py."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("dist\nbuild\n*.egg-info\n")
    (tmp_path / "dist").mkdir()
    (tmp_path / "build").mkdir()
    (tmp_path / "src").mkdir()
    return tmp_path
