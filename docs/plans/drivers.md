# Plan: driving lochara from a chat (Claude or Waymond)

You make a character by talking, from Discord, through [Choomfie](https://github.com/ANonABento/choomfie). Two brains
can drive it, and you can switch between them mid-character:

- **Claude** (a Choomfie chat started in the lochara folder): runs lochara directly on the Mac, reads `AGENTS.md`
  and the skills, and asks Waymond for pictures when a hosted model is better.
- **Waymond** (a `/brain waymond` thread): draws the design and views itself, in the same conversation where you
  approved them, and runs lochara on the Mac through Choomfie's remote MCP endpoint.

Both use the same character folder, so the state lives in lochara, not in either chat. Claude stays the brain for
fixing and extending lochara itself.

```
                   you (Discord thread)
                   ▲ pictures, sheets, renders   │ picks, notes
     ┌─────────────┴───────────────┐   ┌─────────┴───────────────────┐
     │ Claude path                 │   │ Waymond path                │
     │ chat started in ~/lochara   │   │ /brain waymond, mode "char" │
     │ Bash → lochara              │   │ draws design + views itself │
     │ ask_brain → Waymond images  │   │ pipeline tools over remote  │
     └─────────────┬───────────────┘   │ MCP (tunnel, token)         │
                   │                   └─────────┬───────────────────┘
                   ▼                             ▼
            Choomfie on the Mac: pipeline runner (jobs, files, posting)
                                 │
                                 ▼
              lochara (character folder: recipe, requests, renders)
```

## What already works
- lochara: commands write into the character folder and stop at checkpoints; `--via handoff` + `lochara deliver`
  take pictures made anywhere.
- Choomfie: `/brain waymond` threads; Waymond's reply files arrive on the Mac (`BrainReply.files`) and are posted as
  attachments; images you post go to Waymond; Waymond modes (frames sent with every message, "files" modes that land
  files in a folder); the remote MCP endpoint (loopback, bearer token, allowlist, reached through a tunnel); plan
  status notes appended to Waymond's next message.
- Draft PR #101: `ask_brain`, Claude → Waymond with files back on disk.

## Layers

### L1 lochara: a state any driver can read
Waymond doesn't load `AGENTS.md`, and a runner can't parse prose. So lochara says what's next, in JSON.

- **`lochara next <char> [--json]`** (done, `src/lochara/state.py`): where the character is and what happens next:
  ```json
  {"character": "aiko", "stage": "parts", "waiting": "pick",
   "say": "Pick a picture for visor: h1, h2, s12.",
   "show": ["/…/aiko/parts/visor/candidates/sheet.png"],
   "options": ["h1", "h2", "s12"],
   "run": {"pick": ["part", "pick", "aiko", "visor", "<option>"], "redraw": ["part", "draw", "aiko", "visor"]}}
  ```
  `waiting` is one of `pick`, `approve`, `pictures` (a handoff request is open; the step carries `request`), `run`
  (nothing to decide: run `run.next`, maybe for minutes), `input` (only a person can do it), `done`. `show` is what
  to post. Commands are argument lists, never shell strings. Read from the folder every time, never stored. Each
  stage adds its rule as it's built (views next).
- **`--json` on every command** (done): `{ok, command, show?, wrote?, …, next}` on stdout, progress on stderr (the
  file descriptor, so Blender and mflux can't write into it), errors as `{ok: false, problem}` with exit 1.
- **`lochara deliver --from <folder>`** (done): deliver every picture in a folder (what a chat hands over).
- Long steps (3D, paint, bake) stay plain commands; the runner (L3) makes them jobs. lochara holds no keys and never
  names a chat app.

### L2 Choomfie: brains and files (fixes PR #101)
- **`askBrain()` shared function** behind the `ask_brain` tool, used by the tool and the runner.
- **Owner check in code**, not only the role allowlist.
- **Wait for background jobs:** when Waymond moves a turn to the background, `ask_brain` waits for the late result
  (with the tool's timeout) instead of letting the files go only to the chat.
- **Which conversation:** `ask_brain` takes `conversation` (a thread id), so Claude can ask *the thread where you
  designed the character*, not a new one. That's what keeps views consistent with the design.
- **Thread file store:** every image in a thread (yours and the brain's) is kept on disk for a while under
  `<data>/thread-files/<thread>/<message>/`, so a tool can say "the pictures in my last reply" or "message X"
  instead of a path. Pruned by age.

### L3 Choomfie: the pipeline runner (generic, no lochara in code)
Config, hand-edited like `chatRoots`:
```json
"pipelines": {
  "lochara": {"dir": "/Users/bentomac/lochara", "command": ["./lochara"],
              "allow": ["next", "concept", "views", "part", "model", "deliver", "render", "export", "requests"]}
}
```
- **Tools** `pipeline_run(pipeline, args[], chat_id, files?)` and `pipeline_status(job?)`.
  - `args[0]` must be on `allow`; arguments are passed as an array, never a shell string; `--json` is added.
  - `files`: `last_reply`, `last_mine`, or message ids, resolved from the thread file store into a temp folder whose
    path replaces `{files}` in `args`.
  - Quick commands answer inline. Anything over ~20 s becomes a **job**: the tool returns its id at once.
- **Jobs:** one at a time per pipeline (the GPU), queued otherwise; log kept; cancellable (`/pipeline stop`).
- **Posting:** when a command or job ends, the runner posts its `show` files and `say` to the thread itself, so you
  see every checkpoint no matter which brain asked.
- **Waking the brain:** the result is also queued as a note on the brain's next message (like the plan status
  note), so when you answer "h2", Waymond already knows the job finished and what it showed. Optional per thread:
  auto-continue (Choomfie sends the note to the brain right away, so it can carry on without you saying anything).
- **Shortcut:** a "Use as design → <pipeline>" button on brain replies with images, which runs the pipeline's
  intake (`lochara new <char> --design {files}`), for when you designed in a plain Waymond chat.

### L4 Claude path
- Choomfie config: `chatRoots: ["/Users/bentomac/lochara"]`; `/clear cwd:` starts the chat there.
- Claude runs lochara through `pipeline_run`, the same as Waymond: one path, so jobs, the GPU queue, posting and the
  notes behave the same whichever brain drives. (Bash stays for fixing lochara itself, not for making characters.)
- Pictures from Waymond: `ask_brain(conversation=<the design thread>)` → `pipeline_run lochara deliver … {files}`.

### askBrain, any brain to any brain
`askBrain(from, to, …)` is one function, written for any sender and any target. Today: Claude → any loaded non-Claude
brain (Waymond, future plugins with no change). Claude as a target (Waymond → Claude over the remote endpoint) stays
off until there's a real use, because it would let a remote caller start a session that runs commands; turning it on
needs read-only or fixed-folder limits and the owner's approval in Discord.

### L5 Waymond path
- **Remote MCP:** add `pipeline_run`, `pipeline_status` to `remoteMcp.tools`; the tunnel up; Choomfie's endpoint
  added in Waymond's Integrations with the token. Remote calls have owner authority, so the runner's `allow` list
  and argument rules are the boundary.
- **Mode `character`** (a Waymond mode, files mode `characters/`). Its frame, sent with every message, says:
  - Always start with `pipeline_run lochara next <char>` and do what it says; never guess the stage.
  - Draw pictures yourself when `waiting` is `pictures`: follow the request's prompt and the picture rules (one
    character per image, flat cel colour, no lighting, T-pose, the character's own left and right, plain
    background), reply with them, then `pipeline_run lochara deliver <char> <request> {files}` with `files:
    last_reply`.
  - At `pick`/`approve`: the runner has posted the sheet; ask the user, then run what `run` says with their answer.
  - At `run`: run `run.next`; for a long one say what's running and stop; the result arrives as a note.
  - At `input`: tell the user what `say` says.
  - Don't run anything not in `next`'s output; report problems as they are.
- Waymond's limits: a turn stops after several tool calls; no polling loops (notes instead); its sandbox isn't used
  for lochara at all.

### L6 Docs and checks
- lochara `docs/agents.md`: both paths, `next --json`, pictures rules for a remote drawer.
- Choomfie `docs/`: pipelines, the thread file store, `ask_brain(conversation)`, the remote allowlist warning.
- Tests: lochara `next` per stage; Choomfie runner (allow list, array args, files resolution, job queue, posting,
  note), `askBrain` owner refusal and background wait.

## Switching brains mid-character
State is in the character folder, and `next` reads it, so either brain picks up where the other stopped. Pictures
stay consistent if the drawing always happens in the design thread's Waymond conversation: on the Waymond path that's
automatic; on the Claude path it's `ask_brain(conversation=…)`.

## Order of work
| Step | What | Needs |
|---|---|---|
| 1 | ✅ L2: `askBrain()`, owner check, background wait, `conversation` (choomfie #101, merged) | nothing |
| 2 | ✅ L1: `next --json` for what exists today (base, handoff, part draw/pick/model/place, build, render, export) + `--json` | nothing |
| 3 | L3: runner, jobs, posting, notes, thread file store (new Choomfie PR, stacked on #101) | step 1 |
| 4 | L4: `chatRoots`, Claude path end to end on a concept + part | steps 2–3 |
| 5 | L5: tunnel check, remote allowlist, `character` mode; Waymond path end to end on the same | step 4 |
| 6 | Each new stage (views S1, 3D S2, …) adds its `next` entry; both paths get it with no Choomfie change | spikes |

Steps 1–5 don't need the model downloads, so they can run while those finish.

## Risks
- **Remote authority:** anything on `allow` can be run by whoever holds the token. Keep `allow` to lochara
  subcommands, arguments as arrays, paths resolved under the pipeline dir or the thread file store.
- **Waymond drift:** it may skip `next` or invent steps. The frame says to always start from `next`, and the runner
  refuses commands `next` didn't offer for a character waiting on a pick (optional strict mode).
- **Hosted pictures:** the design goes to Waymond's service; the recipe records `via` for each picture.
- **Discord limits:** 10 attachments and 25 MB per message (the runner posts sheets, not every candidate).
