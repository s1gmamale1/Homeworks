# Content JSON Migrations

`scripts/migrate_content_json.py` is the reusable scaffold for making stored
`content_json` shape changes retroactive. Backend code changes take effect on
every request, but data inside each homework row is a frozen snapshot until it
is re-saved or migrated.

## Registering a Transform

Add a pure transform to the registry:

```python
@register_transform("backfill_example")
def backfill_example(content_json: dict, row: dict) -> dict | None:
    new_content = copy.deepcopy(content_json)
    # mutate new_content
    return new_content if changed else None
```

Return `None` when the row is already clean. Raise only for real migration
errors; the harness records the row and continues.

## Dry Run vs Apply

Dry-run is the default and never writes:

```bash
python scripts/migrate_content_json.py --transform add_default_dmg_to_boss --limit 10 --verbose
```

Apply mode validates each transformed blob with
`ContentJSON.model_validate(new_content_json)` before writing through the
existing `update_homework` repo function:

```bash
python scripts/migrate_content_json.py --transform add_default_dmg_to_boss --apply
```

Use `--ids HW-1,HW-2` to scope rows and `--report path.json` to choose the JSON
audit report location.

## Skip-and-Flag Invariant

Every row is handled independently. Transform exceptions, schema validation
failures, `None` returns, and unchanged output are all written to the structured
report. A row that fails validation is never written.

## Worked Example: `option_index`

To backfill missing `option_index` values for old `gb_adaptive_quiz` items:

```python
@register_transform("backfill_gb_adaptive_quiz_option_index")
def backfill_gb_adaptive_quiz_option_index(content_json: dict, row: dict) -> dict | None:
    changed = False
    new_content = copy.deepcopy(content_json)
    for item in new_content.get("gb_adaptive_quiz", []):
        if not isinstance(item, dict):
            continue
        spec = item.get("answer_spec")
        correct = item.get("correct")
        if isinstance(spec, dict) and "option_index" not in spec and isinstance(correct, int):
            spec["option_index"] = correct
            changed = True
    return new_content if changed else None
```

First run it without `--apply`, inspect the first diffs and JSON report, then
rerun with `--apply` once the output is correct.
