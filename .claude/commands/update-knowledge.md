# Update Knowledge Files

Regenerate `.claude/knowledge/` files to match the current source code.

## Argument
`$ARGUMENTS` — a module name (`config`, `server-api`, `server-ui`) or `all`.

## Module Mapping

| Module | Source file | Knowledge file |
|---|---|---|
| `config` | `jam/config.py` | `.claude/knowledge/config.md` |
| `server-api` | `jam/server.py` | `.claude/knowledge/server-api.md` |
| `server-ui` | `jam/html_page.py` | `.claude/knowledge/server-ui.md` |

## Steps

### 1. Determine which modules to update
- If argument is `all`: process every module in the table above.
- If argument is a specific module name: process only that module.
- If argument is empty or invalid: list available module names and stop.

### 2. For each module, check staleness
Run: `sha256sum <source_file> | cut -c1-12`

Compare against the `<!-- hash: ... -->` comment in the knowledge file.
- If hashes match: report `<module>: up to date` and skip.
- If hashes differ or knowledge file is missing: proceed to step 3.

### 3. Regenerate the knowledge file
1. Read the source file.
2. Read the existing knowledge file (if any) to preserve its structure.
3. Rewrite the knowledge file following this format:

```markdown
# <module> Knowledge
<!-- source: <source_file_path> -->
<!-- hash: <new_hash_12_chars> -->
<!-- updated: YYYY-MM-DD -->

## Public API
| Function | Signature | Purpose |

## Key Constants / Schema
...

## Dependencies
- Imports from: ...
- Imported by: ...

## Testing
- File: ...
- Mock targets: ...

## Known Limitations
- ...
```

For `server-api`: focus on endpoints, Pydantic models, and API patterns.
For `server-ui`: focus on HTML_PAGE components, design tokens, and JS helpers.

### 3b. Check downstream impact (after regeneration)

If the regenerated knowledge file shows public API changes (added/removed/renamed
functions or changed signatures), identify downstream modules using this table:

| Module changed | Check downstream modules |
|---|---|
| config | server |
| server-api | (none — leaf) |
| server-ui | (none — leaf) |

For each downstream module, grep for usage of the changed symbols:
```bash
grep -n "changed_function_name" jam/<downstream>.py
```

If usages found, print a warning:
```
WARNING: <module>.<function> changed — used in jam/<downstream>.py line N
```

### 4. Report summary
Print a table:
```
MODULE          STATUS
config          up to date
server-api      UPDATED (hash: abc123def456)
server-ui       up to date
```
