import os

import click

from strictacode import skill
from strictacode.py import PyLoder
from strictacode.go import GoLoder
from strictacode.js import JSLoder
from strictacode.analyzer import Analyzer
from strictacode.utils import detect_language
from strictacode.reporters import TextReporter, JsonReporter


@click.group()
def app():
    pass


@click.option('--short/--no-short', is_flag=True, default=False)
@click.option('--details/--no-details', is_flag=True, default=False)
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text')
@click.argument('path', type=os.path.abspath, required=True)
@app.command()
def analyze(path: str, format: str, short: bool, details: bool):
    if not os.path.exists(path):
        raise click.UsageError(f"Path \"{path}\" does not exist")
    if not os.path.isdir(path):
        raise click.UsageError("Path \"{path}\" is not a directory")

    os.chdir(path)

    lang_to_loader = {
        'golang': GoLoder,
        'python': PyLoder,
        'javascript': JSLoder,
    }
    loader_options = {}

    language = detect_language(path)

    if language is None:
        raise click.UsageError("Program language is not supported")

    if language == 'golang':
        loader_options['class_loc_from_methods'] = True

    loader_class = lang_to_loader[language]
    loader = loader_class(**loader_options)
    sources = loader.load()

    analyzer = Analyzer(sources)
    analyzer.analyze()

    format_to_reporter = {
        'text': TextReporter,
        'json': JsonReporter,
    }
    reporter_class = format_to_reporter[format]

    reporter = reporter_class(sources,
                              short=short,
                              details=details)
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
