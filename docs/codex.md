# Running in Codex

For whoever changes the system. The Codex part is one skill, `.agents/skills/paper-chain/SKILL.md`, where Codex looks for a repository's skills, and `.codex-plugin/plugin.json`, which names that folder as the plugin's skills. It is the counterpart of the Claude Code skill (`docs/claude-code.md`): it holds the same things in Codex's terms and no rule, format or role text. A run has the same agents, the same launch lines and the same workspace in both tools.

## What Codex does differently

- **Starting an agent.** `spawn_agent` takes `fork_turns`, and its default, `"all"`, gives the new agent the whole conversation of the agent that starts it. The skill sets `"none"` at every start; without it every reviewer would start with the author's view. A started agent also gets what Codex gives every agent: the person's `AGENTS.md` files and the list of skills, as a Claude Code agent gets `CLAUDE.md`.
- **The model.** `spawn_agent` also takes `model` and `reasoning_effort`, and a started agent keeps both on every later turn. The session's own agent runs on the model Codex was opened with, which a skill cannot set, so the author is a started agent here too.
- **Every agent can start agents,** as in Claude Code, where a general-purpose started agent has the Agent tool and started an agent in a test with Claude Code 2.1.314. The author could start its reviewers itself; both skills keep the starter doing it, so that what the author's reply holds for the person reaches them while a review runs, and both tools run the same graph.
- **Continuing an agent.** The starter gives a reply or the person's answer to the author with `followup_task`. A started agent outlives the starter's turn, so the starter shows the person what the author has for them, ends its turn, and passes on the person's next message.
- **The scripts are run with `.venv/bin/python`, not `uv run`.** Codex's `workspace-write` sandbox lets a command write only in the folder the session is open in and the temporary folders, and lets it read everywhere. `uv run` opens uv's cache in the home folder and fails; with a cache inside the project it fails on the network instead. The starter makes the project folder's `.venv/` once with `uv sync`, outside the sandbox, which Codex asks the person to approve; the scripts then run in the sandbox, read from the plugin's folder and write in the workspace.
- **No PDF.** Codex has no tool that reads a PDF: `view_image` takes image files, and the rest run commands or open web pages. The transcriber must read the PDF itself, so a run in Codex takes LaTeX source only, and the skill has the starter tell a person who gives a PDF. A transcriber that read the page images in `pages/` instead would need a sentence in `prompts/roles/transcriber.md` and has not been tried.

## Started by another skill

As in Claude Code (`docs/claude-code.md`, "Started by another skill"): the person or another skill the session's agent is running can start the skill, the session's agent is the starter either way, the four decisions stay the person's, and the starter ends with the same four lines once `review-log.md` reads `Chain: accepted`. A PDF is refused as when the person gives one, and no such lines follow.

## Where the files are, installed

Codex reads the marketplace from `.claude-plugin/marketplace.json`, the file Claude Code reads, and copies an installed plugin to `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/`. It takes `.codex-plugin/plugin.json` over `.claude-plugin/plugin.json`, so it loads the Codex skill and not the Claude Code one in `skills/`.

Codex documents no variable for a skill's folder, but it gives the agent each skill's absolute path. The starter takes the project folder as the folder three levels above the skill file and passes it to the author as `Project folder:`; a reviewer finds it from its role file, as in Claude Code. The workspace is made in the folder the session is open in, the one folder the sandbox lets a command write in.

## The model

The skill names no model: the person chooses the model and the effort in the Codex session, and the starter starts every agent without `model` or `reasoning_effort`, so each takes the starter's. `spawn_agent` describes this itself ("inherited parent model is preferred"); it was not run. The person asked for this in place of a model fixed in the file.

## What was checked, with Codex CLI 0.162.1

Each with `codex exec` in a copy of the project that held only the public test paper, before the project was a plugin.

- Codex lists the skill from `.agents/skills/` without the folder being marked as trusted. It does not list the Claude Code skill.
- An agent started with `fork_turns` `"none"` did not know a word written in the starter's prompt, and its first message was the lines it was started with. A start with `"all"` cannot be made in `codex exec --ephemeral`, which keeps no history to hand on.
- The started agent's session file records the model and effort it was started with (the check used `gpt-6-astra` at `high`, with the starter on another model), on its first turn and on a turn given with `followup_task` after the starter's session had ended and was resumed.
- An agent asked to read a page of a one-page PDF with its own reading found no tool for it.
- In the `workspace-write` sandbox, `uv run python scripts/check.py --help` failed on uv's cache, and `.venv/bin/python` ran `convert.py` on LaTeX source and `check.py` (`codex sandbox`, the same sandbox without a model).

Then the plugin form, with a `CODEX_HOME` of its own and no model run:

- `codex plugin marketplace add` on the repository's folder read `.claude-plugin/marketplace.json`, and `codex plugin add paper-logical-chain@paper-logical-chain` copied the plugin into the cache.
- `codex debug prompt-input`, run in another folder, listed `paper-logical-chain:paper-chain` from `.agents/skills/` with its absolute path, and not the Claude Code skill.
- `codex sandbox` in `workspace-write`, with the temporary folders excluded so that the cache was outside every writable folder: writing in the plugin's folder failed, `uv sync` failed on uv's cache, and after `uv sync` outside the sandbox, `.venv/bin/python` ran `convert.py` on LaTeX source and `check.py` with the workspace in the session's folder.

Not checked: an install from the published repository, a whole run, and whether the agents a long run starts reach the cap on open agents, `agents.max_concurrent_threads_per_session`, which Codex chooses when it is unset. The person who opens Codex can set it in their own configuration.
