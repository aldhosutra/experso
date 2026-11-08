# Troubleshooting

## A step stopped on a usage or rate limit

The script prints `rate/usage limit hit`. Finished work is saved. Tell the user, and re-run the **same command** after the limit resets. Never delete state to retry.

## A step outlives the shell tool's time limit

Start it detached and check its log:

```bash
nohup python3 <X>/digest.py <handle> --workers 2 > /tmp/experso-digest.log 2>&1 &
tail -5 /tmp/experso-digest.log
```

The script's last line starts with `DONE` or `[digest] finished`. Every step resumes, so a killed run loses only the items in flight.

## The harness hangs or times out with no output

OpenCode retries provider errors silently. Check the model works: `opencode run -m <provider/model> "Reply OK"`, and pick another with `--model`. Lower the per-call limit with `--timeout <seconds>`.

## Network or permission errors inside a sandbox

`ingest.py` needs network access, and the LLM steps start another agent process that needs network access and its login. A sandboxed agent (for example Codex in its default modes) blocks these: allow network access for the session, or run the command in a normal terminal, then continue.

## Instagram refuses or throttles the download (401, 403, 429)

Wait and re-run: finished posts are skipped. If it persists, log in once with a spare account, `instaloader --login <user>`, then pass `--login <user>` to `ingest.py`.

## "No module named ..." or "can't run here"

Run the experso-setup skill.

## `.agents/skills/<name> already exists and is not @<handle>'s generated skill`

A name collision. Use the experso-merge skill, which merges by default.

## A clip's transcript says only "Thank you."

A speech-recognition artifact on music-only clips. Leave it.
