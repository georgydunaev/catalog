# Ticket 7446 — Catalog: Add JSON schema definition for model dispatch profiles in catalog/schemas/
**Importance:** 4/10
**State:** closed
**Labels:** catalog, automated, fleet-ticket
**Assigned:** openrouter/nvidia/nemotron-3.5-lightning:free

## Description
Author catalog/schemas/model_profile.schema.json documenting expected fields (id, name, aliases, tier, context_window, max_read_lines, tramline).

## Acceptance Criteria
1. Changes are tested and verified without introducing regressions.
2. Code follows repository invariants (Rule 5 zero committed secrets, Rule 6 atomic changes).
3. Ground-truth test commands pass.


## Resolution
- **Status:** COMPLETED & VERIFIED
- **Details:** Authored catalog/schemas/model_profile.schema.json validating model profile schemas.
