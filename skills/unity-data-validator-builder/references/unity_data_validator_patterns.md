# Unity Data Validator Patterns

## Scaffold Boundary
The scaffold creates a validator folder outside K-Unity-Yamae. The generated folder owns profiles, reports, and project-specific rules.

## Profile Pattern
Use one profile per validation domain. A profile should describe:
- table root relative to the Unity project,
- table files and sections,
- required fields,
- relationship checks,
- sentinel values to skip,
- optional payload-shape notes.

## Filesystem Pattern
- Read the Unity project path.
- Write only to the requested validator output path.
- Refuse existing output unless the caller passes an explicit overwrite flag.
- Never create Unity `.meta` files manually.

## Evidence Pattern
Run generated validators from the command line. Store both Markdown and JSON reports so an operator can inspect failures while automation can parse status.
