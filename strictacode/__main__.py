import os
import typing as t

import click

from strictacode import skill
from strictacode import constants
from strictacode.py import PyLoder
from strictacode.go import GoLoder
from strictacode.js import JSLoder
from strictacode.analyzer import Analyzer
from strictacode.utils import detect_language
from strictacode.config import Config, Language
from strictacode.reporters import TextReporter, JsonReporter


def create_config() -> Config:
    config = Config()

    if os.path.exists(f'{constants.CONFIG_NAME}.yml'):
        config = Config.from_yaml_file(f'{constants.CONFIG_NAME}.yml')
    elif os.path.exists(f'{constants.CONFIG_NAME}.yaml'):
        config = Config.from_yaml_file(f'{constants.CONFIG_NAME}.yml')
    elif os.path.exists(f'{constants.CONFIG_NAME}.json'):
        config = Config.from_json_file(f'{constants.CONFIG_NAME}.json')

    return config


@click.group()
def app():
    pass


@click.option('--top-packages', type=int, default=None)
@click.option('--top-modules', type=int, default=None)
@click.option('--top-classes', type=int, default=None)
@click.option('--top-methods', type=int, default=None)
@click.option('--top-functions', type=int, default=None)
@click.option('--short/--no-short', is_flag=True, default=False)
@click.option('--details/--no-details', is_flag=True, default=False)
@click.option('--format', '-f', 'fmt', type=click.Choice(['text', 'json']), default='text')
@click.argument('path', type=os.path.abspath, required=True)
@app.command()
def analyze(path: str, fmt: str, short: bool, details: bool,
            top_packages: t.Optional[int], top_modules: t.Optional[int],
            top_classes: t.Optional[int], top_methods: t.Optional[int],
            top_functions: t.Optional[int]):
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
        loader_options['class_loc_from_methods'] = True

    if config.loader.exclude is not None:
        loader_options['exclude_patterns'] = config.loader.exclude

    loader_class = lang_to_loader[config.lang]
    loader = loader_class(**loader_options)
    sources = loader.load()

    analyzer = Analyzer(sources)
    analyzer.analyze()

    format_to_reporter = {
        'text': TextReporter,
        'json': JsonReporter,
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
                              top_packages=config.reporter.top.packages,
                              top_modules=config.reporter.top.modules,
                              top_classes=config.reporter.top.classes,
                              top_methods=config.reporter.top.methods,
                              top_functions=config.reporter.top.functions,)
    reporter.report()


@app.group()
def install():
    pass


@click.option('--name', type=str, default='strictacode')
@click.option('--agent', required=True, type=click.Choice([
    "claude", "cursor", "codex",
    "gemini", "antigravity",
]))
@install.command()
def agent_skill(agent: str, name: str):
    click.secho(f"Installing skill for agent \"{agent}\"...")
    installed_path = skill.install(name, agent)
    click.secho(f"Successfully installed into \"{installed_path}\"")


if __name__ == '__main__':
    app()
