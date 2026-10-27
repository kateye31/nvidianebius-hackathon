# CLAUDE.md

All project rules live in AGENTS.md so every AI tool follows the same ones.

@AGENTS.md

## Claude-specific

- Plan in a few lines before multi-file edits; keep diffs small.
- Run `pytest -q` from `cloud/` after Python changes.
- If a change touches the packet, update all three places listed in AGENTS.md rule 2.
