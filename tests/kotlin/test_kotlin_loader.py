from unittest.mock import patch

import pytest
from strictacode.kotlin.loader import KotlinLoder


class TestKotlinLoderAttributes:
    def test_lang(self):
        assert KotlinLoder.__lang__ == "kotlin"

    def test_comment_line_prefixes(self):
        assert "//" in KotlinLoder.__comment_line_prefixes__

    def test_comment_code_blocks(self):
        assert ("/*", "*/") in KotlinLoder.__comment_code_blocks__

    def test_ignore_dirs(self):
        assert "build" in KotlinLoder.__ignore_dirs__
        assert ".gradle" in KotlinLoder.__ignore_dirs__


class TestCreateItem:
    def test_creates_class_item(self):
        from strictacode.kotlin.loader import _create_item
        from strictacode.loader import FileItemTypes

        item = _create_item(
            type="class",
            name="UserService",
            lineno=1,
            endline=30,
            complexity=8,
            classname=None,
            methods=[],
            closures=[],
        )
        assert item.type == FileItemTypes.CLASS
        assert item.name == "UserService"

    def test_creates_function_item(self):
        from strictacode.kotlin.loader import _create_item
        from strictacode.loader import FileItemTypes

        item = _create_item(
            type="function", name="init", lineno=5, endline=10, complexity=2, methods=[], closures=[]
        )
        assert item.type == FileItemTypes.FUNCTION

    def test_creates_method_item(self):
        from strictacode.kotlin.loader import _create_item
        from strictacode.loader import FileItemTypes

        item = _create_item(
            type="method",
            name="getUser",
            lineno=10,
            endline=20,
            complexity=3,
            classname="UserService",
            methods=[],
            closures=[],
        )
        assert item.type == FileItemTypes.METHOD
        assert item.class_name == "UserService"
