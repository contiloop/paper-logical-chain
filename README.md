# Paper logical chain

Turns one research paper into a logical chain: the paper's argument told in numbered steps, each linked to the place in the paper it rests on. A person builds a talk from the chain without re-reading the paper.

It is a plugin for Claude Code and for Codex. The person gives a paper, as a folder of LaTeX source or, in Claude Code only, a PDF, and reads the chain at the end.

## Install

`uv` must be on the machine. Nothing else is installed by hand: the first run makes the scripts' Python environment inside the plugin's folder.

In Claude Code:

```
/plugin marketplace add contiloop/paper-logical-chain
/plugin install paper-logical-chain@paper-logical-chain
```

In Codex, from the shell, then start a new session:

```
codex plugin marketplace add contiloop/paper-logical-chain
codex plugin add paper-logical-chain@paper-logical-chain
```

## Use

Open Claude Code or Codex in the folder where the run's files should go, start the skill `paper-chain` (in Claude Code `/paper-logical-chain:paper-chain`) with the paper's path, and name a language if the chain is not to be in English. The chain is written to `workspaces/<the paper's subject>/logical-chain.md` in that folder.

In Codex the first run asks to run `uv sync` in the plugin's folder outside the sandbox, once for each version of the plugin: it writes there and downloads packages, which the sandbox does not allow.

## Calling it from another orchestrator

A pipeline that goes on from the chain, to a script or a video, runs this stage by having its own skill ask for `paper-chain` in the same session: `paper-logical-chain:paper-chain` in Claude Code, the skill `paper-chain` of the plugin `paper-logical-chain` in Codex, which takes LaTeX source only. The session's own agent then runs the stage. A started agent cannot, because it cannot reach the person.

The orchestrator's instructions may give the paper, the workspace, the input name (the first author's family name and the year, such as `lee2024`) and the chain's language. Four decisions stay with the person and are answered only in their own words: whether a run goes on after a **disagreement** in conversion, each round of **feedback**, **acceptance** of the chain, and each addition to the **reviewer's list of question kinds**.

When the person accepts the chain, the stage ends with these lines, with absolute paths:

```
Chain accepted.
Workspace: <workspace>
Chain: <workspace>/logical-chain.md
Source: <workspace>/source/<input>/
```

The person can give feedback after accepting, which starts a new round; the latest such lines are the ones that count. The `Chain:` line of `review-log.md` says how far a run has got, but it can still read `accepted` during that new round.

What the next stage reads is defined in `prompts/`: the workspace in `prompts/work-graph.md`, the chain in `prompts/formats/logical-chain.md`, the converted paper in `prompts/formats/source.md`. Each step links the place in the paper it rests on as `source/<input>/paper.md#<anchor>`, relative to the workspace.

## Develop

```
./install.sh
uv run pytest
```

`install.sh` sets up the scripts' environment in `.venv/` and downloads the paper the tests use (arXiv 2506.01523v2, source and PDF) into `local/papers/yun2025/`. `uv`, `curl` and `tar` must be on the machine; a Python that `uv` has to download goes into `local/python/`. Deleting the folder and installing again gives the same state.

To run the working copy: in Claude Code, start `claude --plugin-dir <this folder>`; Codex finds the Codex skill as a repository skill when it is opened in this folder. `claude plugin validate .` checks the plugin and marketplace files.

## Layout

```
.claude-plugin/              plugin.json and marketplace.json: the plugin and its marketplace, read by Claude Code and by Codex
.codex-plugin/plugin.json    leads Codex to the Codex skill
skills/paper-chain/          the Claude Code part
.agents/skills/paper-chain/  the Codex part
prompts/     everything an agent of a run reads: the rules, the formats, the roles
scripts/     convert.py and check.py, and the modules they use
tests/       tests of the scripts and of the prompts, and under tests/inputs/ the inputs of the reviewer tests
docs/        for whoever changes the system
install.sh   for whoever changes the system: the scripts' environment and the test paper
local/       not committed: the downloaded test paper, and words the prompt tests keep out
workspaces/  not committed: the runs made in this folder
```

## How the parts fit

A run has three parts that know nothing of each other's insides.

| Part | Does | Knows nothing of |
|---|---|---|
| `scripts/` | turns a paper into `source/<input>/` in the workspace, and checks that every link of a chain resolves | agents |
| `prompts/` | says what a chain is, what each agent does and what each file holds | any agent tool |
| a skill, one for each agent tool | starts each agent on a set model, runs the scripts, carries the person's words | the rules |

A run goes: convert → the author writes the spine (the paper's conclusion and the claims it rests on) → a reviewer checks the spine → for each section of the paper, the author writes steps and a reviewer with a fresh context reviews them → a final review of the whole chain → the person reads it and gives feedback or accepts. `prompts/work-graph.md` has the jobs and what passes between them.

Each agent tool has its own skill: `skills/paper-chain/SKILL.md` for Claude Code and `.agents/skills/paper-chain/SKILL.md` for Codex. A run has the same agents, launch lines and workspace in both. The plugin's folder, which holds `prompts/` and `scripts/`, is the project folder of every instruction; the run's workspace is in the folder the session is open in. A part for another tool would be one more skill.

## Where to change what

| To change | Edit only |
|---|---|
| What a chain is and what must hold of it | `prompts/rules.md` |
| The layout of a file | its file in `prompts/formats/` |
| What a reviewer looks for and how it reports | `prompts/roles/reviewer.md`, `prompts/formats/review.md` |
| What the author does and in what order | `prompts/roles/author.md`, `prompts/work-graph.md` |
| The model and effort of the agents, how an agent is started | in Claude Code `skills/paper-chain/SKILL.md`, described in `docs/claude-code.md`; in Codex `.agents/skills/paper-chain/SKILL.md`, described in `docs/codex.md` |
| How a paper is converted | `scripts/`, described in `docs/scripts.md` |
| The plugin's name, description or licence | `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` and `.claude-plugin/marketplace.json` together |

The author and every reviewer read the same rules and formats, and no file copies their text.

When a chain holds a sentence the person does not want, the cause is in an instruction: find the line under `prompts/` that produced it and change that line. A prohibition added for one sentence is applied where it does not fit. `docs/decisions.md` has the cases.

## What is not committed, and why

- `local/` and `workspaces/`. No paper is committed and nothing made from one: a paper may be unpublished, and a run's output is of use only with its paper.
- Words that name a paper of the person's own: they go in `local/private-words.txt`, one regular expression a line, and the prompt tests check that no instruction file and no plugin file holds them.
- No file under `prompts/` holds content of a paper the system is tested on, and none points an agent to `docs/` or `tests/`, which hold answer keys. The same holds for the two skills and the plugin files. `tests/test_prompts.py` checks this.

## Licence

MIT, in `LICENSE`.
