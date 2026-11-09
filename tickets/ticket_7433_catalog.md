# Ticket 7433 — Catalog: Add validation for orphaned markdown links in catalog/index.html
**Importance:** 4/10
**State:** opened
**Labels:** catalog, automated, fleet-ticket
**Assigned:** opencode/glm-5.3-flash-free

## Description
Add an automated validation routine that checks relative href and markdown links in catalog/index.html to ensure 0 broken links.

## Acceptance Criteria
1. Changes are tested and verified without introducing regressions.
2. Code follows repository invariants (Rule 5 zero committed secrets, Rule 6 atomic changes).
3. Ground-truth test commands pass.
