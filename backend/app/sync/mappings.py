"""Build CLI line ↔ YAML line mappings."""

from __future__ import annotations

from app.field_keys import mapping_specificity
from app.models import LineMapping, NacYamlResult, ParseResult


def build_line_mappings(parse_result: ParseResult, yaml_result: NacYamlResult) -> list[LineMapping]:
    """Join parser CLI refs with YAML line ranges."""
    mappings: list[LineMapping] = []
    for ref in parse_result.cli_refs:
        span = yaml_result.ranges.get(ref.field_key)
        if not span:
            continue
        start, end = span
        mappings.append(
            LineMapping(
                cli_line=ref.cli_line,
                yaml_start_line=start,
                yaml_end_line=end,
                label=ref.label,
                field_key=ref.field_key,
            )
        )
    return mappings


def mapping_for_cli_line(mappings: list[LineMapping], cli_line: int) -> LineMapping | None:
    matches = [m for m in mappings if m.cli_line == cli_line]
    if not matches:
        return None
    return max(matches, key=lambda m: mapping_specificity(m.field_key))


def mapping_for_yaml_line(mappings: list[LineMapping], yaml_line: int) -> LineMapping | None:
    matches = [m for m in mappings if m.yaml_start_line <= yaml_line <= m.yaml_end_line]
    if not matches:
        return None
    return min(matches, key=lambda m: m.yaml_end_line - m.yaml_start_line)
