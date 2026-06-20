"""Generate the Spatial-VTK CLI reference pages from the argparse parser.

Purpose
-------
This script walks the public ``svtk`` argparse command tree and writes Sphinx
reference pages that list each command, subcommand, positional argument, and
option accepted by the current package.

Usage examples
--------------
From the repository root:
  ``PYTHONPATH=src python tools/generate_cli_reference.py``
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Sequence

from spatial_vtk.cli import (
    PlotCommand,
    _registered_list_extra_tables,
    _registered_list_input,
    _registered_list_output,
    build_parser,
)


ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "docs"
CLI_DIR = DOCS_ROOT / "reference" / "cli"
CLI_INDEX = DOCS_ROOT / "reference" / "cli_api.rst"

TOP_LEVEL_ORDER = ["config", "io", "qc", "metrics", "spatial", "plot", "map", "visualize", "dashboard", "call"]
HEADING_CHARS = ["=", "-", "~", "^", '"']
EXAMPLE_CONFIG = "data/examples/configuration/example_spatial_vtk_config.yaml"
REQUIRED_INPUT_TABLE_MEANINGS = {
    "sample_df": "a prepared trace-sample table",
    "spectrogram_df": "a precomputed period-spectrogram table",
}


def main(argv: Sequence[str] | None = None) -> int:
    """Write or check the generated CLI reference pages.

    Parameters
    ----------
    argv
        Optional command-line arguments. When omitted, ``sys.argv`` is used.

    Returns
    -------
    int
        Process-style exit code.
    """

    arg_parser = argparse.ArgumentParser(
        description="Generate Spatial-VTK CLI reference pages from the argparse parser.",
        epilog="Run without arguments to rewrite the generated reference files.",
    )
    arg_parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether generated CLI reference files are current without rewriting them.",
    )
    args = arg_parser.parse_args(argv)

    rendered = _render_cli_reference()
    if args.check:
        return _check_cli_reference(rendered)

    CLI_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in rendered.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"Wrote CLI reference pages under {CLI_DIR}")
    return 0


def _render_cli_reference() -> dict[Path, str]:
    """Render every generated CLI reference file into memory."""

    parser = build_parser()
    top_subcommands = _subcommands(parser)
    rendered: dict[Path, str] = {
        CLI_INDEX: "\n".join(_render_cli_index(parser, top_subcommands)).rstrip() + "\n",
    }
    for command_name in _ordered_names(top_subcommands):
        page_path = CLI_DIR / f"{command_name}.rst"
        rendered[page_path] = (
            "\n".join(_render_command_page(command_name, top_subcommands[command_name])).rstrip() + "\n"
        )
    return rendered


def _check_cli_reference(rendered: dict[Path, str]) -> int:
    """Return nonzero when generated CLI reference files are stale."""

    stale: list[str] = []
    for path, expected in rendered.items():
        try:
            current = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            stale.append(f"missing: {path.relative_to(ROOT)}")
            continue
        if current != expected:
            stale.append(f"stale: {path.relative_to(ROOT)}")
    if stale:
        print("Generated CLI reference files are not current:")
        for item in stale:
            print(f"  {item}")
        print("Run: PYTHONPATH=src python tools/generate_cli_reference.py")
        return 1
    print("Generated CLI reference files are current.")
    return 0


def _render_cli_index(
    parser: argparse.ArgumentParser,
    top_subcommands: dict[str, argparse.ArgumentParser],
) -> list[str]:
    """Render the top-level CLI API landing page.

    Parameters
    ----------
    parser
        Root argparse parser for ``svtk``.
    top_subcommands
        Top-level command parsers keyed by command name.

    Returns
    -------
    list[str]
        RST lines for the top-level CLI API page.
    """

    top_help = _subcommand_help_map(parser)
    lines: list[str] = [
        "CLI API",
        "=======",
        "",
        "The public command is ``svtk``. It gives you file-based access to the same major Spatial-VTK workflows used from Python: configuration inspection, metadata and waveform preparation, QC queue export, metric planning and execution, plotting, mapping, dashboards, and advanced calls to public functions that do not yet have curated commands.",
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
            "Most plotting, mapping, and visualization commands can resolve their standard input tables and figure paths from the active config, so ``--input-table``/``--input`` and ``--figure-output``/``--output`` are optional for the usual tutorial/workflow outputs. Registered table defaults may be CSV or Parquet depending on the configured output key; commands that say they accept CSV or parquet read either suffix through the package table helpers. Use ``svtk plot metrics list``, ``svtk plot spatial list``, ``svtk map spatial list``, ``svtk visualize qc list``, ``svtk visualize context list``, or ``svtk visualize waveforms list`` to see which commands use ``config:<key>`` defaults and which still require explicit input tables, shown as ``required:<role>`` entries. Add ``--resolve-paths --config PATH`` to any of those list commands when you want to see the concrete configured paths that will be used. A ``required:<role>`` entry means that command has no registered default table for that role yet, so pass ``--input-table``/``--input`` or a named table flag for that invocation.",
            "",
            "Common figure controls such as ``--metric``, ``--passband``, ``--bin-label``, ``--component``, ``--components``, ``--model``, ``--mode``, ``--dep``, ``--indep``, ``--colorby``, ``--compare-to``, ``--value-col``, ``--score-col``, ``--scale``, ``--time-limit-s``, ``--max-records``, ``--max-traces``, ``--title``, ``--station-region``, ``--event-region``, ``--no-connect-points``, and sidecar options are first-class flags where they apply. Use ``--kwargs key=value`` only for advanced function-specific options that do not yet have curated flags. Prefer configured default tables and named table flags such as ``--event-table``, ``--station-table``, ``--events``, ``--stations``, or ``--records`` when a command lists them; use advanced ``--table function_argument=path`` only for extra function tables that do not yet have named flags.",
            "",
            "Map commands also accept ``--config`` and ``--bounds`` so you can reuse named bounds from your project config. Basemaps are enabled by default for map figures; use ``--no-basemap`` only when you explicitly want a data-only map.",
            "",
            "Advanced Python Calls",
            "---------------------",
            "",
            "``svtk call`` is an advanced escape hatch for importable public functions that do not yet have curated workflow commands. Prefer the named ``config``, ``io``, ``qc``, ``metrics``, ``spatial``, ``plot``, ``map``, ``visualize``, and ``dashboard`` commands for standard workflows. ``svtk call`` only accepts import paths under ``spatial_vtk``.",
            "",
        ]
    )
    return lines


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
    lines.extend(_command_page_notes(command_name))
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


def _command_page_notes(command_name: str) -> list[str]:
    """Return short top-level notes for command groups that need examples."""

    if command_name == "plot":
        return [
            "Config-Backed Plotting",
            "-----------------------",
            "",
            "If a config is active with ``svtk config set`` or passed with ``--config``, registered plotting commands resolve their standard input tables and figure outputs automatically. For routine workflow figures, prefer the curated flags shown below instead of passing legacy ``--input`` and ``--output`` paths.",
            "",
            ".. code-block:: bash",
            "",
            f"   svtk config set {EXAMPLE_CONFIG}",
            "   svtk plot metrics band-score-distribution --score-col log2_residual",
            "   svtk plot metrics residuals-vs-distance --metric PGA --passband \"2-3 sec\" --score-col log2_residual",
            "",
            "These commands use configured outputs such as ``metrics_long`` plus the registered figure keys for the selected plot unless you supply ``--input-table``/``--input`` or ``--figure-output``/``--output`` explicitly. Run ``svtk plot metrics list`` or ``svtk plot spatial list`` to print a table showing each command's input and output source, including ``config:<key>`` defaults and ``required:<role>`` entries. Add ``--resolve-paths --config PATH`` to show the concrete configured files.",
            "",
        ]
    if command_name == "map":
        return [
            "Config-Backed Mapping",
            "----------------------",
            "",
            "If a config is active with ``svtk config set`` or passed with ``--config``, registered map commands resolve their standard input tables, figure outputs, and named map bounds automatically. For routine workflow maps, prefer the curated flags shown below instead of passing legacy ``--input`` and ``--output`` paths.",
            "",
            ".. code-block:: bash",
            "",
            f"   svtk config set {EXAMPLE_CONFIG}",
            "   svtk map spatial station-metric --value-col log2_residual --metric PGA --passband \"2-3 sec\"",
            "   svtk map spatial event-residual --value-col log2_residual --metric PGA --bounds study_area",
            "",
            "These commands use configured outputs such as ``metrics_long`` and ``path_table`` plus the registered figure keys for the selected map unless you supply ``--input-table``/``--input`` or ``--figure-output``/``--output`` explicitly. Run ``svtk map spatial list`` to print a table showing each map command's input and output source, including ``config:<key>`` defaults and ``required:<role>`` entries. Add ``--resolve-paths --config PATH`` to show the concrete configured files.",
            "",
            "Basemaps are enabled by default for map figures; use ``--no-basemap`` only when you explicitly want a data-only map.",
            "",
        ]
    if command_name == "visualize":
        return [
            "Config-Backed Visualization",
            "---------------------------",
            "",
            "If a config is active with ``svtk config set`` or passed with ``--config``, registered visualization commands resolve their standard input tables and figure outputs automatically. For routine context, QC, and waveform figures, prefer the curated flags shown below instead of passing legacy ``--input`` and ``--output`` paths.",
            "",
            ".. code-block:: bash",
            "",
            f"   svtk config set {EXAMPLE_CONFIG}",
            "   svtk visualize qc retention-summary",
            "   svtk visualize context station-event-context --bounds study_area",
            "   svtk visualize waveforms observed-synthetic-record-section --components R --max-records 80",
            "",
            "These commands use configured outputs such as ``qc_metric_pair_retention``, ``event_station_records``, and the registered figure keys for the selected visualization unless you supply ``--input-table``/``--input`` or ``--figure-output``/``--output`` explicitly. Run ``svtk visualize qc list``, ``svtk visualize context list``, or ``svtk visualize waveforms list`` to print a table showing each command's input and output source, including ``config:<key>`` defaults and ``required:<role>`` entries. Add ``--resolve-paths --config PATH`` to show the concrete configured files.",
            "",
            "Use ``svtk visualize sidecars status`` to inspect figure provenance sidecars written by commands that support ``--write-sidecar``.",
            "",
        ]
    if command_name == "dashboard":
        return [
            "Config-Backed Dashboards",
            "------------------------",
            "",
            "Dashboard commands can resolve their standard datasets from the active config. The metrics dashboard uses configured dashboard outputs such as ``metrics_dashboard`` and ``dashboard_summaries`` when you pass ``--config`` or set a default config with ``svtk config set``. Only pass explicit paths when you want to override those configured outputs. Prefer ``--metrics-dataset-dir`` and ``--dashboard-summary-table-dir`` for those overrides; ``--metrics-root``, ``--metrics-dataset``, ``--summary-root``, and ``--dashboard-summary-dir`` are legacy aliases. Dashboard URLs follow the same vocabulary: use ``metrics_dataset_dir`` and ``dashboard_summary_table_dir`` for metrics-dashboard query parameters, and ``qc_trace_summary`` for QC-dashboard query parameters. Older ``metrics_root``, ``summary_root``, and ``trace_summary`` query parameters still work for existing links.",
            "",
            ".. code-block:: bash",
            "",
            f"   svtk dashboard status --config {EXAMPLE_CONFIG} --run-scenario tutorial",
            f"   svtk dashboard metrics --config {EXAMPLE_CONFIG} --run-scenario tutorial --auto-port --proxy-mode",
            f"   svtk dashboard qc --config {EXAMPLE_CONFIG} --run-scenario tutorial --auto-port --proxy-mode",
            "",
            "Use ``--auto-port`` when another Streamlit server may already be running and ``--proxy-mode`` when launching through a proxied notebook or remote desktop service.",
            (
                "Run ``svtk dashboard status`` before launching dashboards when outputs are missing, "
                "stale, or unexpectedly sparse. The status table is bounded to metadata and shows the "
                "configured artifact label, dashboard tabs, required columns, missing columns, "
                "map-coordinate blockers, recognized value columns, non-empty value columns, suggested "
                "action, and resolved path without loading large metric or QC inventories."
            ),
            "",
        ]
    if command_name == "call":
        return [
            "Advanced Escape Hatch",
            "---------------------",
            "",
            "Use ``svtk call`` only for public Spatial-VTK functions that do not yet have a curated workflow command. Standard project workflows should use the named command groups because they resolve config-backed paths, expose stable flags, and document expected inputs directly.",
            "",
        ]
    return []


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
    lines.extend(_render_configured_defaults(parser))
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


def _render_configured_defaults(parser: argparse.ArgumentParser) -> list[str]:
    """Render command-specific config-backed defaults for registered figures."""

    spec = parser.get_default("plot_spec")
    if not isinstance(spec, PlotCommand):
        return []
    rows = _registered_default_rows(spec)
    if not rows:
        return []
    lines = [
        ".. rubric:: Configured defaults",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        "   :widths: 20 26 54",
        "",
        "   * - Role",
        "     - Source",
        "     - Meaning",
    ]
    for role, source, meaning in rows:
        lines.extend(
            [
                f"   * - {role}",
                _table_cell(source),
                _table_cell(meaning),
            ]
        )
    lines.append("")
    return lines


def _registered_default_rows(spec: PlotCommand) -> list[tuple[str, str, str]]:
    """Return human-readable default rows for one registered figure command."""

    rows: list[tuple[str, str, str]] = []
    rows.append(("Input table", f"``{_registered_list_input(spec)}``", _registered_input_default_meaning(spec)))
    rows.append(("Output figure", f"``{_registered_list_output(spec)}``", _registered_output_default_meaning(spec)))
    extra_tables = _registered_list_extra_tables(spec)
    if extra_tables != "-":
        rows.append(("Extra tables", f"``{extra_tables}``", _registered_extra_default_meaning(spec)))
    return rows


def _registered_input_default_meaning(spec: PlotCommand) -> str:
    """Return explanatory text for one registered input default."""

    if spec.primary_arg is None:
        return "This command does not read a primary input table."
    if spec.input_key:
        return (
            f"Uses configured output table ``{spec.input_key}`` when ``--config`` is passed "
            "or a default config is set with ``svtk config set``. Override with "
            "``--input-table`` or ``--input``."
        )
    table_meaning = REQUIRED_INPUT_TABLE_MEANINGS.get(str(spec.primary_arg))
    suffix = f" with {table_meaning}" if table_meaning else ""
    return f"No registered default table is available yet. Pass ``--input-table`` or ``--input``{suffix}."


def _registered_output_default_meaning(spec: PlotCommand) -> str:
    """Return explanatory text for one registered output default."""

    if spec.output_key:
        return (
            f"Uses configured figure output ``{spec.output_key}`` when ``--config`` is passed "
            "or a default config is set with ``svtk config set``. Override with "
            "``--figure-output`` or ``--output``."
        )
    return "No registered default figure path is available yet. Pass ``--figure-output`` or ``--output``."


def _registered_extra_default_meaning(spec: PlotCommand) -> str:
    """Return explanatory text for registered extra table flags."""

    defaults = spec.table_alias_defaults or {}
    if defaults:
        aliases = ", ".join(f"``--{name.replace('_', '-')}``" for name in sorted(defaults))
        return f"Uses configured table defaults for {aliases} when a config is active; override with the same named flags."
    return "Optional named table flags are available for this command."


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
                _table_cell(default),
                _table_cell(description),
            ]
        )
    lines.append("")
    return lines


def _table_cell(value: str) -> str:
    """Return one RST list-table cell without trailing whitespace."""

    return f"     - {value}" if value else "     -"


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
        name = f"``{_render_metavar(action.metavar) if action.metavar else action.dest}``"
        required = "Yes"
        default = _default_text(action)
    description = _rst_escape((action.help or "").replace("%(default)s", str(action.default))).strip()
    if action.metavar:
        prefix = _metavar_description_prefix(action.metavar)
        description = f"{prefix} {description}".strip() if prefix else description
    elif action.option_strings and not isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction, argparse._HelpAction)):
        prefix = _description_value_prefix(description)
        description = f"{prefix} {description}".strip() if prefix else description
    return name, required, default, description or ""


def _render_metavar(metavar: object) -> str:
    """Render one argparse metavar for usage and table text."""

    if isinstance(metavar, tuple):
        return " ".join(str(item) for item in metavar)
    return str(metavar)


def _metavar_description_prefix(metavar: object) -> str:
    """Return a human-readable value prefix for common path metavars."""

    if isinstance(metavar, tuple):
        rendered = _render_metavar(metavar)
    else:
        rendered = _render_metavar(metavar)
    normalized = rendered.strip().upper()
    if normalized == "PATH":
        return "Filesystem path."
    if normalized == "DIR":
        return "Directory path."
    if normalized in {"CONFIG", "CONFIG_PATH"}:
        return "Config file path."
    return ""


def _description_value_prefix(description: str) -> str:
    """Infer a human-readable value prefix from one argument description."""

    lowered = description.lower()
    if "not a filesystem path" in lowered or "function_argument=path" in lowered:
        return ""
    if "directory" in lowered or "folder" in lowered:
        return "Directory path."
    path_phrases = (
        "csv/parquet path",
        "geojson path",
        "manifest json",
        "output path",
        "input path",
        "script path",
        "figure path",
        "table path",
        "config file path",
    )
    if any(phrase in lowered for phrase in path_phrases):
        return "Filesystem path."
    return ""


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
