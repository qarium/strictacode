from strictacode.py.constants import BASE_TYPES


def test_base_types_is_frozenset():
    assert isinstance(BASE_TYPES, frozenset)


def test_base_types_contains_primitives():
    assert "str" in BASE_TYPES
    assert "int" in BASE_TYPES
    assert "float" in BASE_TYPES
    assert "bool" in BASE_TYPES
    assert "list" in BASE_TYPES
    assert "dict" in BASE_TYPES
    assert "set" in BASE_TYPES
    assert "tuple" in BASE_TYPES
    assert "None" in BASE_TYPES


def test_base_types_contains_typing():
    assert "Optional" in BASE_TYPES
    assert "Union" in BASE_TYPES
    assert "Any" in BASE_TYPES
    assert "Callable" in BASE_TYPES
    assert "Type" in BASE_TYPES
    assert "ClassVar" in BASE_TYPES
    assert "Final" in BASE_TYPES
    assert "Literal" in BASE_TYPES


def test_base_types_contains_common_exceptions():
    assert "Exception" in BASE_TYPES
    assert "ValueError" in BASE_TYPES
    assert "TypeError" in BASE_TYPES


def test_base_types_not_contains_custom():
    assert "User" not in BASE_TYPES
    assert "MyService" not in BASE_TYPES
