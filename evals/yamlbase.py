#!/usr/bin/env python3
"""
yamlbase.py — YAML loader with $base inheritance.

Features:
- Any mapping (dict) may contain a `$base` key whose value is a YAML file path.
- The referenced YAML is loaded and used as the base for that mapping.
- Other keys in the mapping extend/override the base via deep-merge.
- `$base` paths are resolved relative to the YAML file that contains `$base`.
- Works recursively; base files may themselves contain `$base`.
- Cycle detection for safety.
- Importable library functions plus a CLI entrypoint.

Merge rules:
- dict + dict: merged recursively
- anything else: override replaces base
- lists are replaced entirely by override lists
"""

from __future__ import annotations

import argparse
import copy
import os
import sys
from typing import Any

import yaml

YAMLValue = Any
YAMLMapping = dict[str, YAMLValue]


class BaseResolutionError(Exception):
    """Raised when $base resolution fails."""


def _read_yaml_file(
    path: str, *, loader: type = yaml.SafeLoader, stack: list[str] | None = None, relative_file: str | None = None
) -> tuple[str, YAMLValue]:
    if stack is None:
        stack = []

    resolved = path
    if relative_file:
        resolved = os.path.join(os.path.dirname(relative_file), path)

    resolved = os.path.normpath(resolved)
    resolved = os.path.abspath(resolved)
    if not os.path.exists(resolved):
        raise FileNotFoundError(f"Could not find file: {resolved} ({path}) resolved from:" + "\n".join(stack))

    try:
        with open(resolved, "r", encoding="utf-8") as f:
            return resolved, yaml.load(f, Loader=loader)
    except Exception as e:
        raise BaseResolutionError(
            f"Failed to read YAML file {resolved} ({path}): {e} resolved from " + "\n".join(stack)
        ) from e


def _deep_merge(base: YAMLValue, override: YAMLValue) -> YAMLValue:
    """
    Deep-merge override onto base.

    - If both are dicts: merge keys recursively.
    - Otherwise: override replaces base.
    """
    if isinstance(base, dict) and isinstance(override, dict):
        result: YAMLMapping = copy.deepcopy(base)
        for k, v in override.items():
            if k in result:
                result[k] = _deep_merge(result[k], v)
            else:
                result[k] = copy.deepcopy(v)
        return result
    else:
        return copy.deepcopy(override)


def _resolve_bases(
    node: YAMLValue,
    *,
    current_file: str,
    loader: type,
    stack: list[str],
    seen: set[str],
) -> YAMLValue:
    """
    Recursively resolve `$base` keys within a YAML structure.

    Args:
        node: The current YAML node.
        current_file: The YAML file path that *contains* this node.
        loader: PyYAML loader class.
        stack: File include stack for cycle detection / error messages.
        seen: Set of normalized absolute paths already in stack.

    Returns:
        A new YAML structure with bases expanded and merged.
    """
    # Mapping / dict
    if isinstance(node, dict):
        if "$base" in node:
            base_ref = node.get("$base")
            if not isinstance(base_ref, str):
                raise BaseResolutionError(
                    f"$base value must be a string path in file '{current_file}', got {type(base_ref).__name__}"
                )

            abs_path, base_data = _read_yaml_file(base_ref, loader=loader, stack=stack, relative_file=current_file)

            if abs_path in seen:
                chain = " -> ".join(stack + [abs_path])
                raise BaseResolutionError(f"Cycle detected in $base chain: {chain}")

            base_resolved = _resolve_bases(
                base_data,
                current_file=abs_path,
                loader=loader,
                stack=stack + [abs_path],
                seen=seen | {abs_path},
            )

            # Resolve override mapping (excluding $base)
            override_map = {k: v for k, v in node.items() if k != "$base"}
            override_resolved: YAMLMapping = {}
            for k, v in override_map.items():
                override_resolved[k] = _resolve_bases(
                    v,
                    current_file=current_file,
                    loader=loader,
                    stack=stack,
                    seen=seen,
                )

            # If base is not a mapping, only allow pure replacement (no extra keys)
            if not isinstance(base_resolved, dict):
                if override_resolved:
                    raise BaseResolutionError(
                        f"Cannot merge mapping overrides onto non-mapping base "
                        f"(base type {type(base_resolved).__name__}) in file '{current_file}'"
                    )
                return copy.deepcopy(base_resolved)

            merged = _deep_merge(base_resolved, override_resolved)
            return merged

        # Normal mapping: resolve children
        out: YAMLMapping = {}
        for k, v in node.items():
            out[k] = _resolve_bases(
                v,
                current_file=current_file,
                loader=loader,
                stack=stack,
                seen=seen,
            )
        return out

    # Sequence / list
    if isinstance(node, list):
        return [
            _resolve_bases(
                item,
                current_file=current_file,
                loader=loader,
                stack=stack,
                seen=seen,
            )
            for item in node
        ]

    # Scalar
    return copy.deepcopy(node)


def load(path: str, *, loader: type = yaml.SafeLoader) -> YAMLValue:
    abs_path, data = _read_yaml_file(path, loader=loader)
    return _resolve_bases(
        data,
        current_file=path,
        loader=loader,
        stack=[path],
        seen={abs_path},
    )


def main():
    parser = argparse.ArgumentParser(description="Build a YAML file with $base inheritance.")
    parser.add_argument("yaml", help="Path to YAML file to build.")
    args = parser.parse_args()

    resolved = load(args.yaml)
    yaml.safe_dump(resolved, stream=sys.stdout, allow_unicode=True)


if __name__ == "__main__":
    main()
