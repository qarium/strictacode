import os
import json
import typing as t

import click

from strictacode import skill
from strictacode import constants
from strictacode.py import PyLoder
from strictacode.go import GoLoder
from strictacode.js import JSLoder
from strictacode.analyzer import Analyzer
from strictacode.threshold import Threshold
from strictacode.utils import detect_language
from strictacode.config import Config, Language
from strictacode.reporters import TextReporter, JsonReporter


def create_config() -> Config:
    config = Config()

    if os.path.exists(f"{constants.CONFIG_NAME}.yml"):
        config = Config.from_yaml_file(f"{constants.CONFIG_NAME}.yml")
    elif os.path.exists(f"{constants.CONFIG_NAME}.yaml"):
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
def analyze(path: str, fmt: str, short: bool, details: bool,
            top_packages: t.Optional[int], top_modules: t.Optional[int],
            top_classes: t.Optional[int], top_methods: t.Optional[int],
            top_functions: t.Optional[int], threshold: t.Optional[str],
            output: t.Optional[str]):
    if not os.path.exists(path):
        raise click.UsageError(f"Path \"{path}\" does not exist")
    if not os.path.isdir(path):
        raise click.UsageError("Path \"{path}\" is not a directory")

    os.chdir(path)

    config = create_config()

    lang_to_loader = {
        Language.GOLANG: GoLoder,
        Language.PYTHON: PyLoder,
        Language.JAVASCRIPT: JSLoder,
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
        "text": TextReporter,
        "json": JsonReporter,
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

    reporter = reporter_class(sources,
                              short=short,
                              details=details,
                              output=output,
                              top_packages=config.reporter.top.packages,
                              top_modules=config.reporter.top.modules,
                              top_classes=config.reporter.top.classes,
                              top_methods=config.reporter.top.methods,
                              top_functions=config.reporter.top.functions,)
    reporter.report()

    if threshold is not None:
        thresholds = Threshold.from_string(threshold)
        errors = thresholds.check(score=sources.status.score.value,
                                  complexity_density=sources.complexity.density,
                                  refactoring_pressure=sources.refactoring_pressure.score,
                                  overengineering_pressure=sources.overengineering_pressure.score)

        if errors:
            for error in errors:
                click.secho(f"FAIL: {error}", fg="red")
            exit(1)


@click.option("--threshold", type=str, default=None)
@click.argument("result_two", type=os.path.abspath, required=True)
@click.argument("result_one", type=os.path.abspath, required=True)
@app.command()
def compare(result_one: str, result_two: str, threshold: t.Optional[str]):
    with open(result_one) as f:
        data_1 = json.load(f)
    with open(result_two) as f:
        data_2 = json.load(f)

    score_1 = data_1["project"]["status"]["score"]
    score_2 = data_2["project"]["status"]["score"]
    density_1 = data_1["project"]["complexity"]["density"]
    density_2 = data_2["project"]["complexity"]["density"]
    rp_1 = data_1["project"]["refactoring_pressure"]["score"]
    rp_2 = data_2["project"]["refactoring_pressure"]["score"]
    op_1 = data_1["project"]["overengineering_pressure"]["score"]
    op_2 = data_2["project"]["overengineering_pressure"]["score"]

    score_diff = abs(score_1 - score_2)
    density_diff = abs(density_1 - density_2)
    rp_diff = abs(rp_1 - rp_2)
    oe_diff = abs(op_1 - op_2)

    click.echo(f"Result({os.path.basename(result_one)}):")
    click.echo(f"  * Score: {score_1}")
    click.echo(f"  * Complexity: {density_1}")
    click.echo(f"  * Refactoring: {rp_1}")
    click.echo(f"  * Overengineering pressure: {op_1}")
    click.echo(f"")
    click.echo(f"---")
    click.echo(f"")
    click.echo(f"Result({os.path.basename(result_two)}):")
    click.echo(f"  * Score: {score_2}")
    click.echo(f"  * Complexity: {density_2}")
    click.echo(f"  * Refactoring: {rp_2}")
    click.echo(f"  * Overengineering pressure: {op_2}")
    click.echo(f"")
    click.echo(f"---")
    click.echo(f"")
    click.secho("Diff:")
    click.echo(f"  * Score: {score_diff}")
    click.echo(f"  * Complexity density: {density_diff}")
    click.echo(f"  * Refactoring pressure: {rp_diff}")
    click.echo(f"  * Overengineering pressure: {oe_diff}")

    if threshold is not None:
        thresholds = Threshold.from_string(threshold)
        errors = thresholds.check(score=score_diff,
                                  complexity_density=density_diff,
                                  refactoring_pressure=rp_diff,
                                  overengineering_pressure=oe_diff)

        if errors:
            for error in errors:
                click.secho(f"FAIL: {error}", fg="red")
            exit(1)


@app.group()
def install():
    pass


@click.option("--name", type=str, default="strictacode")
@click.option("--agent", required=True, type=click.Choice([
    "claude", "cursor", "codex",
    "gemini", "antigravity",
]))
@install.command()
def agent_skill(agent: str, name: str):
    click.secho(f"Installing skill for agent \"{agent}\"...")
    installed_path = skill.install(name, agent)
    click.secho(f"Successfully installed into \"{installed_path}\"")


if __name__ == "__main__":
    app()
