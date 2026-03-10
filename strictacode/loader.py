import os
import abc
import dataclasses
import typing as t
from pathlib import Path
from functools import cached_property

from . import utils
from .source import (
    Sources,
    PackageSource,
    ModuleSource,
    ClassSource,
    MethodSource,
    FunctionSource,
)


def _load_closures(file: ModuleSource,
                   source: t.Union[MethodSource, FunctionSource],
                   closures: list['MetricItem']):
    for closure in closures:
        func = FunctionSource(file,
                              closure.name,
                              lineno=closure.lineno,
                              endline=closure.endline,
                              complexity=closure.complexity)

        source.closures.append(func)
        _load_closures(file, func, closure.closures)


@dataclasses.dataclass(kw_only=True)
class MetricItem:
    type: str
    name: str
    lineno: int = 0
    endline: int = 0
    complexity: int = 0
    class_name: t.Optional[str] = None
    methods: list['MetricItem'] = dataclasses.field(default_factory=list)
    closures: list['MetricItem'] = dataclasses.field(default_factory=list)


class Loader(metaclass=abc.ABCMeta):
    __lang__ = 'Unknown'
    __ignore_dirs__: list[str] = []
    __comment_line_prefixes__: list[str] = []

    def __init__(self, root: str = '.', *,
                 class_loc_from_methods: bool = False):
        self._root = root

        self._class_loc_from_methods = class_loc_from_methods

        self._packages: dict[str, PackageSource] = {}
        self._files: dict[str, ModuleSource] = {}
        self._classes: dict[str, ClassSource] = {}
        self._methods: dict[str, MethodSource] = {}
        self._functions: dict[str, FunctionSource] = {}

    @property
    def root(self):
        return self._root

    @cached_property
    def ignores(self) -> list[str]:
        return list(set(self.__ignore_dirs__ + utils.ignore_dirs(self._root)))

    @abc.abstractmethod
    def extract_metrics(self) -> dict[str, list[MetricItem]]:
        pass

    def _should_exclude_file(self, filepath: str) -> bool:
        path = Path(filepath).resolve()

        for ignore in self.ignores:
            ex_dir = Path(ignore).resolve()
            if path == ex_dir or ex_dir in path.parents:
                return True

        return False

    def __load_file(self, filepath: str, metrics: list[MetricItem]):
        if (file := self._files.get(filepath)) is None:
            self._files[filepath] = file = ModuleSource(filepath)

            package_path = os.path.dirname(filepath)

            if (package := self._packages.get(package_path)) is None:
                self._packages[package_path] = package = PackageSource(package_path)

            package.modules.append(file)

        for item in metrics:
            if item.type == "class":
                key = f"{filepath}:{item.name}"
                self._classes[key] = ClassSource(file,
                                                 item.name,
                                                 lineno=item.lineno,
                                                 endline=item.endline,
                                                 complexity=item.complexity,
                                                 loc_from_methods=self._class_loc_from_methods,
                                                 comment_line_prefixes=self.__comment_line_prefixes__)
                file.classes.append(self._classes[key])
                self.__load_file(filepath, item.methods)
                continue
            elif item.type == "method":
                class_key = f"{filepath}:{item.class_name}"
                class_item = self._classes[class_key]

                key = f"{filepath}:{class_item.name}.{item.name}"
                self._methods[key] = MethodSource(file,
                                                  class_item,
                                                  item.name,
                                                  lineno=item.lineno,
                                                  endline=item.endline,
                                                  complexity=item.complexity,
                                                  comment_line_prefixes=self.__comment_line_prefixes__)
                file.methods.append(self._methods[key])
                class_item.methods.append(self._methods[key])
                _load_closures(file, self._methods[key], item.closures)
                continue
            elif item.type == "function":
                key = f"{filepath}:{item.name}"
                self._functions[key] = FunctionSource(file,
                                                      item.name,
                                                      lineno=item.lineno,
                                                      endline=item.endline,
                                                      complexity=item.complexity,
                                                      comment_line_prefixes=self.__comment_line_prefixes__)
                file.functions.append(self._functions[key])
                _load_closures(file, self._functions[key], item.closures)
                continue

            raise ValueError(f"Unknown metric type: {item.type}")

    def load(self) -> Sources:
        sources = Sources(self.root, self.__lang__)
        metrics = self.extract_metrics()

        for filepath in metrics:
            self.__load_file(filepath, metrics[filepath])

        sources.packages.extend(self._packages.values())
        sources.modules.extend(self._files.values())
        sources.classes.extend(self._classes.values())
        sources.methods.extend(self._methods.values())
        sources.functions.extend(self._functions.values())

        self._packages = {}
        self._files = {}
        self._classes = {}
        self._methods = {}
        self._functions = {}

        return sources
