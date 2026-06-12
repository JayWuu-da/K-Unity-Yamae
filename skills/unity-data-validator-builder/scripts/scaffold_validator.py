from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from textwrap import dedent

SAFE_DOMAIN = re.compile(r"^[a-z][a-z0-9_-]*$")


class ScaffoldError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a project-local Unity data validator skeleton.",
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Unity project root to read at validation time.",
    )
    parser.add_argument("--domain", required=True, help="Safe validation domain name.")
    parser.add_argument("--output", required=True, help="Validator output folder to create.")
    parser.add_argument("--force", action="store_true", help="Replace an existing output folder.")
    return parser.parse_args()


def ensure_safe_domain(domain: str) -> None:
    if not SAFE_DOMAIN.fullmatch(domain):
        raise ScaffoldError("domain must be a safe name matching ^[a-z][a-z0-9_-]*$")


def ensure_safe_output(project_path: Path, output_path: Path) -> None:
    if output_path == project_path:
        raise ScaffoldError("output must not be the Unity project root")
    if project_path in output_path.parents:
        raise ScaffoldError("output must not be inside the Unity project root")
    if output_path.parent == output_path:
        raise ScaffoldError("output must not be a filesystem root")


def prepare_output(project_path: Path, output_path: Path, force: bool) -> None:
    ensure_safe_output(project_path, output_path)
    if output_path.exists() and not force:
        raise ScaffoldError(f"output already exists; pass --force to replace: {output_path}")
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True)


def default_profile(domain: str) -> str:
    return dedent(
        f"""\
        domain: {domain}
        table_root: Assets/Resources/TableDatas
        tables:
          - file: Shop.json
            section: Pass
            id_field: ID
            required_fields: [ID, PRODUCT_ID, PRODUCT_GROUP_ID, LEVEL_COUNT, NAME_KEY]
          - file: Shop.json
            section: Product
            id_field: ID
            required_fields: [ID, TYPE, PURCHASE_ID]
          - file: Shop.json
            section: PassProduct
            id_field: ID
            required_fields: [ID, GROUP_ID, LEVEL, TYPE, REWARD_ID]
          - file: Package.json
            section: Package
            id_field: ID
            where: {{field: PurchaseType, equals: Pass}}
            required_fields: [ID, product_id, PurchaseType]
          - file: Reward.json
            section: Reward
            id_field: ID
            required_fields: [ID, REWARD_ID, TYPE, VALUE, COUNT]
          - file: LocalizeText.json
            section: "*"
            id_field: ID
            required_fields: [TEXT]
        relationships:
          - name: pass-product-package
            from: {{file: Shop.json, section: Pass, field: PRODUCT_ID}}
            to_any:
              - {{file: Shop.json, section: Product, field: ID}}
              - {{file: Package.json, section: Package, field: ID}}
            skip_values: ["", "0", "none", "-1"]
          - name: pass-product-group
            from: {{file: Shop.json, section: Pass, field: PRODUCT_GROUP_ID}}
            to: {{file: Shop.json, section: PassProduct, field: GROUP_ID}}
            skip_values: ["", "0", "none", "-1"]
          - name: pass-name-localization
            from: {{file: Shop.json, section: Pass, field: NAME_KEY}}
            to: {{file: LocalizeText.json, section: "*", field: TEXT}}
            skip_values: ["", "0", "none", "-1"]
          - name: pass-product-reward
            from: {{file: Shop.json, section: PassProduct, field: REWARD_ID}}
            to: {{file: Reward.json, section: Reward, field: REWARD_ID}}
            skip_values: ["", "0", "none", "-1"]
        payload_shape_notes:
          - Record the final Type, Index, Value, and Count shape in project-local reports.
          - Treat server contracts as read-only comparison inputs.
        """
    )


def read_template(name: str) -> str:
    template_path = Path(__file__).resolve().parents[1] / "templates" / name
    return template_path.read_text(encoding="utf-8")


def render_readme(project_path: Path, domain: str) -> str:
    return read_template("README.md").replace("{{PROJECT_PATH}}", str(project_path)).replace(
        "{{DOMAIN}}",
        domain,
    )


def write_files(project_path: Path, output_path: Path, domain: str) -> None:
    (output_path / "profiles").mkdir()
    (output_path / "src").mkdir()
    (output_path / "tests").mkdir()
    (output_path / "reports").mkdir()
    (output_path / "profiles" / f"{domain}.yaml").write_text(
        default_profile(domain),
        encoding="utf-8",
    )
    (output_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (output_path / "src" / "validator.py").write_text(
        read_template("validator.py"),
        encoding="utf-8",
    )
    (output_path / "reports" / ".gitkeep").write_text("", encoding="utf-8")
    (output_path / "tests" / "test_validator_contract.py").write_text(
        read_template("test_validator_contract.py"),
        encoding="utf-8",
    )
    (output_path / "README.md").write_text(render_readme(project_path, domain), encoding="utf-8")


def main() -> int:
    args = parse_args()
    try:
        ensure_safe_domain(args.domain)
        project_path = Path(args.project).resolve()
        output_path = Path(args.output).resolve()
        prepare_output(project_path, output_path, args.force)
        write_files(project_path, output_path, args.domain)
    except ScaffoldError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"created validator: {Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
