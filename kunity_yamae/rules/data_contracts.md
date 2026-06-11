# Unity Data Contracts Rule Card

**Trigger:**
- Table, localization, reward, packet, DTO, payload, backend route, or response-apply work.

**Required:**
- Verify source table rows, localization keys, displayed text, request/response DTOs, final payload shape, merge rules, and response apply path.
- State whether each changed field is a delta carrier, a final snapshot, or display-only data.
- Treat array payloads as shaped contracts: record length, index meaning, and merge behavior.
- Keep server-authoritative data visible. Expose contract mismatches instead of hiding them with local fallback behavior.

**Forbidden:**
- Do not stop at a single-item builder when a final aggregator or send site changes the payload.
- Do not assume the backend recalculates values unless the actual route or service proves it.
- Do not use localization fallback text as proof that the source table is valid.

**Required evidence:**
- A contract summary naming the source row or DTO, final transmitted shape, and response apply owner.
