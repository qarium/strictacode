import json
import os

import click

from strictacode import constants, skill
from strictacode.analyzer import Analyzer
from strictacode.config import Config, Language
from strictacode.go import GoLoder
from strictacode.js import JSLoder
from strictacode.kotlin import KotlinLoder
from strictacode.py import PyLoder
from strictacode.reporters import (
    JsonDiffReporter,
    JsonResultReporter,
    TextDiffReporter,
    TextResultReporter,
)
from strictacode.statistics import ProjectDiff, ProjectStat
from strictacode.swift import SwiftLoder
from strictacode.threshold import Threshold
from strictacode.utils import detect_language


def create_config() -> Config:
    config = Config()

    if os.path.exists(f"{constants.CONFIG_NAME}.yml") or os.path.exists(f"{constants.CONFIG_NAME}.yaml"):
        config = Config.from_yaml_file(f"{constants.CONFIG_NAME}.yml")
    elif os.path.exists(f"{constants.CONFIG_NAME}.json"):
        config = Config.from_json_file(f"{constants.CONFIG_NAME}.json")

    return config


@click.group()
def app():
    pass


@click.option("--threshold", type=str, default=None)
@click.option("--top-packages", type=int, default=None)
@click.option("--top-modules", type=int, default=None)
@click.option("--top-classes", type=int, default=None)
@click.option("--top-methods", type=int, default=None)
@click.option("--top-functions", type=int, default=None)
@click.option("--short/--no-short", is_flag=True, default=False)
@click.option("--output", "-o", type=str, default=None)
@click.option("--details/--no-details", is_flag=True, default=False)
@click.option("--format", "-f", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.argument("path", type=os.path.abspath, required=True)
@app.command()
def analyze(
    path: str,
    fmt: str,
    short: bool,
    details: bool,
    top_packages: int | None,
    top_modules: int | None,
    top_classes: int | None,
    top_methods: int | None,
    top_functions: int | None,
    threshold: str | None,
    output: str | None,
):
    if not os.path.exists(path):
        raise click.UsageError(f'Path "{path}" does not exist')
    if not os.path.isdir(path):
        raise click.UsageError('Path "{path}" is not a directory')

    os.chdir(path)

    config = create_config()

    lang_to_loader = {
        Language.GOLANG: GoLoder,
        Language.PYTHON: PyLoder,
        Language.JAVASCRIPT: JSLoder,
        Language.KOTLIN: KotlinLoder,
        Language.SWIFT: SwiftLoder,
    }
    loader_options = {}

    if config.lang is None:
        lang = detect_language(path)
        config.lang = None if lang is None else Language(lang)

    if config.lang is None:
        raise click.UsageError("Unknown program language")

    if config.lang == Language.GOLANG:
        loader_options["class_loc_from_methods"] = True

    if config.loader.include is not None:
        loader_options["include_patterns"] = config.loader.include
    if config.loader.exclude is not None:
        loader_options["exclude_patterns"] = config.loader.exclude

    loader_class = lang_to_loader[config.lang]
    loader = loader_class(**loader_options)
    sources = loader.load()

    analyzer = Analyzer(sources)
    analyzer.analyze()

    format_to_reporter = {
        "text": TextResultReporter,
        "json": JsonResultReporter,
    }
    reporter_class = format_to_reporter[fmt]

    if top_packages is not None:
        config.reporter.top.packages = top_packages
    if top_modules is not None:
        config.reporter.top.modules = top_modules
    if top_classes is not None:
        config.reporter.top.classes = top_classes
    if top_methods is not None:
        config.reporter.top.methods = top_methods
    if top_functions is not None:
        config.reporter.top.functions = top_functions

    reporter = reporter_class(
        sources,
        short=short,
        details=details,
        output=output,
        top_packages=config.reporter.top.packages,
        top_modules=config.reporter.top.modules,
        top_classes=config.reporter.top.classes,
        top_methods=config.reporter.top.methods,
        top_functions=config.reporter.top.functions,
    )
    reporter.report()

    if threshold is not None:
        thresholds = Threshold.from_string(threshold)
        errors = thresholds.check(
            score=sources.status.score.value,
            complexity_density=sources.complexity.density,
            refactoring_pressure=sources.refactoring_pressure.score,
            overengineering_pressure=sources.overengineering_pressure.score,
        )

        if errors:
            for error in errors:
                click.secho(f"FAIL: {error}", fg="red")
            exit(1)


@click.option("--threshold", type=str, default=None)
@click.option("--output", "-o", type=str, default=None)
@click.option("--details/--no-details", is_flag=True, default=False)
@click.option("--format", "-f", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.argument("current", type=os.path.abspath, required=True)
@click.argument("baseline", type=os.path.abspath, required=True)
@app.command()
def compare(baseline: str, current: str, threshold: str | None, details: bool, output: str, fmt: str):
    with open(baseline) as f:
        baseline_data = json.load(f)
    with open(current) as f:
        current_data = json.load(f)

    baseline_stat = ProjectStat(
        name="baseline",
        score=baseline_data["project"]["status"]["score"],
        complexity_density=baseline_data["project"]["complexity"]["density"],
        refactoring_pressure=baseline_data["project"]["refactoring_pressure"]["score"],
        overengineering_pressure=baseline_data["project"]["overengineering_pressure"]["score"],
    )
    current_stat = ProjectStat(
        name="current",
        score=current_data["project"]["status"]["score"],
        complexity_density=current_data["project"]["complexity"]["density"],
        refactoring_pressure=current_data["project"]["refactoring_pressure"]["score"],
        overengineering_pressure=current_data["project"]["overengineering_pressure"]["score"],
    )
    project_diff = ProjectDiff(current_stat, baseline_stat)

    format_to_reporter = {
        "text": TextDiffReporter,
        "json": JsonDiffReporter,
    }
    reporter_class = format_to_reporter[fmt]

    reporter = reporter_class(
        project_diff,
        output=output,
        details=details,
    )
    reporter.report()

    if threshold is not None:
        thresholds = Threshold.from_string(threshold)
        errors = thresholds.check(
            score=project_diff.score,
            complexity_density=project_diff.complexity_density,
            refactoring_pressure=project_diff.refactoring_pressure,
            overengineering_pressure=project_diff.overengineering_pressure,
        )

        if errors:
            for error in errors:
                click.secho(f"FAIL: {error}", fg="red")
            exit(1)


@app.group()
def install():
    pass


@click.option("--name", type=str, default="strictacode")
@click.option(
    "--agent",
    required=True,
    type=click.Choice(
        [
            "claude",
            "cursor",
            "codex",
            "gemini",
            "antigravity",
        ]
    ),
)
@install.command()
def agent_skill(agent: str, name: str):
    click.secho(f'Installing skill for agent "{agent}"...')
    installed_path = skill.install(name, agent)
    click.secho(f'Successfully installed into "{installed_path}"')


if __name__ == "__main__":
    app()
