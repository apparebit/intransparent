from collections.abc import Iterator
import json
from typing import cast

from .type import (
    CellType,
    MetadataType,
    DisclosureCollectionType,
    DisclosureType,
    RowType,
    SchemaEntryType,
)


def _format_row_json(row: RowType) -> str:
    for header, cell_values in row.items():
        if header != "redundant":
            break

    cells = []
    for cell in cast(list[CellType], cell_values):
        if cell is None:
            cells.append("null")
        elif isinstance(cell, int):
            cells.append(f"{cell}")
        elif isinstance(cell, float):
            cells.append(f"{cell:f}")
        elif isinstance(cell, str):
            cells.append(f'"{cell}"')
        else:
            raise ValueError(f'Invalid cell "{cell}"')

    line = ", ".join(cells)
    line = f"      {{{json.dumps(header)}: [{line}]"
    if row.get("redundant"):
        line = f'{line}, "redundant": true'
    line = f"{line}}}"
    return line


def _format_citation(metadata: MetadataType) -> Iterator[str]:
    keys, values = zip(*metadata.items())
    key_width = max(len(key) for key in keys)
    rule_width = key_width + max(len(value) for value in values) + 10
    rule = "━" * rule_width

    # In ASCII and UTF-8: '!' < [A-Za-z] < '|'
    yield f'    "!": "{rule}",'
    for key, value in zip(keys, values):
        key = json.dumps(key).rjust(key_width + 2 + 4)
        yield f"       {key}: {json.dumps(value)},"
    yield f'    "|": "{rule}"'
    yield "  }"


def encode_reports_per_platform(
    platform_disclosures: DisclosureCollectionType,
) -> Iterator[str]:
    previous_line: None | str = None

    def emit_line(line: str) -> Iterator[str]:
        nonlocal previous_line

        if previous_line is not None:
            yield previous_line
        previous_line = line

    def append_comma_to_line_if_not(flag: bool) -> bool:
        nonlocal previous_line

        if not flag:
            assert previous_line is not None
            previous_line += ","
        return False

    yield from emit_line("{")

    first_platform = True
    for platform, platform_object in platform_disclosures.items():
        first_platform = append_comma_to_line_if_not(first_platform)

        if platform_object is None:
            yield from emit_line(f"  {json.dumps(platform)}: null")
            continue

        yield from emit_line(f"  {json.dumps(platform)}: {{")
        if platform == "@":
            for line in _format_citation(cast(MetadataType, platform_object)):
                yield from emit_line(line)
            continue

        first_property = True
        for key, value in cast(DisclosureType, platform_object).items():
            first_property = append_comma_to_line_if_not(first_property)

            if key == "brands":
                s = ", ".join([json.dumps(item) for item in cast(list[str], value)])
                yield from emit_line(f'    "brands": [{s}]')
            elif key in ("features", "schema"):
                yield from emit_line(f'    "{key}": {{')
                first_item = True
                for k, v in cast(dict, value).items():
                    first_item = append_comma_to_line_if_not(first_item)
                    if v is None:
                        s = "null"
                    elif isinstance(v, str):
                        s = f'"{v}"'
                    else:
                        s = ", ".join(f'"{el}"' for el in v)
                        s = f'[{s}]'
                    yield from emit_line(f'        "{k}": {s}')
                yield from emit_line('    }')
            elif key in ("columns", "comments", "rows", "sources"):
                yield from emit_line(f'    "{key}": [')
                first_item = True
                for item in cast(list, value):
                    first_item = append_comma_to_line_if_not(first_item)
                    if key == "rows":
                        yield from emit_line(_format_row_json(item))
                    else:
                        yield from emit_line(f"      {json.dumps(item)}")
                yield from emit_line(f"    ]")
            else:
                raise ValueError(f'Unknown platform object property "{key}"')

        yield from emit_line("  }")

    yield from emit_line("}")
    assert previous_line is not None
    yield previous_line
