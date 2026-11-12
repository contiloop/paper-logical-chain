# Running in Claude Code

For whoever changes the system. The Claude Code part is one skill, `skills/paper-chain/SKILL.md`, where Claude Code looks for a plugin's skills, and the plugin and marketplace files in `.claude-plugin/`. The only other tool-specific part is the Codex skill and its plugin file, described in `docs/codex.md`.

## What the skill holds, and what it must not

The skill says who starts whom and on which model, where the workspace is, how the two scripts are run and what their exit codes mean, and how a reviewer and the person are reached.

It holds no rule, format or role text. An instruction that stands in the skill and under `prompts/` drifts apart, and a reviewer never reads the skill, so a rule placed there binds the author alone.

## Who runs what

The agent of the session in which the person starts the skill is the starter. It writes nothing of the chain and reads nothing of the paper. It starts the author as a new agent, starts each reviewer when the author asks for one, for a PDF starts the transcriber the same way, and carries the person's answers to the author.

- **Why the author is a started agent.** The person chose the model `opus` at the effort `high` for every agent of a run. A model set in a skill's frontmatter holds for the current turn only, and the session's own model returns with the next prompt, so the session's agent cannot be the author on a fixed model across a run of many turns. A started agent keeps the model it was started on.
- **Why the starter passes nothing but the fixed messages.** The author is started with the skill file, the project folder, the paper, the input's name, the workspace, the chain's language when the person asked for one, and the line that another agent started it. A reviewer is started with the five lines the author ends its reply with. The starter continues the author with the reviewer's reply, or the person's answer, and nothing else. The starter may know things the author must not, such as an answer key in a test, and the reviewer must not have the author's view.
- **Never a fork.** A fork inherits the conversation of the agent that starts it.
- **The author waits for each reviewer.** Each section's steps build on reviewed steps, so nothing is written while a review runs.
- **A reviewer's reply is its verdict and a count.** The review reaches the author as a file, which keeps the author's context, the longest in a run, from filling with reviews.

A run that stops is resumed by starting a new author on the same workspace.

## Where the files are, installed

Claude Code copies an installed plugin to `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` and loads it from there; each version is a new folder. That folder is the project folder: it holds `prompts/` and `scripts/`. The session is open in the person's own folder, where the starter makes the workspace.

- **The starter gives the author the project folder.** Claude Code puts the plugin's folder in place of `${CLAUDE_PLUGIN_ROOT}`, and the skill's folder in place of `${CLAUDE_SKILL_DIR}`, in the skill as it loads it for the starter. The author reads the skill file with its own reading, which leaves them as written, so the starter passes both as absolute paths on the author's launch lines. The variables are not in the environment of a Bash command.
- **A reviewer and the transcriber find it from their role file.** They are started with the absolute path of their role file, and each role file says that a path beginning with `prompts/` is in the folder that holds the `prompts/` folder it is in.
- **The scripts' environment is made on first use.** The author runs `uv run` in the project folder, and the first run makes `.venv/` there. A new version of the plugin makes its own on its first run.

To try a working copy without installing it, start `claude --plugin-dir <the copy>`: Claude Code loads it in place, with the same variables.

## Reading a PDF

No PDF converter is installed. The transcriber reads the PDF with Claude Code's own file reading, which takes a PDF by ranges of pages, at most 20 pages in one request, and it is started with three lines only, so nothing in the skill tells it this: the tool's own description does. The commands of the script's part of a PDF conversion are in `prompts/formats/source.md`, the one place they are written, and the skill points there.

## The model

One line of the skill, under "Models", sets the model and the effort of every agent of a run. Change it there.
