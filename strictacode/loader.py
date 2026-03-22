import abc
import dataclasses
import os
from enum import Enum
from functools import cached_property
from pathlib import Path

from . import utils
from .source import (
    ClassSource,
    FunctionSource,
    MethodSource,
    ModuleSource,
    PackageSource,
    Sources,
)


def _load_closures(file: ModuleSource,
                   source: MethodSource | FunctionSource,
                   closures: list['FileItem']):
    for closure in closures:
        func = FunctionSource(file,
                              closure.name,
                              lineno=closure.lineno,
                              endline=closure.endline,
                              complexity=closure.complexity)

        source.closures.append(func)
        _load_closures(file, func, closure.closures)


class FileItemTypes(str, Enum):
    CLASS = "class"
    METHOD = "method"
    FUNCTION = "function"


@dataclasses.dataclass(kw_only=True)
class FileItem:
    type: str
    name: str
    lineno: int = 0
    endline: int = 0
    complexity: int = 0
    class_name: str | None = None
    methods: list['FileItem'] = dataclasses.field(default_factory=list)
    closures: list['FileItem'] = dataclasses.field(default_factory=list)


class Loader(metaclass=abc.ABCMeta):
    __lang__ = 'Unknown'
    __ignore_dirs__: list[str] = []
    __comment_line_prefixes__: list[str] = []
    __comment_code_blocks__: list[tuple[str, str]] = []

    def __init__(self, root: str = '.', *,
                 class_loc_from_methods: bool = False,
                 include_patterns: list[str] | None = None,
                 exclude_patterns: list[str] | None = None):
        self._root = root

        self._include_patterns = include_patterns or []
        self._exclude_patterns = exclude_patterns or []
        self._class_loc_from_methods = class_loc_from_methods

        self.__sources = Sources(self.root, self.__lang__)

        self.__packages: dict[str, PackageSource] = {}
        self.__modules: dict[str, ModuleSource] = {}
        self.__classes: dict[str, ClassSource] = {}
        self.__methods: dict[str, MethodSource] = {}
        self.__functions: dict[str, FunctionSource] = {}

    @property
    def root(self):
        return self._root

    @property
    def sources(self) -> Sources:
        return self.__sources

    @cached_property
    def ignores(self) -> list[str]:
        return list(set(self.__ignore_dirs__ + utils.ignore_dirs(self._root) + self._exclude_patterns))

    @abc.abstractmethod
    def collect(self) -> dict[str, list[FileItem]]:
        pass

    @abc.abstractmethod
    def build(self):
        pass

    def _should_exclude_file(self, filepath: str) -> bool:
        path = Path(filepath).resolve()

        included = False if self._include_patterns else True

        for include in self._include_patterns:
            inc_dir = Path(include).resolve()
            if path == inc_dir or inc_dir in path.parents:
                included = True

        if not included:
            return True

        for ignore in self.ignores:
            ex_dir = Path(ignore).resolve()
            if path == ex_dir or ex_dir in path.parents:
                return True

        return False

    def __load_items_from_file(self, filepath: str, items: list[FileItem]):
        if (module := self.__modules.get(filepath)) is None:
            self.__modules[filepath] = module = ModuleSource(filepath)

            package_path = os.path.dirname(filepath)

            if (package := self.__packages.get(package_path)) is None:
                self.__packages[package_path] = package = PackageSource(package_path)

            package.modules.append(module)

        for item in items:
            if item.type == FileItemTypes.CLASS:
                key = f"{filepath}:{item.name}"
                self.__classes[key] = ClassSource(module,
                                                  item.name,
                                                  lineno=item.lineno,
                                                  endline=item.endline,
                                                  complexity=item.complexity,
                                                  loc_from_methods=self._class_loc_from_methods,
                                                  comment_line_prefixes=self.__comment_line_prefixes__)
                module.classes.append(self.__classes[key])
                self.__load_items_from_file(filepath, item.methods)
                continue

            if item.type == FileItemTypes.METHOD:
                class_key = f"{filepath}:{item.class_name}"
                class_item = self.__classes[class_key]

                key = f"{filepath}:{class_item.name}.{item.name}"
                self.__methods[key] = MethodSource(module,
                                                   class_item,
                                                   item.name,
                                                   lineno=item.lineno,
                                                   endline=item.endline,
                                                   complexity=item.complexity,
                                                   comment_line_prefixes=self.__comment_line_prefixes__)
                module.methods.append(self.__methods[key])
                class_item.methods.append(self.__methods[key])
                _load_closures(module, self.__methods[key], item.closures)
                continue

            if item.type == FileItemTypes.FUNCTION:
                key = f"{filepath}:{item.name}"
                self.__functions[key] = FunctionSource(module,
                                                       item.name,
                                                       lineno=item.lineno,
                                                       endline=item.endline,
                                                       complexity=item.complexity,
                                                       comment_line_prefixes=self.__comment_line_prefixes__)
                module.functions.append(self.__functions[key])
                _load_closures(module, self.__functions[key], item.closures)
                continue

            raise ValueError(f"Unknown metric type: {item.type}")

    def load(self) -> Sources:
        file_to_items = self.collect()

        for filepath, items in file_to_items.items():
            if self._should_exclude_file(filepath):
                continue

            self.__load_items_from_file(filepath, items)

        self.__sources.packages.extend(self.__packages.values())
        self.__sources.modules.extend(self.__modules.values())
        self.__sources.classes.extend(self.__classes.values())
        self.__sources.methods.extend(self.__methods.values())
        self.__sources.functions.extend(self.__functions.values())

        self.__packages = {}
        self.__modules = {}
        self.__classes = {}
        self.__methods = {}
        self.__functions = {}

        self.build()

        self.__sources.compile()

        return self.__sources
