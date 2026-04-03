import ast
from collections import defaultdict
from pathlib import Path


class Analyzer(ast.NodeVisitor):
    def __init__(self, filepath: str, module: str):
        self.filepath = filepath
        self.module = module

        self.classes = {}
        self.class_bases = defaultdict(list)

        self.current_class = None

    @classmethod
    def file(cls, filepath: str):
        path = Path(filepath)
        module = path.with_suffix("")
        module = ".".join(module.parts)

        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            return None

        analyzer = cls(filepath, module)
        analyzer.visit(tree)

        return analyzer

    def visit_ClassDef(self, node):
        cname = f"{self.filepath}:{node.name}"

        self.classes[cname] = {"methods": 0}
        self.current_class = cname

        for base in node.bases:
            if isinstance(base, ast.Name):
                self.class_bases[cname].append(base.id)

            if isinstance(base, ast.Attribute):
                self.class_bases[cname].append(base.attr)

        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, _node):
        if self.current_class:
            self.classes[self.current_class]["methods"] += 1
