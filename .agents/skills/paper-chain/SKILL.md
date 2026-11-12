---
name: paper-chain
description: Build the logical chain of one research paper, section by section, with a fresh reviewer after each section, a final review, and the person's feedback. Use when the person gives a paper (a folder of LaTeX source) and asks for its logical chain, or asks to go on with a run in an existing workspace.
---

# Paper chain

This file says only how a run is carried out in Codex: who starts whom and on which model, where the workspace is, how the scripts are run, and how the person is asked. Every rule of the work is under `prompts/` in the project folder, the folder that holds `prompts/` and `scripts/`, and none is repeated here. The project folder is the folder three levels above this file, which is `.agents/skills/paper-chain/SKILL.md` in it, and not the folder the session is open in.

Two agents read this file. The agent of the session in which the person started the skill is the **starter**. The agent it starts to write the chain is the **author**.

## Models

Every agent of a run is on the model and reasoning effort the person chose for this session: start the author and each reviewer with no `model` and no `reasoning_effort`, and each takes yours. If the person names a model or an effort for the run, pass that to every start.

- Why the author is still a started agent: the person can change the session's model between turns, and a started agent keeps what it was started on.

## The starter

You write nothing of the chain and read nothing of the paper. You start agents and pass messages.

1. **The paper.** A run in Codex takes the paper's LaTeX source only. If the person gives a PDF, tell them so, and that Claude Code can run from a PDF: the transcriber must read the PDF itself, and no tool of Codex reads a PDF.
2. **The workspace.** It is the folder the person names. If they name none, make `workspaces/<the paper's subject in full words>/` in the folder this session is open in, with the subject as the person gave it; ask if they did not. `<input>` is the first author's family name and the year, such as `lee2024`; take it from the person, and ask if they did not give it.
3. **The scripts' Python.** If the project folder has no `.venv/`, run `uv sync` in the project folder, outside the sandbox: it writes in the project folder and downloads packages, and the sandbox allows neither.
4. **Start the author** with `spawn_agent`: `fork_turns` `"none"`, the model as above, no `agent_type`, and as `message` these lines and nothing else, with absolute paths:

   ```
   Skill file: <this file>
   Project folder: <the project folder>
   Paper: <the folder of LaTeX source, or its main .tex file>
   Input name: <input>
   Workspace: <workspace>
   Chain language: <the language the person asked for the chain in; leave this line out when they asked for none>
   Another agent started you.
   ```

   To go on with a run that stopped, start a new author the same way on the same workspace.
5. **When the author's reply ends with the lines for a reviewer**, start a reviewer with `spawn_agent` the same way, with exactly those lines as its `message`. What the reply holds for the person above those lines, show the person, and do not wait for their answer: an answer that comes while an agent runs goes to the author after that agent's reply. Wait for the reviewer's final answer, and give it to the author with `followup_task` and nothing else.
   - Why `fork_turns` `"none"` at every start: its default gives the new agent your whole conversation, and a reviewer must not have the author's view, nor the author yours.
6. **When the author's reply ends with something for the person**, show it to the person and end your turn. Give the author their answer as they gave it, with `followup_task`.

## The author

You are the author of this run. The project folder is the one on your line `Project folder:`. Your instructions are `prompts/roles/author.md` in it. Read that file and follow it. The rest of this section says how three things are done here.

**Running the scripts.** Run both from the project folder with the project's own Python, `.venv/bin/python`, which the starter has made. Codex's sandbox stops `uv run`, which needs uv's cache outside the project folder.

Convert, once, before you read anything of the paper. A workspace that already has a `review-log.md` is a run to go on with: do not convert again.

```
.venv/bin/python scripts/convert.py <folder of LaTeX source, or its main .tex file> <input> <workspace> [--support <folder>]
```

`--support` names a second folder that holds files the main file includes, such as its figures, when they are not beside it.

- Exit code 0: converted, no disagreement.
- Exit code 1: converted, with one or more disagreements, each printed on a line. Stop, and have the person shown those lines and asked whether to go on. Read nothing in `source/` until they answer.
- Exit code 2: not converted. Have the person shown the message.

Check, whenever `prompts/roles/author.md` says to run the check script:

```
.venv/bin/python scripts/check.py <workspace>
```

It writes `check-report.md` in the workspace. Exit code 0 is pass and 1 is fail.

**Asking for a reviewer.** End your reply with these five lines, with absolute paths, and stop. The starter starts the reviewer, though you could: that way the person is shown what your reply holds while the review runs. You are continued with the reviewer's reply, which is its verdict and the number of issues; the review is in the file.

```
Reviewer role file: <project folder>/prompts/roles/reviewer.md
Kind of review: <a spine review, a section review, a second look, or the final review>
Workspace: <workspace>
Under review: <what is under review>
Write your review to: <the review file>
```

**Asking the person.** The starter carries everything between you and the person. End your reply with what the person is to be shown or asked, and stop. You are continued with their answer. To show the person something without waiting for an answer, such as the spine, put it above the lines for a reviewer.
