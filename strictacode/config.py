import json
from dataclasses import dataclass, field
from enum import Enum

import yaml

from . import constants


class Language(str, Enum):
    GOLANG = "golang"
    PYTHON = "python"
    JAVASCRIPT = "javascript"


@dataclass(kw_only=True)
class Loader:
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class ReporterTop:
    packages: int = field(default=constants.DEFAULT_TOP_PACKAGES)
    modules: int = field(default=constants.DEFAULT_TOP_MODULES)
    classes: int = field(default=constants.DEFAULT_TOP_CLASSES)
    methods: int = field(default=constants.DEFAULT_TOP_METHODS)
    functions: int = field(default=constants.DEFAULT_TOP_FUNCTIONS)


@dataclass(kw_only=True)
class Reporter:
    top: ReporterTop = field(default_factory=ReporterTop)

    def __post_init__(self):
        if isinstance(self.top, dict):
            self.top = ReporterTop(**self.top)


@dataclass(kw_only=True)
class Config:
    lang: Language | None = field(default=None)
    loader: Loader = field(default_factory=Loader)
    reporter: Reporter = field(default_factory=Reporter)

    def __post_init__(self):
        if self.lang is not None and not isinstance(self.lang, Language):
            self.lang = Language(self.lang)
        if isinstance(self.loader, dict):
            self.loader = Loader(**self.loader)
        if isinstance(self.reporter, dict):
            self.reporter = Reporter(**self.reporter)

    @classmethod
    def from_json_file(cls, config_path: str) -> "Config":
        with open(config_path, encoding="utf-8") as fo:
            data = json.load(fo)
        return cls(**data)

    @classmethod
    def from_yaml_file(cls, config_path: str) -> "Config":
        with open(config_path, encoding="utf-8") as fo:
            data = yaml.safe_load(fo)
        return cls(**data)
