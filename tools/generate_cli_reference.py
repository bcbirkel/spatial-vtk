"""Generate the Spatial-VTK CLI reference pages from the argparse parser.

Purpose
-------
This script walks the public ``svtk`` argparse command tree and writes Sphinx
reference pages that list each command, subcommand, positional argument, and
option accepted by the current package.

Usage examples
--------------
From the public migration root:
  ``PYTHONPATH=src python tools/generate_cli_reference.py``

From the private repository root:
  ``PYTHONPATH=public_migration/src python public_migration/tools/generate_cli_reference.py``
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from spatial_vtk.cli import build_parser


ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "docs"
CLI_DIR = DOCS_ROOT / "reference" / "cli"
CLI_INDEX = DOCS_ROOT / "reference" / "cli_api.rst"

TOP_LEVEL_ORDER = ["config", "io", "qc", "metrics", "plot", "map", "visualize", "dashboard", "call"]
HEADING_CHARS = ["=", "-", "~", "^", '"']


def main() -> int:
    """Write the generated CLI reference pages.

    Parameters
    ----------
    None

    Returns
    -------
    int
        Process-style exit code.
    """

    parser = build_parser()
    CLI_DIR.mkdir(parents=True, exist_ok=True)
    top_subcommands = _subcommands(parser)
    _write_cli_index(parser, top_subcommands)
    for command_name in _ordered_names(top_subcommands):
        page_path = CLI_DIR / f"{command_name}.rst"
        page_path.write_text(
            "\n".join(_render_command_page(command_name, top_subcommands[command_name])).rstrip() + "\n",
            encoding="utf-8",
        )
    print(f"Wrote CLI reference pages under {CLI_DIR}")
    return 0


def _write_cli_index(
    parser: argparse.ArgumentParser,
    top_subcommands: dict[str, argparse.ArgumentParser],
) -> None:
    """Write the top-level CLI API landing page.

    Parameters
    ----------
    parser
        Root argparse parser for ``svtk``.
    top_subcommands
        Top-level command parsers keyed by command name.

    Returns
    -------
    None
    """

    top_help = _subcommand_help_map(parser)
    lines: list[str] = [
        "CLI API",
        "=======",
        "",
        "The public command is ``svtk``. It gives you file-based access to the same major Spatial-VTK workflows used from Python: configuration inspection, metadata and waveform preparation, QC queue export, metric planning and execution, plotting, mapping, dashboards, and advanced calls to importable public functions.",
        "",
        "Run ``svtk --help`` to see the command tree from your installed environment.",
        "",
        ".. code-block:: bash",
        "",
        "   svtk --help",
        "   svtk --version",
        "",
        "Command Groups",
        "--------------",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        "   :widths: 24 76",
        "",
        "   * - Command",
        "     - What it does",
    ]
    for name in _ordered_names(top_subcommands):
        summary = top_help.get(name) or _parser_summary(top_subcommands[name])
        lines.extend(
            [
                f"   * - :doc:`svtk {name} <cli/{name}>`",
                f"     - {_rst_escape(summary)}",
            ]
        )
    lines.extend(
        [
            "",
            "Detailed Command Reference",
            "--------------------------",
            "",
            ".. toctree::",
            "   :maxdepth: 2",
            "",
        ]
    )
    for name in _ordered_names(top_subcommands):
        lines.append(f"   cli/{name}")
    lines.extend(
        [
            "",
            "Plotting and Mapping Notes",
            "--------------------------",
            "",
            "Most plotting and mapping commands accept ``--input`` for the main table, ``--output`` for the figure path, and ``--kwargs key=value`` for function-specific settings such as ``value_col=log2_residual`` or ``title='Residuals by distance'``. Commands that need additional tables accept ``--table argument_name=path`` and, where available, convenience aliases such as ``--events`` or ``--stations``.",
            "",
            "Map commands also accept ``--config`` and ``--bounds`` so you can reuse named bounds from your project config. Basemaps are enabled by default for map figures; use ``--no-basemap`` only when you explicitly want a data-only map.",
            "",
            "Advanced Python Calls",
            "---------------------",
            "",
            "``svtk call`` is available when you need to run an importable public function that does not yet have a curated workflow command. It only accepts import paths under ``spatial_vtk``.",
            "",
        ]
    )
    CLI_INDEX.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _render_command_page(command_name: str, parser: argparse.ArgumentParser) -> list[str]:
    """Render one top-level command page.

    Parameters
    ----------
    command_name
        Top-level command name, such as ``metrics``.
    parser
        Argparse parser for that command.

    Returns
    -------
    list[str]
        RST lines for the page.
    """

    title = f"svtk {command_name}"
    summary = _parser_summary(parser)
    lines = [_command_anchor(parser.prog), "", title, "=" * len(title), ""]
    if summary:
        lines.extend([_rst_escape(summary), ""])
    lines.extend(
        [
            "Command Tree",
            "------------",
            "",
        ]
    )
    lines.extend(_render_command_tree(parser))
    lines.extend(
        [
            "",
            "Command Details",
            "---------------",
            "",
        ]
    )
    lines.extend(_render_command_details(parser, level=2, include_title=False, include_summary=False))
    return lines


def _render_command_details(
    parser: argparse.ArgumentParser,
    *,
    level: int,
    include_title: bool = True,
    include_summary: bool = True,
) -> list[str]:
    """Render command usage and parameters plus child command detail sections.

    Parameters
    ----------
    parser
        Parser to render.
    level
        Heading level used for nested command sections.
    include_title
        Whether to emit a section title for ``parser.prog``.
    include_summary
        Whether to emit the parser's short description before usage.

    Returns
    -------
    list[str]
        RST lines for this command and its descendants.
    """

    lines: list[str] = []
    if include_title:
        title = parser.prog
        underline = HEADING_CHARS[min(level, len(HEADING_CHARS) - 1)] * len(title)
        lines.extend([_command_anchor(parser.prog), "", title, underline, ""])
    summary = _parser_summary(parser)
    if summary and include_summary:
        lines.extend([_rst_escape(summary), ""])
    lines.extend(_render_usage(parser))
    argument_lines = _render_arguments(parser)
    if argument_lines:
        lines.extend(argument_lines)
    children = _subcommands(parser)
    if children:
        for child_name in _ordered_names(children):
            lines.extend(_render_command_details(children[child_name], level=level + 1, include_title=True))
    return lines


def _render_command_tree(parser: argparse.ArgumentParser, *, depth: int = 0) -> list[str]:
    """Render a nested clickable list of commands.

    Parameters
    ----------
    parser
        Parser whose command tree should be rendered.
    depth
        Current list nesting depth.

    Returns
    -------
    list[str]
        RST bullet-list lines.
    """

    indent = "   " * depth
    summary = _parser_summary(parser)
    summary_text = f" - {_rst_escape(summary)}" if summary and depth > 0 else ""
    lines = [f"{indent}- :ref:`{parser.prog} <{_command_ref(parser.prog)}>`{summary_text}"]
    children = _subcommands(parser)
    for child_name in _ordered_names(children):
        lines.extend(_render_command_tree(children[child_name], depth=depth + 1))
    return lines


def _render_usage(parser: argparse.ArgumentParser) -> list[str]:
    """Render a parser usage block.

    Parameters
    ----------
    parser
        Parser whose usage should be rendered.

    Returns
    -------
    list[str]
        RST lines containing a bash code block.
    """

    usage = parser.format_usage().replace("usage: ", "", 1).strip()
    return [".. rubric:: Usage", "", ".. code-block:: bash", "", f"   {usage}", ""]


def _render_arguments(parser: argparse.ArgumentParser) -> list[str]:
    """Render positional and optional parser arguments.

    Parameters
    ----------
    parser
        Parser whose arguments should be rendered.

    Returns
    -------
    list[str]
        RST lines containing an argument table.
    """

    rows = [_argument_row(action) for action in parser._actions if _is_argument_action(action)]
    rows = [row for row in rows if row is not None]
    if not rows:
        return []
    lines = [
        ".. rubric:: Parameters",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        "   :widths: 26 13 14 47",
        "",
        "   * - Name",
        "     - Required",
        "     - Default / choices",
        "     - Description",
    ]
    for name, required, default, description in rows:
        lines.extend(
            [
                f"   * - {name}",
                f"     - {required}",
                f"     - {default}",
                f"     - {description}",
            ]
        )
    lines.append("")
    return lines


def _argument_row(action: argparse.Action) -> tuple[str, str, str, str] | None:
    """Convert an argparse action into one reference-table row.

    Parameters
    ----------
    action
        Argparse action for a positional or optional parameter.

    Returns
    -------
    tuple[str, str, str, str] | None
        Rendered name, required marker, default/choices text, and description.
    """

    if isinstance(action, argparse._HelpAction):
        name = "``-h``, ``--help``"
        required = "No"
        default = ""
    elif action.option_strings:
        name = ", ".join(f"``{option}``" for option in action.option_strings)
        required = "Yes" if getattr(action, "required", False) else "No"
        default = _default_text(action)
    else:
        name = f"``{action.dest}``"
        required = "Yes"
        default = _default_text(action)
    description = _rst_escape((action.help or "").replace("%(default)s", str(action.default))).strip()
    if action.metavar:
        description = f"Value: ``{action.metavar}``. {description}".strip()
    elif action.option_strings and not isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction, argparse._HelpAction)):
        description = f"Value: ``{action.dest}``. {description}".strip()
    return name, required, default, description or ""


def _default_text(action: argparse.Action) -> str:
    """Format defaults, choices, and repeatability for one action.

    Parameters
    ----------
    action
        Argparse action.

    Returns
    -------
    str
        Compact default and choices description for an RST table cell.
    """

    parts: list[str] = []
    default = getattr(action, "default", None)
    if default not in (None, argparse.SUPPRESS, False, (), []):
        parts.append(f"Default: {_literal_or_empty(str(default))}")
    if getattr(action, "choices", None):
        choices = ", ".join(_literal_or_empty(str(choice)) for choice in action.choices)
        parts.append(f"Choices: {choices}")
    if getattr(action, "nargs", None):
        parts.append(f"Nargs: ``{action.nargs}``")
    if getattr(action, "action", None) == "append":
        parts.append("Repeatable")
    if isinstance(action, argparse._AppendAction):
        parts.append("Repeatable")
    if isinstance(action, argparse._StoreTrueAction):
        parts.append("Flag")
    return "; ".join(parts)


def _subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    """Return subcommands registered on a parser.

    Parameters
    ----------
    parser
        Parser to inspect.

    Returns
    -------
    dict[str, argparse.ArgumentParser]
        Subcommand choices keyed by command name.
    """

    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def _command_anchor(prog: str) -> str:
    """Return an explicit RST anchor for one CLI command.

    Parameters
    ----------
    prog
        Full command path, such as ``svtk plot metrics``.

    Returns
    -------
    str
        RST label line.
    """

    return f".. _{_command_ref(prog)}:"


def _command_ref(prog: str) -> str:
    """Return a stable reference token for one CLI command.

    Parameters
    ----------
    prog
        Full command path, such as ``svtk plot metrics``.

    Returns
    -------
    str
        Reference label safe for Sphinx ``:ref:`` links.
    """

    token = prog.replace(" ", "-").replace("_", "-")
    return f"cli-{token}"


def _subcommand_help_map(parser: argparse.ArgumentParser) -> dict[str, str]:
    """Return help text registered for a parser's subcommands.

    Parameters
    ----------
    parser
        Parser whose subparser action should be inspected.

    Returns
    -------
    dict[str, str]
        Short help text keyed by subcommand name.
    """

    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return {choice.dest: choice.help or "" for choice in action._choices_actions}
    return {}


def _is_argument_action(action: argparse.Action) -> bool:
    """Decide whether an argparse action should be shown as a parameter.

    Parameters
    ----------
    action
        Argparse action to inspect.

    Returns
    -------
    bool
        True for normal positional and optional arguments.
    """

    return not isinstance(action, argparse._SubParsersAction)


def _ordered_names(items: dict[str, argparse.ArgumentParser]) -> list[str]:
    """Sort command names with top-level commands in workflow order.

    Parameters
    ----------
    items
        Command parser mapping.

    Returns
    -------
    list[str]
        Ordered command names.
    """

    preferred = [name for name in TOP_LEVEL_ORDER if name in items]
    remaining = sorted(name for name in items if name not in TOP_LEVEL_ORDER)
    return preferred + remaining


def _parser_summary(parser: argparse.ArgumentParser) -> str:
    """Return the best short description available for a parser.

    Parameters
    ----------
    parser
        Parser to summarize.

    Returns
    -------
    str
        Description or empty string.
    """

    return (parser.description or "").strip() or _summary_from_help(parser)


def _summary_from_help(parser: argparse.ArgumentParser) -> str:
    """Extract a concise summary from parser help text.

    Parameters
    ----------
    parser
        Parser whose help text should be searched.

    Returns
    -------
    str
        Short help summary when available.
    """

    return ""


def _rst_escape(value: str) -> str:
    """Escape table-sensitive characters in generated RST text.

    Parameters
    ----------
    value
        Raw text.

    Returns
    -------
    str
        RST-safe text.
    """

    return value.replace("|", "\\|").replace("\n", " ")


def _literal_or_empty(value: str) -> str:
    """Render a value as an inline literal or a readable empty-string marker.

    Parameters
    ----------
    value
        Raw value to render in generated RST.

    Returns
    -------
    str
        RST-safe inline literal text, or ``empty string`` for blank values.
    """

    if value == "":
        return "empty string"
    return f"``{_rst_escape(value)}``"


if __name__ == "__main__":
    raise SystemExit(main())
