# context-guard

Claude Code plugin that stops sessions from silently growing too large.

## topic-guard
Blocks a prompt once the session's context reaches `TOPIC_GUARD_BLOCK_CTX` tokens (default 200000).
The user then types `/clear` (old session stays in `/resume`) or resends the prompt starting with `+`.
After a `+` it stays quiet in that session until it grows another `TOPIC_GUARD_STEP_CTX` (default 100000).
Slash commands always pass. Needs `python3` (macOS/Linux). Fails open on any error.

## Install (manual, one user)
    /plugin install topic-guard --marketplace Atrinum-Group-AG/context-guard

## Roll out to the whole org
claude.ai → Organization settings → Claude Code → Managed settings: see `managed-settings.example.json`.
