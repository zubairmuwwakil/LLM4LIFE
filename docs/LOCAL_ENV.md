# LLM4LIFE local environment

Repo-root `.env` is the durable local configuration file for development/runtime values that should not be committed. It is already ignored by Git.

## Automatic loading

Supported local People/Obsidian commands read `.env` automatically. You do not need to run `source .env` first.

The loader parses `KEY=VALUE` data without executing the file as shell code. Existing exported environment variables win over `.env`, so temporary shell overrides still work.

## Initialize and persist current values

If useful values are still exported in the current shell, capture known LLM4LIFE variables and generate a missing Obsidian bridge token:

```bash
python3 scripts/init_local_env.py --capture-current
```

The command:

- creates/updates `.env`;
- preserves existing saved values;
- captures known currently-exported values only when the saved value is missing;
- generates a 64-hex-character Obsidian bridge token if none is saved;
- never prints secret values;
- sets `.env` permissions to `0600`.

## Lost bridge token

A token that existed only in an old shell process and was never persisted cannot be reconstructed. Rotate it instead:

```bash
python3 scripts/init_local_env.py --rotate-bridge-token
```

If an old Obsidian bridge is still running, it continues using the old in-memory token until that process exits. Find the listener:

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
```

Confirm the PID belongs to the LLM4LIFE Python bridge before stopping it:

```bash
ps -p <PID> -o pid=,command=
kill <PID>
```

Then start the bridge again:

```bash
bash scripts/run_obsidian_bridge.sh
```

The restarted process reads the persisted token from `.env`.

## Other credentials

`init_local_env.py` does not fabricate replacements for database, Google OAuth, Cloudflare, or other provider credentials. With `--capture-current`, it can persist a known value that is still exported. If such a credential is genuinely lost, recover or rotate it at its real authority/provider rather than generating a random local replacement.

## Security

- Never commit `.env`.
- Keep it mode `0600`.
- Do not paste secret values into issue/PR bodies or public logs.
- Provider/production secret stores remain authoritative where applicable; `.env` is for local runtime access.
