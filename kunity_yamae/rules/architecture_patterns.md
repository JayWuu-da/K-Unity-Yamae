# Unity Architecture Patterns Rule Card

- Identify existing UI and gameplay ownership before adding abstractions.
- Prefer the project's existing MVP, MVC, MVVM, Controller, Manager, Service, EventBus, or ScriptableObject data pattern.
- Keep gameplay/domain state separate from UI view code when the touched domain already follows that pattern.
- Add a new abstraction only when it removes repeated complexity or matches an established local convention.
