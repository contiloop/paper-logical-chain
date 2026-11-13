---
name: paper-chain
description: Build the logical chain of one research paper, section by section, with a fresh reviewer after each section, a final review, and the person's feedback. Use when the person, or another skill this session is running, gives a paper (a folder of LaTeX source, or a PDF) and asks for its logical chain, or asks to go on with a run in an existing workspace.
---

# Paper chain

This file says only how a run is carried out in Claude Code: who starts whom and on which model, where the workspace is, how the scripts are run, and how the person is asked. Every rule of the work is under `prompts/` in the project folder, the folder that holds `prompts/` and `scripts/`, and none is repeated here. The project folder is the folder of this plugin, not the folder the session is open in.

Two agents read this file. The agent of the session that loads this skill is the **starter**, whether the person started the skill or another skill that agent is running asked for it. The agent it starts to write the chain is the **author**.

- Why the session's agent and never a started agent: a started agent cannot reach the person, so the person's decisions would pass through the agent that started it.

## Models

Every agent of a run is started on the model `opus` at the effort `high`: the author, each reviewer, and for a PDF the transcriber. This is the person's choice. To change it, change this line.

- Why the author is a started agent and not the session's agent: a model set for a skill holds for one turn of the session, and a run takes many turns.

## The starter

You write nothing of the chain and read nothing of the paper. You start agents and pass messages.

1. **The workspace.** The paper, the workspace, `<input>` and the chain language come from the person or from the instructions of the skill that asked for this one; ask the person only for what neither gave. The workspace is the folder named. If none is named, make `workspaces/<the paper's subject in full words>/` in the folder this session is open in, with the subject as given; ask if it was not. `<input>` is the first author's family name and the year, such as `lee2024`.
2. **Start the author** with the Agent tool as a new general-purpose agent, on the model and effort above, never as a fork. The prompt is these lines and nothing else, with absolute paths:

   ```
   Skill file: ${CLAUDE_SKILL_DIR}/SKILL.md
   Project folder: ${CLAUDE_PLUGIN_ROOT}
   Paper: <the folder of LaTeX source, its main .tex file, or the PDF>
   Input name: <input>
   Workspace: <workspace>
   Chain language: <the language the person asked for the chain in; leave this line out when they asked for none>
   Another agent started you.
   ```

   To go on with a run that stopped, start a new author the same way on the same workspace.
3. **When the author's reply ends with the lines for a reviewer or for a transcriber**, start that agent with the Agent tool as a new general-purpose agent, on the model and effort above, never as a fork, with exactly those lines as its prompt. What the reply holds for the person above those lines, show the person, and do not wait for their answer: an answer that comes while an agent runs goes to the author after that agent's reply. Wait for the agent to end. Continue the author with its reply and nothing else.
   - Why nothing else, and never a fork: a reviewer must not have the author's view, and the author must not have yours.
4. **When the author's reply ends with something for the person**, show it to the person in the conversation, wait, and continue the author with the person's answer as they gave it.

   Four decisions are the person's: whether the run goes on after the conversion reports a **disagreement**, every round of **feedback** on the chain, the **acceptance** of the chain, and every addition to the **reviewer's list of question kinds**. Answer the author on them only with the person's own words in this conversation: never from the instructions of the skill that asked for this one, even where they say how to answer, and never from your own judgment.
5. **When the chain is accepted.** After you have passed the person's acceptance to the author and the author has replied, read the `Chain:` line of `<workspace>/review-log.md`. If it reads `Chain: accepted`, end your reply in the conversation with these four lines, with absolute paths, filled from the workspace and the input name you started the author with. They end the chain stage: the skill that asked for this one, if any, may go on from them, and nothing of this skill follows them. Write them at no other point.

   ```
   Chain accepted.
   Workspace: <workspace>
   Chain: <workspace>/logical-chain.md
   Source: <workspace>/source/<input>/
   ```

   - Why the recorded line and not the author's reply: `prompts/roles/author.md` gives the author no reply on acceptance. Reading that one line is not reading the paper or the chain.

## The author

You are the author of this run. The project folder is the one on your line `Project folder:`. Your instructions are `prompts/roles/author.md` in it. Read that file and follow it. The rest of this section says how three things are done here.

**Running the scripts.** Run both from the project folder.

Convert, once, before you read anything of the paper. A workspace that already has a `review-log.md` is a run to go on with: do not convert again.

```
uv run python scripts/convert.py <folder of LaTeX source, or its main .tex file> <input> <workspace> [--support <folder>]
```

`--support` names a second folder that holds files the main file includes, such as its figures, when they are not beside it.

- Exit code 0: converted, no disagreement.
- Exit code 1: converted, with one or more disagreements, each printed on a line. Stop, and have the person shown those lines and asked whether to go on. Read nothing in `source/` until they answer.
- Exit code 2: not converted. Have the person shown the message.

From a PDF, conversion takes these moves, and `prompts/formats/source.md` gives the command of each move the script makes. Do them before you read anything of the paper:

1. Run the command that writes the page images.
2. Ask for a transcriber: end your reply with these three lines, with absolute paths, and stop. You are continued with its reply, "done" and a number of disagreements. The transcriber reads the PDF itself, writes `paper.md`, and has each figure and table cut out.

   ```
   Transcriber role file: <project folder>/prompts/roles/transcriber.md
   PDF: <the PDF>
   Write in: <workspace>/source/<input>
   ```

3. Run the `index` command yourself. Its exit codes mean what convert's do above: on 1, stop and have the person shown the disagreements and asked whether to go on.

Check, whenever `prompts/roles/author.md` says to run the check script:

```
uv run python scripts/check.py <workspace>
```

It writes `check-report.md` in the workspace. Exit code 0 is pass and 1 is fail.

**Asking for a reviewer.** End your reply with these five lines, with absolute paths, and stop. The starter starts the reviewer, though you could: that way the person is shown what your reply holds while the review runs, and Claude Code and Codex run the same graph. You are continued with the reviewer's reply, which is its verdict and the number of issues; the review is in the file.

```
Reviewer role file: <project folder>/prompts/roles/reviewer.md
Kind of review: <a spine review, a section review, a second look, or the final review>
Workspace: <workspace>
Under review: <what is under review>
Write your review to: <the review file>
```

**Asking the person.** You cannot reach the person yourself. End your reply with what the person is to be shown or asked, and stop. You are continued with their answer. To show the person something without waiting for an answer, such as the spine, put it above the lines for a reviewer.
