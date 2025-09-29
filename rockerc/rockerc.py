import sys
import subprocess
import pathlib
import yaml
import os
import logging
from typing import List, Tuple, Dict, Any
from tabulate import tabulate

# Unified detached execution & VS Code attach flow helpers
from rockerc.core import (
    derive_container_name,
    prepare_launch_plan,
    execute_plan,
)


#############################################
# Coloring / Formatting Helpers
#############################################


class _Colors:  # pragma: no cover - trivial container
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"


def _use_color() -> bool:
    # Respect NO_COLOR (https://no-color.org/) and only colorize when stdout is a TTY
    if os.environ.get("NO_COLOR") is not None:
        return False
    try:
        return sys.stdout.isatty()
    except Exception:  # pragma: no cover - defensive
        return False


def _c(txt: str, color: str, *, bold: bool = False) -> str:
    if not _use_color():
        return txt
    prefix = color
    if bold:
        prefix += _Colors.BOLD
    return f"{prefix}{txt}{_Colors.RESET}"


def _header(txt: str) -> str:
    return _c(txt, _Colors.BLUE, bold=True)


#############################################
# Extension Table Renderer (new functionality)
#############################################


def render_extension_table(
    final_args: list[str],
    *,
    original_global_args: list[str] | None,
    original_project_args: list[str] | None,
    blacklist: list[str],
    removed_by_blacklist: list[str],
) -> None:
    """Render a provenance table of extensions.

    Consumes pre-computed metadata – does NOT perform merge/filter logic.
    Columns (updated): Global | Local | Status
    The previous redundant 'Extension' column (duplicating the name) was removed.
    Group order: global-only, shared, local-only (stable original order).
    Blacklisted entries appear with strikethrough & red status in-place.
    """

    g_raw = original_global_args or []
    p_raw = original_project_args or []
    g_set = set(g_raw)
    p_set = set(p_raw)
    bl_set = set(blacklist)
    removed_set = set(removed_by_blacklist)
    final_set = set(final_args)

    # Ordered grouping per corrected spec: precedence by provenance group only, preserving
    # original encounter order within each group (no alphabetical sorting).
    # We derive a stable first-seen index from the concatenation of (g_raw + p_raw).
    first_seen: dict[str, int] = {}
    for idx, name in enumerate(g_raw + p_raw):
        if name not in first_seen:
            first_seen[name] = idx

    def group_rank(name: str) -> int:
        in_g = name in g_set
        in_p = name in p_set
        if in_g and not in_p:
            return 0  # global-only
        if in_g and in_p:
            return 1  # shared
        if in_p and not in_g:
            return 2  # local-only
        return 3  # unknown / fallback (should not happen)

    # Collect unique names from provenance sets for grouping
    unique_names: list[str] = []
    for name in g_raw + p_raw:
        if name not in unique_names:
            unique_names.append(name)

    # Partition per group preserving stable order via first_seen
    global_only_names = [n for n in unique_names if group_rank(n) == 0]
    shared_names = [n for n in unique_names if group_rank(n) == 1]
    local_only_names = [n for n in unique_names if group_rank(n) == 2]

    # We retain previous defensive insertion semantics by later injecting removed_by_blacklist
    ordered = (
        global_only_names + shared_names + local_only_names
    )  # used for removal reinsertion only

    # Normalize any accidental aggregated tokens like "nvidia - x11 - user" (display only)
    def _expand_aggregates(ext_list: list[str]) -> list[str]:
        expanded: list[str] = []
        # We relax the requirement that parts already appear in provenance; if a tokenized
        # aggregate arrives we still expand it for clearer display.
        for item in ext_list:
            if " - " in item and not item.strip().startswith("-"):
                parts = [p.strip() for p in item.split(" - ") if p.strip()]
                # Only expand if every part looks like a plausible extension token
                if parts and all(part.replace("-", "").isalnum() for part in parts):
                    for p in parts:
                        if p not in expanded:  # avoid duplicating earlier entries
                            expanded.append(p)
                    continue
            expanded.append(item)
        return expanded

    # Expand aggregates and, if expansion occurred in project or global lists, update provenance
    expanded_ordered = _expand_aggregates(ordered)
    if expanded_ordered != ordered:
        # Rebuild raw lists similarly so membership columns reflect correct provenance
        g_raw = _expand_aggregates(g_raw)
        p_raw = _expand_aggregates(p_raw)
        g_set = set(g_raw)
        p_set = set(p_raw)
        # Recompute unique names & group partitions to include expanded tokens
        unique_names = []
        for name in g_raw + p_raw:
            if name not in unique_names:
                unique_names.append(name)
        global_only_names = [n for n in unique_names if (n in g_set and n not in p_set)]
        shared_names = [n for n in unique_names if (n in g_set and n in p_set)]
        local_only_names = [n for n in unique_names if (n in p_set and n not in g_set)]
        ordered = expanded_ordered
    else:
        ordered = expanded_ordered

    # Defensive: ensure any removed/blacklisted not in ordered are injected according to rank
    for ext in removed_by_blacklist:
        if ext in ordered:
            continue
        r = group_rank(ext)
        if r == 0:
            # Insert before first non global-only
            first_non_global = next(
                (i for i, n in enumerate(ordered) if group_rank(n) != 0), len(ordered)
            )
            ordered.insert(first_non_global, ext)
        elif r == 1:
            # After last shared (or after all global-only if none shared yet)
            last_shared_pos = -1
            for i, n in enumerate(ordered):
                if group_rank(n) == 1:
                    last_shared_pos = i
            if last_shared_pos >= 0:
                ordered.insert(last_shared_pos + 1, ext)
            else:
                # after all global-only
                after_globals = next(
                    (i for i, n in enumerate(ordered) if group_rank(n) != 0), len(ordered)
                )
                ordered.insert(after_globals, ext)
        elif r == 2:
            # Append at end (local-only segment is last)
            ordered.append(ext)
        else:
            ordered.append(ext)

    use_color = _use_color()

    def strike(txt: str) -> str:
        if not txt:
            return txt
        if use_color:
            return f"\033[9m{txt}\033[0m"
        return f"<del>{txt}</del>"

    def color(txt: str, code: str, bold: bool = False) -> str:
        if not use_color:
            return txt
        prefix = code
        if bold:
            prefix += _Colors.BOLD
        return f"{prefix}{txt}{_Colors.RESET}"

    def build_single_row(ext: str) -> list[str]:
        if ext in final_set:
            status = "loaded"
        elif ext in removed_set:
            status = "blacklisted"
        elif ext in bl_set:
            status = "filtered"
        else:
            status = "loaded"

        def fmt_cell(ext_name: str, show: bool, state: str) -> str:
            if not show:
                return ""
            cell_txt = ext_name
            if state == "loaded":
                cell_txt = color(cell_txt, _Colors.CYAN)
            elif state == "blacklisted":
                cell_txt = color(cell_txt, _Colors.RED)
                cell_txt = strike(cell_txt)
            elif state == "filtered":
                cell_txt = color(cell_txt, _Colors.YELLOW)
            return cell_txt

        global_cell = fmt_cell(ext, ext in g_set, status)
        local_cell = fmt_cell(ext, ext in p_set, status)
        if status == "loaded":
            status_txt = color(status, _Colors.GREEN)
        elif status == "blacklisted":
            status_txt = color(status, _Colors.RED)
        else:
            status_txt = color(status, _Colors.YELLOW)
        return [global_cell, local_cell, status_txt]

    # Build three explicit 2D arrays
    global_rows = [build_single_row(ext) for ext in global_only_names]
    shared_rows = [build_single_row(ext) for ext in shared_names]
    local_rows = [build_single_row(ext) for ext in local_only_names]

    all_rows = global_rows + shared_rows + local_rows
    if all_rows:
        headers = ["Global", "Local", "Status"]
        if use_color:
            headers = [f"{_Colors.CYAN}{_Colors.BOLD}{h}{_Colors.RESET}" for h in headers]
        print(tabulate(all_rows, headers=headers, tablefmt="plain"))


def yaml_dict_to_args(d: dict, extra_args: str = "") -> str:
    """Given a dictionary of arguments turn it into an argument string to pass to rocker

    Args:
        d (dict): rocker arguments dictionary
        extra_args (str): additional command line arguments to insert before the image

    Returns:
        str: rocker arguments string
    """
    image = d.pop("image", None)
    segments = []

    # explicit flags
    for a in d.pop("args", []):
        segments.append(f"--{a}")

    # special handling for extension-blacklist
    extension_blacklist = d.pop("extension-blacklist", None)
    if extension_blacklist:
        if isinstance(extension_blacklist, list):
            for extension in extension_blacklist:
                segments.extend(["--extension-blacklist", str(extension)])
        else:
            segments.extend(["--extension-blacklist", str(extension_blacklist)])

    # key/value pairs
    for k, v in d.items():
        segments.extend([f"--{k}", str(v)])

    # any extra CLI pieces - keep as string to preserve complex quoting
    cmd_str = " ".join(segments)
    if extra_args:
        cmd_str += f" {extra_args}"

    # separator + image
    if image:
        cmd_str += f" -- {image}"

    return cmd_str


def load_global_config() -> dict:
    """Load global rockerc configuration from ~/.rockerc.yaml

    Returns:
        dict: Parsed configuration dictionary, or empty dict if parsing fails.
    """
    config_path = pathlib.Path.home() / ".rockerc.yaml"
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        logging.warning(f"Failed to parse YAML config at {config_path}: {e}")
        return {}
    except Exception as e:
        logging.warning(f"Error loading config at {config_path}: {e}")
        return {}


def deduplicate_extensions(extensions: list) -> list:
    """Remove duplicate extensions while preserving order

    Args:
        extensions (list): List of extension names

    Returns:
        list: Deduplicated list of extensions
    """
    seen = set()
    result = []
    for ext in extensions:
        if ext not in seen:
            seen.add(ext)
            result.append(ext)
    return result


def collect_arguments(path: str = ".") -> dict:
    """Search for rockerc.yaml files and return a merged dictionary

    Args:
        path (str, optional): path to reach for files. Defaults to ".".

    Returns:
        dict: A dictionary of merged rockerc arguments
    """
    # Load global config first
    global_config = load_global_config()

    # Load project-specific config
    search_path = pathlib.Path(path)
    merged_dict = {}
    for p in search_path.glob("rockerc.yaml"):
        print(f"loading {p}")

        with open(p.as_posix(), "r", encoding="utf-8") as f:
            merged_dict.update(yaml.safe_load(f))

    # Start with global config as base, then override with project-specific settings
    final_dict = global_config | merged_dict

    # Special handling for args - merge and deduplicate instead of overriding
    global_args = global_config.get("args", [])
    project_args = merged_dict.get("args", [])
    if global_args or project_args:
        final_dict["args"] = deduplicate_extensions(global_args + project_args)

    # Special handling for extension-blacklist - merge lists instead of overriding
    global_blacklist = global_config.get("extension-blacklist", [])
    project_blacklist = merged_dict.get("extension-blacklist", [])

    # Ensure they are lists for consistent handling
    if not isinstance(global_blacklist, list):
        global_blacklist = [global_blacklist] if global_blacklist else []
    if not isinstance(project_blacklist, list):
        project_blacklist = [project_blacklist] if project_blacklist else []

    if global_blacklist or project_blacklist:
        final_dict["extension-blacklist"] = deduplicate_extensions(
            global_blacklist + project_blacklist
        )

    # Filter out blacklisted extensions from args
    if "extension-blacklist" in final_dict and "args" in final_dict:
        blacklisted_extensions = set(final_dict["extension-blacklist"])
        filtered_args = [arg for arg in final_dict["args"] if arg not in blacklisted_extensions]
        final_dict["args"] = filtered_args

    return final_dict


def collect_arguments_with_meta(path: str = ".") -> tuple[dict, dict]:
    """Enhanced variant of collect_arguments returning (final_config, metadata).

    Metadata contains:
      original_global_args: list | None
      original_project_args: list | None
      merged_args_before_blacklist: list
      removed_by_blacklist: list
      blacklist: list
      global_config_used: bool
      project_config_used: bool
      source_files: list[str]
    """
    # Load global & project similar to collect_arguments, but keep more info
    config_path = pathlib.Path.home() / ".rockerc.yaml"
    global_config: Dict[str, Any] = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                global_config = yaml.safe_load(f) or {}
        except Exception:  # pragma: no cover - fallback
            global_config = {}

    search_path = pathlib.Path(path)
    project_config: Dict[str, Any] = {}
    project_files: List[str] = []
    for p in search_path.glob("rockerc.yaml"):
        project_files.append(p.as_posix())
        with open(p.as_posix(), "r", encoding="utf-8") as f:
            project_config.update(yaml.safe_load(f) or {})

    final_dict: Dict[str, Any] = global_config | project_config

    g_args = global_config.get("args", []) or []
    p_args = project_config.get("args", []) or []
    merged_args = []
    if g_args or p_args:
        merged_args = deduplicate_extensions(g_args + p_args)
        final_dict["args"] = merged_args.copy()

    g_bl = global_config.get("extension-blacklist", []) or []
    p_bl = project_config.get("extension-blacklist", []) or []

    if not isinstance(g_bl, list):
        g_bl = [g_bl]
    if not isinstance(p_bl, list):
        p_bl = [p_bl]

    if g_bl or p_bl:
        blacklist = deduplicate_extensions(g_bl + p_bl)
        final_dict["extension-blacklist"] = blacklist
    else:
        blacklist = []

    removed: List[str] = []
    if blacklist and merged_args:
        removed = [a for a in merged_args if a in set(blacklist)]
        final_dict["args"] = [a for a in merged_args if a not in set(blacklist)]

    meta = {
        "original_global_args": g_args or None,
        "original_project_args": p_args or None,
        "merged_args_before_blacklist": merged_args,
        "removed_by_blacklist": removed,
        "blacklist": blacklist,
        "global_config_used": bool(global_config),
        "project_config_used": bool(project_config),
        "source_files": project_files,
    }
    return final_dict, meta


def build_docker(dockerfile_path: str = ".") -> str:
    """Build a Docker image from a Dockerfile and return an autogenerated image tag based on where rocker was run.

    Args:
        dockerfile_path (str, optional): Path to the Dockerfile. Defaults to ".".

    Returns:
        str: The tag of the built Docker image.
    """

    tag = f"{pathlib.Path().absolute().name.lower()}:latest"
    dockerfile_dir = pathlib.Path(dockerfile_path).absolute().parent
    subprocess.call(["docker", "build", "-t", tag, str(dockerfile_dir)])
    return tag


def save_rocker_cmd(split_cmd: List[str]) -> str | None:
    dry_run = split_cmd + ["--mode", "dry-run"]
    try:
        s = subprocess.run(dry_run, capture_output=True, text=True, check=True)
        output = s.stdout
        # Split by "vvvvvv" to discard the top section
        _, after_vvvvvv = output.split("vvvvvv", 1)
        # Split by "^^^^^^" to get the second section
        section_to_save, after_caret = after_vvvvvv.split("^^^^^^", 1)
        # Save the Dockerfile section
        dockerfile_content = section_to_save.strip()
        with open("Dockerfile.rocker", "w", encoding="utf-8") as dockerfile:
            dockerfile.write("#This file was autogenerated by rockerc\n")
            dockerfile.write(dockerfile_content)
        # Find the "run this command" section
        run_command_section = after_caret.split("Run this command: ", 1)[-1].strip()
        formatted_script_lines = []
        lines = run_command_section.split()
        formatted_script_lines.append("#!/bin/bash")
        formatted_script_lines.append("# This file was autogenerated by rockerc")
        formatted_script_lines.append("docker run \\")

        for i, line in enumerate(
            lines[2:], start=2
        ):  # Skip 'docker run' which is split in the first two items
            if i < len(lines) - 1:
                formatted_script_lines.append(f"  {line} \\")
            else:
                formatted_script_lines.append(f"  {line}")

        formatted_script_content = "\n".join(formatted_script_lines)

        bash_script_path = "run_dockerfile.sh"
        with open(bash_script_path, "w", encoding="utf-8") as bash_script:
            bash_script.write(formatted_script_content)

        # Make the bash script executable
        os.chmod(bash_script_path, 0o755)

        logging.info(
            "Saved generated Dockerfile to Dockerfile.rocker and launch script to %s",
            bash_script_path,
        )
        return dockerfile_content
    except subprocess.CalledProcessError as e:
        logging.error("[rockerc] Error: rocker dry-run failed.")
        logging.error(f"[rockerc] Command: {' '.join(dry_run)}")
        logging.error(f"[rockerc] Exit code: {e.returncode}")
        logging.error(f"[rockerc] Output:\n{e.stdout}")
        logging.error(f"[rockerc] Error output:\n{e.stderr}")
        logging.error(
            "[rockerc] This likely means rocker or one of its extensions failed to generate a Dockerfile. Please check your rockerc.yaml and rocker installation."
        )
        sys.exit(e.returncode)
    except ValueError as e:
        logging.error(f"[rockerc] Error processing the output from rocker dry-run: {e}")
        logging.error(
            "[rockerc] The output format may have changed or rocker failed to generate the expected output."
        )
        sys.exit(1)
    return None


def _parse_extra_flags(argv: List[str]) -> Tuple[bool, bool, bool, List[str]]:
    """Parse ad-hoc flags for --vsc, --force and --verbose.

    Returns: (vsc, force, verbose, remaining_args)
    """
    vsc = False
    force = False
    verbose = False
    remaining: List[str] = []
    for a in argv:
        if a == "--vsc":
            vsc = True
            continue
        if a in ("--force", "-f"):
            force = True
            continue
        if a in ("--verbose", "-v"):
            verbose = True
            continue
        remaining.append(a)
    return vsc, force, verbose, remaining


def _configure_logging(verbose: bool):  # pragma: no cover - formatting only
    # Remove any existing handlers (avoid duplicate logs when called multiple times)
    root = logging.getLogger()
    if root.handlers:
        for h in list(root.handlers):
            root.removeHandler(h)

    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler()

    def format_record(record: logging.LogRecord) -> str:
        level_color = {
            "DEBUG": _Colors.MAGENTA,
            "INFO": _Colors.GREEN,
            "WARNING": _Colors.YELLOW,
            "ERROR": _Colors.RED,
            "CRITICAL": _Colors.RED,
        }.get(record.levelname, _Colors.CYAN)
        prefix = _c(record.levelname, level_color, bold=True)
        msg = record.getMessage()
        return f"{prefix}: {msg}"

    class _Formatter(logging.Formatter):  # pragma: no cover - trivial
        def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
            return format_record(record)

    handler.setFormatter(_Formatter())
    root.addHandler(handler)
    root.setLevel(level)


def run_rockerc(path: str = "."):
    """Unified rockerc entry point (always-detached model).

    Behavior:
    1. Collect + merge configuration.
    2. Optionally build Dockerfile if 'dockerfile' key present.
    3. Support --create-dockerfile to emit a generated Dockerfile + run script.
    4. Always ensure container is (or becomes) detached so we can exec a shell.
    5. Optional VS Code attach with --vsc.
    6. Reuse existing container unless --force provided.
    """

    # Raw arguments after script name
    cli_args = sys.argv[1:]
    vsc, force, verbose, filtered_cli = _parse_extra_flags(cli_args)

    _configure_logging(verbose)

    # Suppress banner printing per user request (previously printed 'rockerc' header)

    merged_dict, meta = collect_arguments_with_meta(path)

    if not merged_dict:
        logging.error(
            "No rockerc.yaml found in the specified directory. Please create a rockerc.yaml file with rocker arguments. See 'rocker -h' for help."
        )
        sys.exit(1)

    if "args" not in merged_dict:
        logging.error(
            "No 'args' key found in rockerc.yaml. Please add an 'args' list with rocker arguments. See 'rocker -h' for help."
        )
        sys.exit(1)

    # Dockerfile build handling
    if "dockerfile" in merged_dict:
        logging.info("Dockerfile specified -> building image locally")
        merged_dict["image"] = build_docker(merged_dict["dockerfile"])
        logging.info("Disabling 'pull' extension because a local Dockerfile was used")
        if "pull" in merged_dict["args"]:
            merged_dict["args"].remove("pull")
        merged_dict.pop("dockerfile")

    # create-dockerfile mode
    create_dockerfile = False
    if "create-dockerfile" in merged_dict["args"]:
        merged_dict["args"].remove("create-dockerfile")
        create_dockerfile = True

    # Detect explicit container name in user filtered args (very naive: look for --name <value>)
    explicit_name = None
    if "--name" in filtered_cli:
        try:
            idx = filtered_cli.index("--name")
            explicit_name = filtered_cli[idx + 1]
        except (ValueError, IndexError):  # pragma: no cover - defensive
            pass

    container_name = derive_container_name(explicit_name)

    # Remaining CLI (space-preserved) for injection pass
    extra_cli = " ".join(filtered_cli)

    plan = prepare_launch_plan(
        merged_dict,
        extra_cli,
        container_name,
        vsc,
        force,
        pathlib.Path(path).absolute(),
    )

    # Render new provenance table (replaces prior summary block)
    render_extension_table(
        merged_dict.get("args", []),
        original_global_args=meta.get("original_global_args"),
        original_project_args=meta.get("original_project_args"),
        blacklist=meta.get("blacklist", []),
        removed_by_blacklist=meta.get("removed_by_blacklist", []),
    )

    # Show origin info (only if verbose to reduce noise)
    if verbose:
        origins: List[str] = []
        if meta.get("global_config_used"):
            origins.append("global ~/.rockerc.yaml")
        if meta.get("project_config_used"):
            origins.append("project rockerc.yaml")
        if origins:
            print(_c("Sources:", _Colors.DIM, bold=True), _c(", ".join(origins), _Colors.DIM))
        if meta.get("original_global_args"):
            print(
                _c("Global args:", _Colors.DIM, bold=True),
                _c(", ".join(meta["original_global_args"]), _Colors.DIM),
            )
        if meta.get("original_project_args"):
            print(
                _c("Project args:", _Colors.DIM, bold=True),
                _c(", ".join(meta["original_project_args"]), _Colors.DIM),
            )
        if meta.get("merged_args_before_blacklist"):
            print(
                _c("Merged (pre-blacklist):", _Colors.DIM, bold=True),
                _c(", ".join(meta["merged_args_before_blacklist"]), _Colors.DIM),
            )

    if create_dockerfile and plan.rocker_cmd:
        dockerfile_content = save_rocker_cmd(plan.rocker_cmd)
        if verbose and dockerfile_content:
            print(_header("Generated Dockerfile (Dockerfile.rocker):"))
            print(_c(dockerfile_content, _Colors.DIM))
            print(_c("(End Dockerfile)", _Colors.DIM))

    exit_code = execute_plan(plan)
    sys.exit(exit_code)


if __name__ == "__main__":
    run_rockerc()
