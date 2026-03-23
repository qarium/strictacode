import abc
import json

from .. import utils
from ..source import Sources


class BaseResultReporter(metaclass=abc.ABCMeta):
    def __init__(
        self,
        sources: Sources,
        *,
        short: bool = False,
        details: bool = False,
        top_packages: int = 3,
        top_modules: int = 5,
        top_classes: int = 10,
        top_methods: int = 15,
        top_functions: int = 20,
        output: str | None = None,
    ):
        self._sources = sources

        self._short = short
        self._details = details

        self._top_packages = []
        self._top_modules = []
        self._top_classes = []
        self._top_methods = []
        self._top_functions = []

        self._output = output

        self._make_top_packages(top_packages)
        self._make_top_modules(top_modules)
        self._make_top_classes(top_classes)
        self._make_top_methods(top_methods)
        self._make_top_functions(top_functions)

    def _make_top_packages(self, top: int):
        packages_by_score = sorted(self._sources.packages, key=lambda x: x.status.score.value, reverse=True)
        packages_by_complexity = sorted(self._sources.packages, key=lambda x: x.complexity.score, reverse=True)
        packages_by_density = sorted(self._sources.packages, key=lambda x: x.complexity.density, reverse=True)
        packages_by_rp = sorted(self._sources.packages, key=lambda x: x.refactoring_pressure.score, reverse=True)
        packages_by_op = sorted(self._sources.packages, key=lambda x: x.overengineering_pressure.score, reverse=True)

        self._top_packages = []

        for package in packages_by_score[:top]:
            self._top_packages.append(package)
        for package in packages_by_complexity[:top]:
            if package not in self._top_packages:
                self._top_packages.append(package)
        for package in packages_by_density[:top]:
            if package not in self._top_packages:
                self._top_packages.append(package)
        for package in packages_by_rp[:top]:
            if package not in self._top_packages:
                self._top_packages.append(package)
        for package in packages_by_op[:top]:
            if package not in self._top_packages:
                self._top_packages.append(package)

        self._top_packages = sorted(self._top_packages, key=lambda x: x.status.score.value, reverse=True)[:top]

    def _make_top_modules(self, top: int):
        modules_by_score = sorted(self._sources.modules, key=lambda x: x.status.score.value, reverse=True)
        modules_by_complexity = sorted(self._sources.modules, key=lambda x: x.complexity.score, reverse=True)
        modules_by_density = sorted(self._sources.modules, key=lambda x: x.complexity.density, reverse=True)
        modules_by_rp = sorted(self._sources.modules, key=lambda x: x.refactoring_pressure.score, reverse=True)
        modules_by_op = sorted(self._sources.modules, key=lambda x: x.overengineering_pressure.score, reverse=True)

        self._top_modules = []

        for package in modules_by_score[:top]:
            self._top_modules.append(package)
        for package in modules_by_complexity[:top]:
            if package not in self._top_modules:
                self._top_modules.append(package)
        for package in modules_by_density[:top]:
            if package not in self._top_modules:
                self._top_modules.append(package)
        for package in modules_by_rp[:top]:
            if package not in self._top_modules:
                self._top_modules.append(package)
        for package in modules_by_op[:top]:
            if package not in self._top_modules:
                self._top_modules.append(package)

        self._top_modules = sorted(self._top_modules, key=lambda x: x.status.score.value, reverse=True)[:top]

    def _make_top_classes(self, top: int):
        classes_by_score = sorted(self._sources.classes, key=lambda x: x.status.score.value, reverse=True)
        classes_by_complexity = sorted(self._sources.classes, key=lambda x: x.complexity.score, reverse=True)
        classes_by_density = sorted(self._sources.classes, key=lambda x: x.complexity.density, reverse=True)
        classes_by_op = sorted(self._sources.classes, key=lambda x: x.overengineering_pressure.score, reverse=True)

        self._top_classes = []

        for cls in classes_by_score[:top]:
            self._top_classes.append(cls)
        for cls in classes_by_complexity[:top]:
            if cls not in self._top_classes:
                self._top_classes.append(cls)
        for cls in classes_by_density[:top]:
            if cls not in self._top_classes:
                self._top_classes.append(cls)
        for cls in classes_by_op[:top]:
            if cls not in self._top_classes:
                self._top_classes.append(cls)

        self._top_classes = sorted(self._top_classes, key=lambda x: x.status.score.value, reverse=True)[:top]

    def _make_top_methods(self, top: int):
        methods_by_score = sorted(self._sources.methods, key=lambda x: x.status.score.value, reverse=True)
        methods_by_complexity = sorted(self._sources.methods, key=lambda x: x.complexity.score, reverse=True)
        methods_by_density = sorted(self._sources.methods, key=lambda x: x.complexity.density, reverse=True)

        self._top_methods = []

        for method in methods_by_score[:top]:
            self._top_methods.append(method)
        for method in methods_by_complexity[:top]:
            if method not in self._top_methods:
                self._top_methods.append(method)
        for method in methods_by_density[:top]:
            if method not in self._top_methods:
                self._top_methods.append(method)

        self._top_methods = sorted(self._top_methods, key=lambda x: x.status.score.value, reverse=True)[:top]

    def _make_top_functions(self, top: int):
        functions_by_score = sorted(self._sources.functions, key=lambda x: x.status.score.value, reverse=True)
        functions_by_complexity = sorted(self._sources.functions, key=lambda x: x.complexity.score, reverse=True)
        functions_by_density = sorted(self._sources.functions, key=lambda x: x.complexity.density, reverse=True)

        self._top_functions = []

        for function in functions_by_score[:top]:
            self._top_functions.append(function)
        for function in functions_by_complexity[:top]:
            if function not in self._top_functions:
                self._top_functions.append(function)
        for function in functions_by_density[:top]:
            if function not in self._top_functions:
                self._top_functions.append(function)

        self._top_functions = sorted(self._top_functions, key=lambda x: x.status.score.value, reverse=True)[:top]

    @abc.abstractmethod
    def _report(self) -> None:
        pass

    def report(self) -> None:
        if self._output is not None:
            with utils.redirect_output(self._output):
                return self._report()
        return self._report()


class TextResultReporter(BaseResultReporter):
    def project_report(self):
        print("Project:")
        print("  * lang:", self._sources.lang)
        print("  * loc:", self._sources.loc)
        print("  * packages:", len(self._sources.packages))
        print("  * modules:", len(self._sources.modules))
        print("  * classes:", len(self._sources.classes))
        print("  * methods:", len(self._sources.methods))
        print("  * functions:", len(self._sources.functions))
        print("  * status:")
        print("    - name:", self._sources.status.name.value)
        print("    - score:", self._sources.status.score.value)
        if self._sources.status.reasons:
            print("    - reasons:")
            for reason in self._sources.status.reasons:
                print(f"      + {reason}")
        if self._sources.status.suggestions:
            print("    - suggestions:")
            for suggestion in self._sources.status.suggestions:
                print(f"      + {suggestion}")
        print("  * overengineering_pressure:")
        print("    - score:", self._sources.overengineering_pressure.score)
        print("    - stat(modules):")
        print("      + avg:", self._sources.overengineering_pressure.stat.avg)
        print("      + min:", self._sources.overengineering_pressure.stat.min)
        print("      + max:", self._sources.overengineering_pressure.stat.max)
        print("      + p50:", self._sources.overengineering_pressure.stat.p50)
        print("      + p90:", self._sources.overengineering_pressure.stat.p90)
        print("  * refactoring_pressure:")
        print("    - score:", self._sources.refactoring_pressure.score)
        print("    - stat(modules):")
        print("      + avg:", self._sources.refactoring_pressure.stat.avg)
        print("      + min:", self._sources.refactoring_pressure.stat.min)
        print("      + max:", self._sources.refactoring_pressure.stat.max)
        print("      + p50:", self._sources.refactoring_pressure.stat.p50)
        print("      + p90:", self._sources.refactoring_pressure.stat.p90)
        print("  * complexity:")
        print("    - score:", self._sources.complexity.score)
        print("    - density:", self._sources.complexity.density)
        print("    - stat(modules):")
        print("      + avg:", self._sources.complexity.stat.avg)
        print("      + min:", self._sources.complexity.stat.min)
        print("      + max:", self._sources.complexity.stat.max)
        print("      + p50:", self._sources.complexity.stat.p50)
        print("      + p90:", self._sources.complexity.stat.p90)

    def packages_report(self):
        if self._top_packages:
            print()
            print("---")
            print()
            print("Packages:")
            for package in self._top_packages:
                print(f"  * {package.name}:")
                print("    - dir:", package.path)
                print("    - loc:", package.loc)
                print("    - modules:", len(package.modules))
                print("    - status:")
                print("      + name:", package.status.name.value)
                print("      + score:", package.status.score.value)
                if package.status.reasons:
                    print("      + reasons:")
                    for reason in package.status.reasons:
                        print(f"        - {reason}")
                if package.status.suggestions:
                    print("      + suggestions:")
                    for suggestion in package.status.suggestions:
                        print(f"        - {suggestion}")
                print("    - overengineering_pressure:")
                print("      + score:", package.overengineering_pressure.score)
                print("      + stat(modules):")
                print("        - avg:", package.overengineering_pressure.stat.avg)
                print("        - min:", package.overengineering_pressure.stat.min)
                print("        - max:", package.overengineering_pressure.stat.max)
                print("        - p50:", package.overengineering_pressure.stat.p50)
                print("        - p90:", package.overengineering_pressure.stat.p90)
                print("    - refactoring_pressure:")
                print("      + score:", package.refactoring_pressure.score)
                print("      + stat(modules):")
                print("        - avg:", package.refactoring_pressure.stat.avg)
                print("        - min:", package.refactoring_pressure.stat.min)
                print("        - max:", package.refactoring_pressure.stat.max)
                print("        - p50:", package.refactoring_pressure.stat.p50)
                print("        - p90:", package.refactoring_pressure.stat.p90)
                print("    - complexity:")
                print("      + score:", package.complexity.score)
                print("      + density:", package.complexity.density)
                print("      + stat(modules):")
                print("        - avg:", package.complexity.stat.avg)
                print("        - min:", package.complexity.stat.min)
                print("        - max:", package.complexity.stat.max)
                print("        - p50:", package.complexity.stat.p50)
                print("        - p90:", package.complexity.stat.p90)

    def modules_report(self):
        if self._top_modules:
            print()
            print("---")
            print()
            print("Modules:")
            for module in self._top_modules:
                print(f"  * {module.name}:")
                print("    - file:", module.path)
                print("    - loc:", module.loc)
                print("    - classes:", len(module.classes))
                print("    - functions:", len(module.functions))
                print("    - status:")
                print("      + name:", module.status.name.value)
                print("      + score:", module.status.score.value)
                if module.status.reasons:
                    print("      + reasons:")
                    for reason in module.status.reasons:
                        print(f"        - {reason}")
                if module.status.suggestions:
                    print("      + suggestions:")
                    for suggestion in module.status.suggestions:
                        print(f"        - {suggestion}")
                print("    - overengineering_pressure:")
                print("      + score:", module.overengineering_pressure.score)
                print("      + stat(classes):")
                print("        - avg:", module.overengineering_pressure.stat.avg)
                print("        - min:", module.overengineering_pressure.stat.min)
                print("        - max:", module.overengineering_pressure.stat.max)
                print("        - p50:", module.overengineering_pressure.stat.p50)
                print("        - p90:", module.overengineering_pressure.stat.p90)
                print("    - refactoring_pressure:")
                print("      + score:", module.refactoring_pressure.score)
                print("    - complexity:")
                print("      + score:", module.complexity.score)
                print("      + density:", module.complexity.density)
                print("      + stat(classes+functions):")
                print("        - avg:", module.complexity.stat.avg)
                print("        - min:", module.complexity.stat.min)
                print("        - max:", module.complexity.stat.max)
                print("        - p50:", module.complexity.stat.p50)
                print("        - p90:", module.complexity.stat.p90)

    def classes_report(self):
        if self._top_classes:
            print()
            print("---")
            print()
            print("Classes:")
            for cls in self._top_classes:
                print(f"  * {cls.name}:")
                print("    - file:", cls.module.path)
                print("    - loc:", cls.loc)
                print("    - methods:", len(cls.methods))
                print("    - status:")
                print("      + name:", cls.status.name.value)
                print("      + score:", cls.status.score.value)
                if cls.status.reasons:
                    print("      + reasons:")
                    for reason in cls.status.reasons:
                        print(f"        - {reason}")
                if cls.status.suggestions:
                    print("      + suggestions:")
                    for suggestion in cls.status.suggestions:
                        print(f"        - {suggestion}")
                print("    - overengineering_pressure:")
                print("      + score:", cls.overengineering_pressure.score)
                print("    - complexity:")
                print("      + score:", cls.complexity.score)
                print("      + density:", cls.complexity.density)
                print("      + stat(methods):")
                print("        - avg:", cls.complexity.stat.avg)
                print("        - min:", cls.complexity.stat.min)
                print("        - max:", cls.complexity.stat.max)
                print("        - p50:", cls.complexity.stat.p50)
                print("        - p90:", cls.complexity.stat.p90)

    def methods_report(self):
        if self._top_methods:
            print()
            print("---")
            print()
            print("Methods:")
            for method in self._top_methods:
                print(f"  * {method.name}:")
                print("    - file:", method.module.path)
                print("    - class:", method.cls.name)
                print("    - loc:", method.loc)
                print("    - closures:", len(method.closures))
                print("    - status:")
                print("      + name:", method.status.name.value)
                print("      + score:", method.status.score.value)
                if method.status.reasons:
                    print("      - reasons:")
                    for reason in method.status.reasons:
                        print(f"        + {reason}")
                if method.status.suggestions:
                    print("      - suggestions:")
                    for suggestion in method.status.suggestions:
                        print(f"        + {suggestion}")
                print("    - complexity:")
                print("      + score:", method.complexity.score)
                print("      + total:", method.complexity.total)
                print("      + density:", method.complexity.density)
                print("      + stat(closures):")
                print("        - avg:", method.complexity.stat.avg)
                print("        - min:", method.complexity.stat.min)
                print("        - max:", method.complexity.stat.max)
                print("        - p50:", method.complexity.stat.p50)
                print("        - p90:", method.complexity.stat.p90)

    def functions_report(self):
        if self._top_functions:
            print()
            print("---")
            print()
            print("Functions:")
            for func in self._top_functions:
                print(f"  * {func.name}:")
                print("    - file:", func.module.path)
                print("    - loc:", func.loc)
                print("    - closures:", len(func.closures))
                print("    - status:")
                print("      + name:", func.status.name.value)
                print("      + score:", func.status.score.value)
                if func.status.reasons:
                    print("      - reasons:")
                    for reason in func.status.reasons:
                        print(f"        + {reason}")
                if func.status.suggestions:
                    print("      - suggestions:")
                    for suggestion in func.status.suggestions:
                        print(f"        + {suggestion}")
                print("    - complexity:")
                print("      + score:", func.complexity.score)
                print("      + total:", func.complexity.total)
                print("      + density:", func.complexity.density)
                print("      + stat(closures):")
                print("        - avg:", func.complexity.stat.avg)
                print("        - min:", func.complexity.stat.min)
                print("        - max:", func.complexity.stat.max)
                print("        - p50:", func.complexity.stat.p50)
                print("        - p90:", func.complexity.stat.p90)

    def _report(self) -> None:
        self.project_report()

        if self._short:
            return

        self.packages_report()
        self.modules_report()

        if self._details:
            self.classes_report()
            self.methods_report()
            self.functions_report()


class JsonResultReporter(BaseResultReporter):
    def make_packages_report(self, data: dict):
        data["packages"] = []

        if self._top_packages:
            for package in self._top_packages:
                data["packages"].append(
                    {
                        "name": package.name,
                        "dir": package.path,
                        "loc": package.loc,
                        "modules": len(package.modules),
                        "status": {
                            "name": package.status.name.value,
                            "score": package.status.score.value,
                            "reasons": package.status.reasons,
                            "suggestions": package.status.suggestions,
                        },
                        "overengineering_pressure": {
                            "score": package.overengineering_pressure.score,
                        },
                        "refactoring_pressure": {
                            "score": package.refactoring_pressure.score,
                            "stat(modules)": {
                                "avg": package.refactoring_pressure.stat.avg,
                                "min": package.refactoring_pressure.stat.min,
                                "max": package.refactoring_pressure.stat.max,
                                "p50": package.refactoring_pressure.stat.p50,
                                "p90": package.refactoring_pressure.stat.p90,
                            },
                        },
                        "complexity": {
                            "score": package.complexity.score,
                            "density": package.complexity.density,
                            "stat(modules)": {
                                "avg": package.complexity.stat.avg,
                                "min": package.complexity.stat.min,
                                "max": package.complexity.stat.max,
                                "p50": package.complexity.stat.p50,
                                "p90": package.complexity.stat.p90,
                            },
                        },
                    }
                )

    def make_modules_report(self, data: dict):
        data["modules"] = []

        if self._top_modules:
            for module in self._top_modules:
                data["modules"].append(
                    {
                        "name": module.name,
                        "file": module.path,
                        "loc": module.loc,
                        "classes": len(module.classes),
                        "functions": len(module.functions),
                        "status": {
                            "name": module.status.name.value,
                            "score": module.status.score.value,
                            "reasons": module.status.reasons,
                            "suggestions": module.status.suggestions,
                        },
                        "overengineering_pressure": {
                            "score": module.overengineering_pressure.score,
                        },
                        "refactoring_pressure": {
                            "score": module.refactoring_pressure.score,
                        },
                        "complexity": {
                            "score": module.complexity.score,
                            "density": module.complexity.density,
                            "stat(classes+functions)": {
                                "avg": module.complexity.stat.avg,
                                "min": module.complexity.stat.min,
                                "max": module.complexity.stat.max,
                                "p50": module.complexity.stat.p50,
                                "p90": module.complexity.stat.p90,
                            },
                        },
                    }
                )

    def make_classes_report(self, data: dict):
        data["classes"] = []

        if self._top_classes:
            for cls in self._top_classes:
                data["classes"].append(
                    {
                        "name": cls.name,
                        "file": cls.module.path,
                        "loc": cls.loc,
                        "methods": len(cls.methods),
                        "status": {
                            "name": cls.status.name.value,
                            "score": cls.status.score.value,
                            "reasons": cls.status.reasons,
                            "suggestions": cls.status.suggestions,
                        },
                        "overengineering_pressure": {
                            "score": cls.overengineering_pressure.score,
                        },
                        "complexity": {
                            "score": cls.complexity.score,
                            "density": cls.complexity.density,
                            "stat(methods)": {
                                "avg": cls.complexity.stat.avg,
                                "min": cls.complexity.stat.min,
                                "max": cls.complexity.stat.max,
                                "p50": cls.complexity.stat.p50,
                                "p90": cls.complexity.stat.p90,
                            },
                        },
                    }
                )

    def make_methods_report(self, data: dict):
        data["methods"] = []

        if self._top_methods:
            for method in self._top_methods:
                data["methods"].append(
                    {
                        "name": method.name,
                        "file": method.module.path,
                        "class": method.cls.name,
                        "loc": method.loc,
                        "closures": len(method.closures),
                        "status": {
                            "name": method.status.name.value,
                            "score": method.status.score.value,
                            "reasons": method.status.reasons,
                            "suggestions": method.status.suggestions,
                        },
                        "complexity": {
                            "value": method.complexity.score,
                            "total": method.complexity.total,
                            "density": method.complexity.density,
                            "stat(closures)": {
                                "avg": method.complexity.stat.avg,
                                "min": method.complexity.stat.min,
                                "max": method.complexity.stat.max,
                                "p50": method.complexity.stat.p50,
                                "p90": method.complexity.stat.p90,
                            },
                        },
                    }
                )

    def make_functions_report(self, data: dict):
        data["functions"] = []

        if self._top_functions:
            for func in self._top_functions:
                data["functions"].append(
                    {
                        "name": func.name,
                        "file": func.module.path,
                        "loc": func.loc,
                        "closures": len(func.closures),
                        "status": {
                            "name": func.status.name.value,
                            "score": func.status.score.value,
                            "reasons": func.status.reasons,
                            "suggestions": func.status.suggestions,
                        },
                        "complexity": {
                            "score": func.complexity.score,
                            "total": func.complexity.total,
                            "density": func.complexity.density,
                            "stat(closures)": {
                                "avg": func.complexity.stat.avg,
                                "min": func.complexity.stat.min,
                                "max": func.complexity.stat.max,
                                "p50": func.complexity.stat.p50,
                                "p90": func.complexity.stat.p90,
                            },
                        },
                    }
                )

    def _report(self) -> None:
        data = {
            "project": {
                "lang": self._sources.lang,
                "loc": self._sources.loc,
                "packages": len(self._sources.packages),
                "modules": len(self._sources.modules),
                "classes": len(self._sources.classes),
                "methods": len(self._sources.methods),
                "functions": len(self._sources.functions),
                "status": {
                    "name": self._sources.status.name,
                    "score": self._sources.status.score.value,
                    "reasons": self._sources.status.reasons,
                    "suggestions": self._sources.status.suggestions,
                },
                "overengineering_pressure": {
                    "score": self._sources.overengineering_pressure.score,
                },
                "refactoring_pressure": {
                    "score": self._sources.refactoring_pressure.score,
                    "stat(modules)": {
                        "avg": self._sources.refactoring_pressure.stat.avg,
                        "min": self._sources.refactoring_pressure.stat.min,
                        "max": self._sources.refactoring_pressure.stat.max,
                        "p50": self._sources.refactoring_pressure.stat.p50,
                        "p90": self._sources.refactoring_pressure.stat.p90,
                    },
                },
                "complexity": {
                    "score": self._sources.complexity.score,
                    "density": self._sources.complexity.density,
                    "stat(modules)": {
                        "avg": self._sources.complexity.stat.avg,
                        "min": self._sources.complexity.stat.min,
                        "max": self._sources.complexity.stat.max,
                        "p50": self._sources.complexity.stat.p50,
                        "p90": self._sources.complexity.stat.p90,
                    },
                },
            },
        }

        if not self._short:
            self.make_packages_report(data)
            self.make_modules_report(data)

            if self._details:
                self.make_classes_report(data)
                self.make_methods_report(data)
                self.make_functions_report(data)

        print(json.dumps(data, indent=2))
