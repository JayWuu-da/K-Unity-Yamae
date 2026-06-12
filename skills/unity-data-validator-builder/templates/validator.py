from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

TableValue = str | int | float | None
TableRow = dict[str, TableValue]


@dataclass(frozen=True, slots=True)
class Issue:
    severity: str
    table: str
    row_id: str
    field: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Unity data tables from a profile.",
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--report-md", required=True)
    parser.add_argument("--report-json", required=True)
    return parser.parse_args()


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def rows_for(data, section: str) -> list[TableRow]:
    if section == "*":
        if isinstance(data, dict):
            rows: list[TableRow] = []
            for value in data.values():
                if isinstance(value, list):
                    rows.extend(item for item in value if isinstance(item, dict))
            return rows
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        value = data.get(section, [])
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def filtered_rows(rows: list[TableRow], rule) -> list[TableRow]:
    where_rule = rule.get("where")
    if not isinstance(where_rule, dict):
        return rows
    field = where_rule.get("field")
    expected = where_rule.get("equals")
    if not isinstance(field, str):
        return rows
    return [row for row in rows if normalize(row.get(field)) == normalize(expected)]


def normalize(value: TableValue) -> str:
    if value is None:
        return ""
    return str(value).strip()


def table_key(file_name: str, section: str) -> str:
    return f"{file_name}::{section}"


def build_index(rows: list[TableRow], field: str) -> set[str]:
    return {normalize(row.get(field)) for row in rows}


def relationship_targets(loaded: dict[str, list[TableRow]], relationship) -> set[str]:
    to_rules = relationship.get("to_any")
    if isinstance(to_rules, list):
        values: set[str] = set()
        for to_rule in to_rules:
            if isinstance(to_rule, dict):
                rows = loaded.get(table_key(to_rule["file"], to_rule["section"]), [])
                values.update(build_index(rows, to_rule["field"]))
        return values
    to_rule = relationship["to"]
    to_rows = loaded.get(table_key(to_rule["file"], to_rule["section"]), [])
    return build_index(to_rows, to_rule["field"])


def validate(project_path: Path, profile_path: Path) -> tuple[dict[str, int], list[Issue]]:
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    table_root = project_path / profile["table_root"]
    loaded: dict[str, list[TableRow]] = {}
    issues: list[Issue] = []

    for table in profile.get("tables", []):
        file_name = table["file"]
        section = table["section"]
        rows = filtered_rows(rows_for(load_json(table_root / file_name), section), table)
        loaded[table_key(file_name, section)] = rows
        id_field = table.get("id_field", "ID")
        for row in rows:
            row_id = normalize(row.get(id_field))
            for field in table.get("required_fields", []):
                if field not in row or normalize(row.get(field)) == "":
                    issues.append(
                        Issue(
                            "error",
                            table_key(file_name, section),
                            row_id,
                            field,
                            "required field is missing",
                        )
                    )

    checked_relationships = 0
    for relationship in profile.get("relationships", []):
        from_rule = relationship["from"]
        from_rows = loaded.get(table_key(from_rule["file"], from_rule["section"]), [])
        to_values = relationship_targets(loaded, relationship)
        skip_values = {normalize(value) for value in relationship.get("skip_values", [])}
        for row in from_rows:
            value = normalize(row.get(from_rule["field"]))
            if value in skip_values:
                continue
            checked_relationships += 1
            if value not in to_values:
                issues.append(
                    Issue(
                        "error",
                        table_key(from_rule["file"], from_rule["section"]),
                        normalize(row.get("ID")),
                        from_rule["field"],
                        f"{relationship['name']} {from_rule['field']} missing {value}",
                    )
                )

    return {
        "checked_tables": len(loaded),
        "checked_relationships": checked_relationships,
    }, issues


def write_reports(
    summary: dict[str, int],
    issues: list[Issue],
    report_md: Path,
    report_json: Path,
) -> None:
    status = "passed" if not issues else "failed"
    payload = {
        "status": status,
        "summary": summary,
        "issues": [asdict(issue) for issue in issues],
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# Unity Data Validator Report",
        "",
        f"- Status: {status}",
        f"- Checked tables: {summary['checked_tables']}",
        f"- Checked relationships: {summary['checked_relationships']}",
        "",
    ]
    if issues:
        lines.append("## Issues")
        for issue in issues:
            lines.append(
                f"- {issue.severity}: {issue.table} row={issue.row_id} "
                f"field={issue.field} - {issue.message}"
            )
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    summary, issues = validate(Path(args.project), Path(args.profile))
    write_reports(summary, issues, Path(args.report_md), Path(args.report_json))
    state = "passed" if not issues else "failed"
    print(
        f"{state}: {summary['checked_tables']} tables, "
        f"{summary['checked_relationships']} relationships"
    )
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
