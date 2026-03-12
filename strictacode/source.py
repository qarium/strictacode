import os
import typing as t
from enum import Enum
from functools import cached_property
from dataclasses import dataclass, field

from . import utils
from .graph import DiGraph
from .calc import score, Complexity
from .calc.pressure import refactoring
from .calc.pressure import overengineering


@dataclass(kw_only=True)
class Status:
    score: 'score.Metric' = score.Metric(value=0)
    reasons: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def name(self) -> Enum:
        return self.score.status


class Sources:
    def __init__(self, path: str, lang: str):
        self._path = path
        self._lang = lang

        self._status: Status = Status()
        self._graph: DiGraph = DiGraph()

        self._packages: list[PackageSource] = []
        self._modules: list[ModuleSource] = []
        self._classes: list[ClassSource] = []
        self._methods: list[MethodSource] = []
        self._functions: list[FunctionSource] = []
        self._overengineering_pressure: t.Optional[overengineering.Metric] = None

    def __repr__(self):
        return  f"<{self.__class__.__name__}: {self.path} " \
                f"loc={self.loc} packages={len(self.packages)} modules={len(self.modules)}>"

    @property
    def path(self):
        return self._path

    @property
    def lang(self):
        return self._lang

    @property
    def status(self):
        return self._status

    @property
    def graph(self):
        return self._graph

    @property
    def packages(self):
        return self._packages

    @property
    def modules(self):
        return self._modules

    @property
    def classes(self):
        return self._classes

    @property
    def methods(self):
        return self._methods

    @property
    def functions(self):
        return self._functions

    @property
    def loc(self):
        return sum((i.loc for i in self.modules))

    @cached_property
    def complexity(self) -> Complexity:
        score = sum((i.complexity.score for i in self.modules))
        children = [i.complexity for i in self.modules]
        return Complexity(score, loc=self.loc, children=children)

    @cached_property
    def refactoring_pressure(self) -> refactoring.Metric:
        return refactoring.calculate(
            refactoring.Data(
                loc=self.loc,
                max_complexity=self.complexity.stat.max,
                p90_complexity=self.complexity.stat.p90,
                complexity_density=self.complexity.density,
            ),
            children=[i.refactoring_pressure for i in self.modules],
        )

    @property
    def overengineering_pressure(self) -> overengineering.Metric:
        if self._overengineering_pressure is None:
            raise ValueError('Overengineering_pressure not set')
        return self._overengineering_pressure

    def _compile_overengineering_pressure(self):
        op = overengineering.calculate(self.graph)

        for cls_score in op.classes:
            for cls in self.classes:
                if cls.name == cls_score.name and cls.module.path == cls_score.path:
                    cls.overengineering_pressure = overengineering.Metric(int(round(cls_score.value, 0)))
                    break

        for mod_score in op.modules:
            for module in self.modules:
                if module.name == mod_score.name and module.path == mod_score.path:
                    module.overengineering_pressure = overengineering.Metric(int(round(mod_score.value, 0)),
                                                                             children=[
                                                                                 i.overengineering_pressure
                                                                                 for i in self.classes
                                                                             ])
                    break

        self._overengineering_pressure = overengineering.Metric(op.score,
                                                                children=[
                                                                    i.overengineering_pressure
                                                                    for i in self.modules
                                                                ])

    def compile(self):
        self._compile_overengineering_pressure()

        self._status.score = score.calculate(self.refactoring_pressure.score,
                                             self.overengineering_pressure.score,
                                             self.complexity.density)

        for package in self.packages:
            package.compile()
        for module in self.modules:
            module.compile()
        for cls in self.classes:
            cls.compile()
        for method in self.methods:
            method.compile()
        for function in self.functions:
            function.compile()


class PackageSource:
    def __init__(self, path: str):
        self._path = path

        self._status: Status = Status()

        self._modules: list[ModuleSource] = []

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.path} " \
                f"loc={self.loc} modules={len(self.modules)}>"

    @property
    def path(self):
        return self._path

    @property
    def status(self):
        return self._status

    @property
    def modules(self):
        return self._modules

    @property
    def name(self):
        return os.path.basename(self._path) or "<root>"

    @property
    def loc(self):
        return sum((i.loc for i in self.modules))

    @cached_property
    def complexity(self) -> Complexity:
        score = sum((i.complexity.score for i in self.modules))
        children = [i.complexity for i in self.modules]
        return Complexity(score, loc=self.loc, children=children)

    @cached_property
    def refactoring_pressure(self) -> refactoring.Metric:
        return refactoring.calculate(
            refactoring.Data(
                loc=self.loc,
                max_complexity=self.complexity.stat.max,
                p90_complexity=self.complexity.stat.p90,
                complexity_density=self.complexity.density,
            ),
            children=[i.refactoring_pressure for i in self.modules],
        )

    @cached_property
    def overengineering_pressure(self) -> overengineering.Metric:
        module_scores = [i.overengineering_pressure for i in self.modules]
        score = sum(i.score for i in module_scores)
        return overengineering.Metric(score, children=module_scores)

    def compile(self):
        self.status.score = score.calculate(self.refactoring_pressure.score,
                                            self.overengineering_pressure.score,
                                            self.complexity.density)


class ModuleSource:
    def __init__(self, path: str, *,
                 comment_line_prefixes: t.Optional[list[str]] = None,
                 comment_code_blocks: t.Optional[list[tuple[str, str]]] = None):
        self._path = path

        self._loc = utils.lines_of_code(path,
                                        ignore_blocks=comment_code_blocks,
                                        ignore_prefixes=comment_line_prefixes)

        self._status: Status = Status()

        self._classes: list[ClassSource] = []
        self._methods: list[MethodSource] = []
        self._functions: list[FunctionSource] = []
        self._overengineering_pressure: t.Optional[overengineering.Metric] = None

    def __repr__(self):
        return  f"<{self.__class__.__name__}: {self.path} " \
                f"loc={self.loc} classes={len(self.classes)} functions={len(self.functions)}>"

    @property
    def path(self):
        return self._path

    @property
    def loc(self):
        return self._loc

    @property
    def status(self):
        return self._status

    @property
    def name(self):
        return os.path.basename(self._path)

    @property
    def classes(self):
        return self._classes

    @property
    def methods(self):
        return self._methods

    @property
    def functions(self):
        return self._functions

    @cached_property
    def content(self):
        with open(self._path, 'r', encoding='utf-8') as f:
            return f.read()

    @cached_property
    def complexity(self) -> Complexity:
        score = sum([
            sum((i.complexity.score for i in self.classes)),
            sum((i.complexity.score for i in self.functions)),
        ])
        children = [i.complexity for i in self.classes] + [i.complexity for i in self.functions]
        return Complexity(score, loc=self.loc, children=children)

    @cached_property
    def refactoring_pressure(self) -> refactoring.Metric:
        return refactoring.calculate(
            refactoring.Data(
                loc=self.loc,
                max_complexity=self.complexity.stat.max,
                p90_complexity=self.complexity.stat.p90,
                complexity_density=self.complexity.density,
            ),
        )

    @property
    def overengineering_pressure(self) -> overengineering.Metric:
        if self._overengineering_pressure is None:
            return overengineering.Metric(0)
        return self._overengineering_pressure

    @overengineering_pressure.setter
    def overengineering_pressure(self, value):
        self._overengineering_pressure = value

    def compile(self):
        self.status.score = score.calculate(self.refactoring_pressure.score,
                                            self.overengineering_pressure.score,
                                            self.complexity.density)


class ClassSource:
    def __init__(self, module: ModuleSource, name: str, *,
                 lineno: int = 0,
                 endline: int = 0,
                 complexity: int = 0,
                 loc_from_methods: bool = False,
                 comment_line_prefixes: t.Optional[list[str]] = None,
                 comment_code_blocks: t.Optional[list[tuple[str, str]]] = None):
        self._module = module
        self._name = name
        self._lineno = lineno
        self._endline = endline
        self._complexity = complexity

        self._loc = utils.lines_of_code(module.path,
                                        lineno=lineno,
                                        endline=endline,
                                        ignore_blocks=comment_code_blocks,
                                        ignore_prefixes=comment_line_prefixes)

        self._loc_from_methods = loc_from_methods

        self._status: Status = Status()

        self._methods: list[MethodSource] = []
        self._overengineering_pressure: t.Optional[overengineering.Metric] = None

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.name} methods={len(self.methods)}>'

    @property
    def module(self):
        return self._module

    @property
    def name(self):
        return self._name

    @property
    def lineno(self):
        return self._lineno

    @property
    def endline(self):
        return self._endline

    @property
    def loc(self):
        if self._loc_from_methods:
            return sum((i.loc for i in self.methods))
        return self._loc

    @property
    def status(self):
        return self._status

    @property
    def methods(self):
        return self._methods

    @cached_property
    def content(self) -> str:
        return utils.source_content(self.module.path, self.lineno, self.endline)

    @cached_property
    def complexity(self) -> Complexity:
        children = [i.complexity for i in self.methods]
        return Complexity(self._complexity, loc=self.loc, children=children)

    @property
    def overengineering_pressure(self) -> overengineering.Metric:
        if self._overengineering_pressure is None:
            return overengineering.Metric(0)
        return self._overengineering_pressure

    @overengineering_pressure.setter
    def overengineering_pressure(self, value):
        self._overengineering_pressure = value

    def compile(self):
        self.status.score = score.calculate(self.module.refactoring_pressure.score,
                                            self.overengineering_pressure.score,
                                            self.complexity.density,
                                            rp_weight=0.15,
                                            oe_weight=0.35,
                                            density_weight=0.5)


class MethodSource:
    def __init__(self, module: ModuleSource, cls: ClassSource, name: str, *,
                 lineno: int = 0,
                 endline: int = 0,
                 complexity: int = 0,
                 comment_line_prefixes: t.Optional[list[str]] = None,
                 comment_code_blocks: t.Optional[list[tuple[str, str]]] = None):
        self._module = module
        self._cls = cls
        self._name = name
        self._lineno = lineno
        self._endline = endline
        self._complexity = complexity

        self._loc = utils.lines_of_code(module.path,
                                        lineno=lineno,
                                        endline=endline,
                                        ignore_blocks=comment_code_blocks,
                                        ignore_prefixes=comment_line_prefixes)

        self._status: Status = Status()

        self._closures: list[FunctionSource] = []

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.name} class={self.cls.name} loc={self.loc}>'

    @property
    def module(self):
        return self._module

    @property
    def cls(self):
        return self._cls

    @property
    def name(self):
        return self._name

    @property
    def lineno(self):
        return self._lineno

    @property
    def endline(self):
        return self._endline

    @property
    def loc(self):
        return self._loc

    @property
    def status(self):
        return self._status

    @property
    def closures(self):
        return self._closures

    @cached_property
    def content(self) -> str:
        return utils.source_content(self.module.path, self.lineno, self.endline)

    @cached_property
    def complexity(self) -> Complexity:
        children = [i.complexity for i in self.closures]
        return Complexity(self._complexity, loc=self.loc, total_sum=True, children=children)

    def compile(self):
        self.status.score = score.calculate(self.module.refactoring_pressure.score,
                                            self.cls.overengineering_pressure.score,
                                            self.complexity.density,
                                            rp_weight=0.1,
                                            oe_weight=0.3,
                                            density_weight=0.6)


class FunctionSource:
    def __init__(self, module: ModuleSource, name, *,
                 lineno: int = 0,
                 endline: int = 0,
                 complexity: int = 0,
                 comment_line_prefixes: t.Optional[list[str]] = None,
                 comment_code_blocks: t.Optional[list[tuple[str, str]]] = None):
        self._module = module
        self._name = name
        self._lineno = lineno
        self._endline = endline
        self._complexity = complexity

        self._loc = utils.lines_of_code(module.path,
                                        lineno=lineno,
                                        endline=endline,
                                        ignore_blocks=comment_code_blocks,
                                        ignore_prefixes=comment_line_prefixes)

        self._status: Status = Status()

        self._closures: list[FunctionSource] = []

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.name} loc={self.loc}>'

    @property
    def module(self):
        return self._module

    @property
    def name(self):
        return self._name

    @property
    def lineno(self):
        return self._lineno

    @property
    def endline(self):
        return self._endline

    @property
    def loc(self):
        return self._loc

    @property
    def status(self):
        return self._status

    @property
    def closures(self):
        return self._closures

    @cached_property
    def content(self):
        return utils.source_content(self.module.path, self.lineno, self.endline)

    @cached_property
    def complexity(self):
        children = [i.complexity for i in self.closures]
        return Complexity(self._complexity, loc=self.loc, total_sum=True, children=children)

    def compile(self):
        self.status.score = score.calculate(self.module.refactoring_pressure.score,
                                            self.module.overengineering_pressure.score,
                                            self.complexity.density,
                                            rp_weight=0.2,
                                            oe_weight=0.2,
                                            density_weight=0.6)
