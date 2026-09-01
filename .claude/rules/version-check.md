---
paths:
  - "vyuct/__init__.py"
  - ".github/workflows/ci.yml"
---

# CI `version-check` job — every dev push needs a strictly-higher version

The `version-check` job compares `vyuct/__init__.py`'s `__version__` on `dev`
against the SAME file on `origin/master` (`git show origin/master:...`) and
FAILS unless dev's version is strictly greater — with **no exception for a
docs-only or trivial commit**.

Gotcha (hit live, #19 follow-up, PR #21): after a PR merges `dev`→`master`,
the two branches' versions match. ANY next commit pushed to `dev` — even one
that touches only `docs/autopilot-log.md` — fails `version-check` unless it
ALSO bumps the version first. This applies even to a same-day follow-up
commit landed right after the ticket's own PR merged. Bump `__version__`
(PATCH is fine) as part of that commit, not as an afterthought once CI
already failed once.

See the global `version-bumping.md` rule for the general "bump immediately
after every merge" discipline — this note is the project-specific, CI-job-
level gotcha that makes skipping it fail LOUDLY and immediately.
