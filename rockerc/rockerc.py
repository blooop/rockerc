import sys
import subprocess
import pathlib
import yaml
import shlex
import os
import logging
import json
from collections import OrderedDict
import re


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

    # key/value pairs
    for k, v in d.items():
        if isinstance(v, list):
            # For list values, add each item as a separate argument
            for item in v:
                segments.extend([f"--{k}", str(item)])
        else:
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


def inspect_container(container_name_or_id: str) -> dict:
    """Inspect a Docker container and extract relevant run options

    Args:
        container_name_or_id (str): Container name or ID to inspect

    Returns:
        dict: Dictionary containing extracted container options suitable for rocker

    Raises:
        subprocess.CalledProcessError: If docker inspect fails
        ValueError: If container data cannot be parsed
    """
    try:
        # Get container details using docker inspect
        result = subprocess.run(
            ["docker", "inspect", container_name_or_id], capture_output=True, text=True, check=True
        )

        container_data = json.loads(result.stdout)[0]

        # Extract relevant information
        config = container_data.get("Config", {})
        host_config = container_data.get("HostConfig", {})

        # Build rocker-compatible options
        rocker_options = {}

        # Get the image
        rocker_options["image"] = config.get("Image", "")

        # Extract environment variables
        env_vars = config.get("Env", [])
        if env_vars:
            # Filter out PATH and other system vars, keep user-defined ones
            system_prefixes = ["PATH=", "HOSTNAME=", "HOME=", "PWD="]
            filtered_env = [
                env
                for env in env_vars
                if not any(env.startswith(prefix) for prefix in system_prefixes)
            ]
            if filtered_env:
                rocker_options["env"] = filtered_env

        # Extract volumes/bind mounts
        binds = host_config.get("Binds", [])
        if binds:
            volumes = []
            for bind in binds:
                parts = bind.split(":")
                if len(parts) >= 2:
                    source, target = parts[0], parts[1]
                    mode = parts[2] if len(parts) > 2 else "rw"
                    volumes.append(f"{source}:{target}:{mode}")
            if volumes:
                rocker_options["volume"] = volumes

        # Extract port mappings
        port_bindings = host_config.get("PortBindings", {})
        ports = []
        for container_port, host_bindings in port_bindings.items():
            if not host_bindings:
                continue
            for binding in host_bindings:
                host_port = binding.get("HostPort", "")
                if host_port:
                    ports.append(f"{host_port}:{container_port}")
        if ports:
            rocker_options["port"] = ports

        # Extract working directory (commented out for now as rocker doesn't have direct support)
        # workdir = config.get("WorkingDir", "")
        # if workdir:
        #     # Use oyr-run-arg to pass --workdir to docker run
        #     rocker_options["oyr-run-arg"] = [f"'--workdir {workdir}'"]

        # Extract user
        user = config.get("User", "")
        if user:
            rocker_options["user"] = user

        # Extract devices
        devices = host_config.get("Devices", [])
        device_mappings = []
        for device in devices:
            path_on_host = device.get("PathOnHost", "")
            path_in_container = device.get("PathInContainer", "")
            if path_on_host and path_in_container:
                device_mappings.append(f"{path_on_host}:{path_in_container}")
        if device_mappings:
            rocker_options["device"] = device_mappings

        # Extract capabilities
        cap_add = host_config.get("CapAdd", [])
        if cap_add and cap_add != [None]:
            rocker_options["cap-add"] = cap_add

        # Extract privileged mode
        if host_config.get("Privileged", False):
            rocker_options["privileged"] = True

        # Extract network mode
        network_mode = host_config.get("NetworkMode", "")
        if network_mode and network_mode not in ["default", "bridge"]:
            rocker_options["network"] = network_mode

        return rocker_options

    except subprocess.CalledProcessError as e:
        raise subprocess.CalledProcessError(
            e.returncode, e.cmd, f"Failed to inspect container '{container_name_or_id}': {e.stderr}"
        )
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        raise ValueError(f"Failed to parse container data for '{container_name_or_id}': {e}") from e


def generate_container_name(original_name: str, suffix: str = "rockerc") -> str:
    """Generate a new container name, handling collisions

    Args:
        original_name (str): Original container name
        suffix (str): Suffix to append (default: "rockerc")

    Returns:
        str: New unique container name
    """
    base_name = f"{original_name}-{suffix}"

    # Check if the base name is available
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={base_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True,
        )

        if base_name not in result.stdout.splitlines():
            return base_name

        # If collision, add a short random suffix
        import random
        import string

        short_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"{base_name}-{short_suffix}"

    except subprocess.CalledProcessError:
        # If docker command fails, just return the base name
        return base_name


def merge_container_options_with_config(container_options: dict, config_dict: dict) -> dict:
    """Merge container options with rockerc.yaml configuration

    Args:
        container_options (dict): Options extracted from container inspection
        config_dict (dict): Configuration from rockerc.yaml files

    Returns:
        dict: Merged configuration with container options as base and config overrides
    """
    merged = {key: _copy_value(value) for key, value in container_options.items()}

    # Handle args specially - these are rocker extensions
    if "args" in config_dict:
        merged["args"] = deduplicate_extensions(_normalize_simple_list(config_dict.get("args", [])))
        args = merged["args"]
        if "user" in args and "user" in merged:
            merged.pop("user", None)
    elif "args" in merged:
        merged["args"] = deduplicate_extensions(_normalize_simple_list(merged["args"]))

    list_handlers = {
        "env": lambda c, cfg: _merge_keyed_items(c, cfg, _normalize_env_list, _env_key),
        "volume": lambda c, cfg: _merge_keyed_items(c, cfg, _normalize_volume_list, _volume_key),
        "port": lambda c, cfg: _merge_keyed_items(c, cfg, _normalize_port_list, _port_key),
        "device": lambda c, cfg: _merge_keyed_items(c, cfg, _normalize_device_list, _device_key),
        "cap-add": _merge_simple_items,
    }

    for key, handler in list_handlers.items():
        container_value = container_options.get(key)
        config_value = config_dict.get(key)
        merged_value = handler(container_value, config_value)
        if merged_value is None:
            continue
        if merged_value:
            merged[key] = merged_value
        else:
            merged.pop(key, None)

    for key, value in config_dict.items():
        if key in ("args", "env", "volume", "port", "device", "cap-add"):
            continue
        merged[key] = _copy_value(value)

    return merged


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


def _copy_value(value):
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    return value


def _is_explicitly_empty(value) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _strip_outer_quotes(value: str) -> str:
    if not value:
        return value
    if (value[0] == value[-1]) and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _normalize_env_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        normalized = []
        for key, val in value.items():
            if val is None or val == "":
                normalized.append(str(key))
            else:
                normalized.append(f"{key}={val}")
        return normalized
    items = value if isinstance(value, list) else [value]
    normalized = []
    for item in items:
        if item is None:
            continue
        normalized.append(str(item).strip())
    return normalized


def _env_key(entry: str) -> str:
    if "=" in entry:
        return entry.split("=", 1)[0]
    return entry


def _split_volume_entry(entry: str) -> tuple[str | None, str | None, str | None]:
    if not entry:
        return None, None, None
    cleaned = _strip_outer_quotes(entry.strip())
    key_value_target = _extract_target_from_key_value(cleaned)
    if key_value_target:
        # key/value syntax handled separately
        return cleaned, key_value_target, None

    parts = cleaned.rsplit(":", 2)
    if len(parts) == 1:
        return parts[0], None, None
    if len(parts) == 2:
        return parts[0], parts[1], None
    return parts[0], parts[1], parts[2]


def _extract_target_from_key_value(entry: str) -> str | None:
    if "target=" not in entry:
        return None
    for segment in entry.split(","):
        segment = segment.strip()
        if segment.startswith("target="):
            return _strip_outer_quotes(segment.split("=", 1)[1])
    return None


def _normalize_volume_list(value) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    normalized = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _volume_key(entry: str) -> str | tuple[str | None, str | None]:
    if not entry:
        return entry
    cleaned = entry.strip()
    unquoted = _strip_outer_quotes(cleaned)
    key_value_target = _extract_target_from_key_value(unquoted)
    if key_value_target:
        return key_value_target
    source, target, _mode = _split_volume_entry(unquoted)
    key_target = _strip_outer_quotes(target) if target else None
    key_source = _strip_outer_quotes(source) if source else None
    return key_target or key_source or unquoted


def _normalize_device_list(value) -> list[str]:
    return _normalize_volume_list(value)


def _device_key(entry: str):
    if not entry:
        return entry
    cleaned = _strip_outer_quotes(entry.strip())
    parts = cleaned.rsplit(":", 2)
    if len(parts) >= 2:
        return _strip_outer_quotes(parts[1])
    return cleaned


def _normalize_port_list(value) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    normalized = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _port_key(entry: str):
    if not entry:
        return entry
    cleaned = entry.strip()
    segments = cleaned.split(":")
    if not segments:
        return cleaned
    return segments[-1]


def _normalize_simple_list(value) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    normalized = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _volume_target(entry: str) -> str | None:
    if not entry:
        return None
    cleaned = _strip_outer_quotes(str(entry).strip())
    key_value_target = _extract_target_from_key_value(cleaned)
    if key_value_target:
        return key_value_target
    source, target, _mode = _split_volume_entry(cleaned)
    if target:
        return _strip_outer_quotes(target)
    if source:
        return _strip_outer_quotes(source)
    return None


def _remove_volume_target(merged_dict: dict, target: str) -> bool:
    if not target:
        return False
    volumes = merged_dict.get("volume")
    if not volumes:
        return False

    normalized_target = target.strip()
    updated = []
    removed = False
    for entry in _normalize_volume_list(volumes):
        entry_target = _volume_target(entry)
        if entry_target and entry_target.strip() == normalized_target:
            removed = True
            continue
        updated.append(entry)

    if removed:
        if updated:
            merged_dict["volume"] = updated
        else:
            merged_dict.pop("volume", None)
    return removed


def _extract_duplicate_mount_target(stderr_output: str) -> str | None:
    if not stderr_output:
        return None
    # docker errors can include quotes or trailing newline; capture path conservatively
    match = re.search(r"Duplicate mount point: (?P<path>\S+)", stderr_output)
    if match:
        return match.group("path")
    return None


def _merge_keyed_items(container_value, config_value, normalize_fn, key_fn):
    container_list = normalize_fn(container_value)
    config_list = normalize_fn(config_value)
    explicit_empty = _is_explicitly_empty(config_value)

    if explicit_empty and config_value is not None and not config_list:
        return []

    if not container_list and not config_list:
        return [] if explicit_empty else None

    items = OrderedDict()

    def add_entry(entry):
        key = key_fn(entry)
        key_obj = (None, entry) if key is None else key
        items[key_obj] = entry

    for entry in container_list:
        add_entry(entry)

    for entry in config_list:
        add_entry(entry)

    result = [value for value in items.values() if value not in (None, "")]
    if not result and (config_value is not None or explicit_empty):
        return []
    return result or None


def _merge_simple_items(container_value, config_value):
    container_list = _normalize_simple_list(container_value)
    config_list = _normalize_simple_list(config_value)
    explicit_empty = _is_explicitly_empty(config_value)

    if explicit_empty and config_value is not None and not config_list:
        return []

    if not container_list and not config_list:
        return [] if explicit_empty else None

    seen = set()
    result = []

    for entry in container_list + config_list:
        if entry not in seen:
            seen.add(entry)
            result.append(entry)

    if not result and (config_value is not None or explicit_empty):
        return []
    return result or None


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

    return final_dict


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


def save_rocker_cmd(split_cmd: str):
    dry_run = split_cmd + ["--mode", "dry-run"]
    try:
        s = subprocess.run(dry_run, capture_output=True, text=True, check=True)
        output = s.stdout
        # Split by "vvvvvv" to discard the top section
        _, after_vvvvvv = output.split("vvvvvv", 1)
        # Split by "^^^^^^" to get the second section
        section_to_save, after_caret = after_vvvvvv.split("^^^^^^", 1)
        # Save the Dockerfile section
        with open("Dockerfile.rocker", "w", encoding="utf-8") as dockerfile:
            dockerfile.write("#This file was autogenerated by rockerc\n")  # Add the shebang
            dockerfile.write(section_to_save.strip())
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
            f"Files have been saved:\n - Dockerfile.rocker\n - {bash_script_path} (executable)"
        )
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


def run_rockerc(path: str = "."):
    """run rockerc by searching for rocker.yaml in the specified directory and passing those arguments to rocker

    Args:
        path (str, optional): Search path for rockerc.yaml files. Defaults to ".".
    """

    logging.basicConfig(level=logging.INFO)

    # Parse command line arguments for --from-container
    from_container = None
    create_dockerfile = False
    remaining_args = []

    i = 0
    while i < len(sys.argv):
        if i == 0:  # Skip script name
            i += 1
            continue

        arg = sys.argv[i]
        if arg == "--from-container":
            if i + 1 < len(sys.argv):
                from_container = sys.argv[i + 1]
                i += 2  # Skip both --from-container and its value
            else:
                logging.error("--from-container requires a container name or ID")
                sys.exit(1)
        elif arg == "--create-dockerfile":
            create_dockerfile = True
            i += 1
        else:
            remaining_args.append(arg)
            i += 1

    # Handle --from-container workflow
    if from_container:
        logging.info(f"Deriving container from existing container: {from_container}")

        try:
            # Inspect the source container
            container_options = inspect_container(from_container)
            logging.info(f"Successfully inspected container '{from_container}'")

            # Load rockerc.yaml configuration
            config_dict = collect_arguments(path)

            # If no rockerc.yaml found, create minimal config with just args
            if not config_dict:
                logging.warning(
                    "No rockerc.yaml found. Using only container options with default extensions."
                )
                config_dict = {"args": []}

            # Ensure args exist
            if "args" not in config_dict:
                config_dict["args"] = []

            # Merge container options with config
            merged_dict = merge_container_options_with_config(container_options, config_dict)

            # Generate new container name
            original_name = from_container
            # If from_container is a container ID, get the actual name
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format", "{{.Name}}", from_container],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                # Remove leading slash from container name
                original_name = result.stdout.strip().lstrip("/")
            except subprocess.CalledProcessError:
                # If we can't get the name, use the ID/name as provided
                pass

            new_container_name = generate_container_name(original_name)
            merged_dict["name"] = new_container_name

            logging.info(f"New container will be named: {new_container_name}")

        except (subprocess.CalledProcessError, ValueError) as e:
            logging.error(f"Failed to process container '{from_container}': {e}")
            sys.exit(1)

    else:
        # Standard workflow - load from rockerc.yaml
        merged_dict = collect_arguments(path)

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

    # Handle dockerfile building
    if "dockerfile" in merged_dict:
        logging.info("Building dockerfile...")
        merged_dict["image"] = build_docker(merged_dict["dockerfile"])
        logging.info("disabling 'pull' extension as a Dockerfile is used instead")
        if "pull" in merged_dict["args"]:
            merged_dict["args"].remove("pull")  # can't pull as we just build image
        # remove the dockerfile command as it does not need to be passed onto rocker
        merged_dict.pop("dockerfile")

    # Handle create-dockerfile from args or CLI
    if "create-dockerfile" in merged_dict.get("args", []):
        merged_dict["args"].remove("create-dockerfile")
        create_dockerfile = True

    # Build extra args from remaining CLI arguments
    extra_args = " ".join(remaining_args) if remaining_args else ""

    attempts = 0
    max_attempts = 5
    dockerfile_saved = False

    while True:
        cmd_args = yaml_dict_to_args(merged_dict, extra_args)
        if len(cmd_args) == 0:
            break

        cmd = f"rocker {cmd_args}"
        logging.info(f"running cmd: {cmd}")
        split_cmd = shlex.split(cmd)

        if create_dockerfile and not dockerfile_saved:
            save_rocker_cmd(split_cmd)
            dockerfile_saved = True

        try:
            result = subprocess.run(split_cmd, check=True, stderr=subprocess.PIPE, text=True)
            if result.stderr:
                sys.stderr.write(result.stderr)
            return
        except subprocess.CalledProcessError as e:
            duplicate_target = _extract_duplicate_mount_target(
                (e.stderr or "") + ("\n" + e.stdout if getattr(e, "stdout", None) else "")
            )
            if duplicate_target and attempts < max_attempts:
                if _remove_volume_target(merged_dict, duplicate_target):
                    attempts += 1
                    logging.warning(
                        "Detected duplicate mount point '%s'. Removing container mount and retrying.",
                        duplicate_target,
                    )
                    continue
            raise

    logging.error(
        "no arguments found in rockerc.yaml. Please add rocker arguments as described in rocker -h:"
    )
    subprocess.call("rocker -h", shell=True)


if __name__ == "__main__":
    run_rockerc()
