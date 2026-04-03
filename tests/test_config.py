import json

import pytest
import yaml
from strictacode import constants
from strictacode.config import Config, Language, Loader, Reporter, ReporterTop


# ---------------------------------------------------------------------------
# 1. Language enum values
# ---------------------------------------------------------------------------
class TestLanguage:
    def test_values(self):
        assert Language.GOLANG == "golang"
        assert Language.PYTHON == "python"
        assert Language.JAVASCRIPT == "javascript"
        assert Language.KOTLIN == "kotlin"
        assert Language.SWIFT == "swift"

    def test_is_str_enum(self):
        """Language inherits from both str and Enum, so comparison with plain
        strings must work."""
        assert Language.GOLANG == "golang"
        assert isinstance(Language.PYTHON, str)

    def test_from_string(self):
        assert Language("python") is Language.PYTHON
        assert Language("javascript") is Language.JAVASCRIPT
        assert Language("kotlin") is Language.KOTLIN
        assert Language("swift") is Language.SWIFT


# ---------------------------------------------------------------------------
# 2. Loader defaults
# ---------------------------------------------------------------------------
class TestLoader:
    def test_defaults(self):
        loader = Loader()
        assert loader.include == []
        assert loader.exclude == []

    def test_mutable_default_isolation(self):
        """Each instance must get its own list, not a shared reference."""
        a = Loader()
        b = Loader()
        a.include.append("foo")
        assert b.include == []


# ---------------------------------------------------------------------------
# 3. ReporterTop defaults match constants
# ---------------------------------------------------------------------------
class TestReporterTop:
    def test_defaults_match_constants(self):
        rt = ReporterTop()
        assert rt.packages == constants.DEFAULT_TOP_PACKAGES
        assert rt.modules == constants.DEFAULT_TOP_MODULES
        assert rt.classes == constants.DEFAULT_TOP_CLASSES
        assert rt.methods == constants.DEFAULT_TOP_METHODS
        assert rt.functions == constants.DEFAULT_TOP_FUNCTIONS

    def test_custom_values(self):
        rt = ReporterTop(packages=99, modules=88)
        assert rt.packages == 99
        assert rt.modules == 88
        assert rt.classes == constants.DEFAULT_TOP_CLASSES


# ---------------------------------------------------------------------------
# 4. Reporter __post_init__ with dict -> converts to ReporterTop
# ---------------------------------------------------------------------------
class TestReporter:
    def test_default_top(self):
        reporter = Reporter()
        assert isinstance(reporter.top, ReporterTop)

    def test_dict_top_converted(self):
        reporter = Reporter(top={"packages": 42})
        assert isinstance(reporter.top, ReporterTop)
        assert reporter.top.packages == 42
        # remaining fields should still hold their defaults
        assert reporter.top.modules == constants.DEFAULT_TOP_MODULES


# ---------------------------------------------------------------------------
# 5. Config defaults
# ---------------------------------------------------------------------------
class TestConfigDefaults:
    def test_defaults(self):
        cfg = Config()
        assert cfg.lang is None
        assert isinstance(cfg.loader, Loader)
        assert isinstance(cfg.reporter, Reporter)

    def test_loader_and_reporter_have_nested_defaults(self):
        cfg = Config()
        assert cfg.loader.include == []
        assert cfg.loader.exclude == []
        assert isinstance(cfg.reporter.top, ReporterTop)


# ---------------------------------------------------------------------------
# 6. Config __post_init__ with lang as string -> Language enum
# ---------------------------------------------------------------------------
class TestConfigLangConversion:
    def test_string_lang_converted_to_enum(self):
        cfg = Config(lang="python")
        assert isinstance(cfg.lang, Language)
        assert cfg.lang is Language.PYTHON

    def test_enum_lang_unchanged(self):
        cfg = Config(lang=Language.JAVASCRIPT)
        assert cfg.lang is Language.JAVASCRIPT

    def test_none_lang_stays_none(self):
        cfg = Config(lang=None)
        assert cfg.lang is None

    def test_invalid_string_lang_raises_value_error(self):
        with pytest.raises(ValueError, match="'rust' is not a valid Language"):
            Config(lang="rust")


# ---------------------------------------------------------------------------
# 7. Config __post_init__ with loader as dict
# ---------------------------------------------------------------------------
class TestConfigLoaderDict:
    def test_dict_loader_converted(self):
        cfg = Config(loader={"include": ["src/"], "exclude": ["venv/"]})
        assert isinstance(cfg.loader, Loader)
        assert cfg.loader.include == ["src/"]
        assert cfg.loader.exclude == ["venv/"]

    def test_partial_dict_uses_defaults(self):
        cfg = Config(loader={"include": ["src/"]})
        assert isinstance(cfg.loader, Loader)
        assert cfg.loader.include == ["src/"]
        assert cfg.loader.exclude == []


# ---------------------------------------------------------------------------
# 8. Config __post_init__ with reporter as dict
# ---------------------------------------------------------------------------
class TestConfigReporterDict:
    def test_dict_reporter_converted(self):
        cfg = Config(reporter={"top": {"packages": 7}})
        assert isinstance(cfg.reporter, Reporter)
        assert isinstance(cfg.reporter.top, ReporterTop)
        assert cfg.reporter.top.packages == 7
        assert cfg.reporter.top.modules == constants.DEFAULT_TOP_MODULES


# ---------------------------------------------------------------------------
# 9. Config.from_json_file
# ---------------------------------------------------------------------------
class TestConfigFromJsonFile:
    def test_roundtrip(self, tmp_path):
        payload = {
            "lang": "golang",
            "loader": {"include": ["cmd/"], "exclude": ["vendor/"]},
            "reporter": {"top": {"packages": 3, "modules": 5}},
        }
        json_path = tmp_path / "config.json"
        json_path.write_text(json.dumps(payload), encoding="utf-8")

        cfg = Config.from_json_file(str(json_path))

        assert isinstance(cfg.lang, Language)
        assert cfg.lang is Language.GOLANG
        assert cfg.loader.include == ["cmd/"]
        assert cfg.loader.exclude == ["vendor/"]
        assert cfg.reporter.top.packages == 3
        assert cfg.reporter.top.modules == 5

    def test_minimal_json(self, tmp_path):
        json_path = tmp_path / "empty.json"
        json_path.write_text("{}", encoding="utf-8")

        cfg = Config.from_json_file(str(json_path))

        assert cfg.lang is None
        assert isinstance(cfg.loader, Loader)
        assert isinstance(cfg.reporter, Reporter)

    def test_nonexistent_json_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            Config.from_json_file(str(tmp_path / "nonexistent.json"))

    def test_from_json_file_malformed(self, tmp_path):
        json_path = tmp_path / "malformed.json"
        json_path.write_text("{invalid json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            Config.from_json_file(str(json_path))


# ---------------------------------------------------------------------------
# 10. Config.from_yaml_file
# ---------------------------------------------------------------------------
class TestConfigFromYamlFile:
    def test_roundtrip(self, tmp_path):
        yaml_content = (
            "lang: javascript\n"
            "loader:\n"
            "  include: ['lib/']\n"
            "  exclude: ['node_modules/']\n"
            "reporter:\n"
            "  top:\n"
            "    classes: 15\n"
        )
        yaml_path = tmp_path / "config.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        cfg = Config.from_yaml_file(str(yaml_path))

        assert isinstance(cfg.lang, Language)
        assert cfg.lang is Language.JAVASCRIPT
        assert cfg.loader.include == ["lib/"]
        assert cfg.loader.exclude == ["node_modules/"]
        assert cfg.reporter.top.classes == 15
        assert cfg.reporter.top.packages == constants.DEFAULT_TOP_PACKAGES

    def test_minimal_yaml(self, tmp_path):
        yaml_path = tmp_path / "empty.yaml"
        yaml_path.write_text("{}\n", encoding="utf-8")

        cfg = Config.from_yaml_file(str(yaml_path))

        assert cfg.lang is None
        assert isinstance(cfg.loader, Loader)
        assert isinstance(cfg.reporter, Reporter)

    def test_from_yaml_file_malformed(self, tmp_path):
        yaml_path = tmp_path / "malformed.yaml"
        yaml_path.write_text("{: invalid", encoding="utf-8")
        with pytest.raises(yaml.YAMLError):
            Config.from_yaml_file(str(yaml_path))
