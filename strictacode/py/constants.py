import typing as t

BASE_TYPES: t.Final = frozenset(
    {
        # Primitives
        "str", "int", "float", "bool", "bytes", "bytearray",
        "list", "dict", "set", "tuple", "frozenset",
        "None", "type", "object", "complex",
        # typing module
        "Optional", "Union", "Any", "Callable", "Type",
        "ClassVar", "Final", "Literal", "Sequence",
        "Mapping", "Iterator", "Generator", "Awaitable",
        "AsyncIterator", "ContextManager", "IO",
        # Common exceptions
        "Exception", "BaseException", "ValueError",
        "TypeError", "RuntimeError", "KeyError",
        "IndexError", "AttributeError", "NotImplementedError",
        # stdlib common types
        "Path", "Decimal", "UUID", "datetime", "date", "time",
        "timedelta", "Pattern", "Match",
        # Literals
        "Enum",
    }
)
