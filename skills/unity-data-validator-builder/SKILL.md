---
name: unity-data-validator-builder
description: Build or refresh project-local Unity data validator skeletons for table, reward, shop, pass, package, localization, payload-shape, and read-only server-contract checks without storing project-specific examples in K-Unity-Yamae.
---

# Unity Data Validator Builder

## Purpose
Use this skill to create or update a project-local validator that checks Unity data contracts. The skill owns the scaffold and workflow; the generated validator owns project-specific profiles, table paths, and reports.

## When To Use
- A Unity data domain needs repeatable validation before code or content changes.
- Tables must be checked across source rows, lookup tables, reward rows, localization keys, package/shop links, or payload-shape assumptions.
- Server or backend contracts must be compared as read-only reference material.

## Workflow
1. Read the target project's `Agent.md` or `AGENTS.md` first.
2. Run `kunity-yamae context --pretty "<task>"` when Unity risk context is useful.
3. Scaffold or refresh an external validator folder:

   ```bash
   python skills/unity-data-validator-builder/scripts/scaffold_validator.py \
     --project <unity-project-root> \
     --domain <safe-domain-name> \
     --output <validator-output-folder>
   ```

4. Put project-specific table paths, field names, profile rules, and report expectations in the generated validator output, not in K-Unity-Yamae.
5. Run the generated validator through its CLI and keep Markdown/JSON reports as evidence.

## Guardrails
- Do not add project-specific examples, real local paths, product names, packet names, or table row IDs to this skill.
- Do not edit Unity project files while scaffolding. The generated validator reads the project path only.
- Treat external server code and server routes as read-only comparison inputs.
- Do not add a core `kunity-yamae` command until the same generated-validator pattern has been proven across multiple domains.
- Do not mask contract failures with fallback values; report the mismatch.

## Outputs
- `profiles/<domain>.yaml`: project-local validation profile.
- `src/validator.py`: generated CLI validator.
- `reports/*.md` and `reports/*.json`: operator-facing evidence.
- `tests/test_validator_contract.py`: generated validator smoke tests.

## References
- Read `references/validator_contract.md` before defining profile rules.
- Read `references/unity_data_validator_patterns.md` before changing scaffold behavior.
