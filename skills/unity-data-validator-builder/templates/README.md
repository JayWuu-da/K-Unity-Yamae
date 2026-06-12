# Unity Data Validator

Domain: `{{DOMAIN}}`

This validator reads Unity table data from the project path recorded during scaffold:

```text
{{PROJECT_PATH}}
```

Project-specific rules live in `profiles/{{DOMAIN}}.yaml`.
Reports are emitted as Markdown and JSON under `reports/`.

Run:

```bash
python src/validator.py \
  --project <unity-project-root> \
  --profile profiles/{{DOMAIN}}.yaml \
  --report-md reports/{{DOMAIN}}.md \
  --report-json reports/{{DOMAIN}}.json
```
