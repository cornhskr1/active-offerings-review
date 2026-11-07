# Active Offerings releases

When changing executable files in this repository, coordinate the release with
the private [collector repository](https://github.com/cornhskr1/active-offerings-data).
Its scheduled jobs compare the executable files on app main to
`contracts/trusted-app-code.json` before collection. This includes tests,
workflows, frontend assets and migration files. The authoritative path rule is
`source_path` in the data repository's `scripts/select_app_revision.py`.

For an authorized merge touching those paths, review the code diff and run
the application regression tests. Prepare the companion manifest change from
the tested tree. Verify the actual merged app commit and its complete executable
tree, then finalize the manifest's commit, paths, modes and blob hashes. Merge
the tested companion PR as part of the same authorized release. A data-only or
Markdown-only change with no executable differences does not require a repin.

Verify the data repository's revision selector accepts current app main and
report the status of a subsequent scheduled collector. If companion-repository
access or merge authority is missing, flag that dependency while the app PR
is still open so the release can be coordinated.
