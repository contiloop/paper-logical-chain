# Decisions and why

For whoever changes the design. No agent of a run reads this file.

## What a chain is

- **The chain tells the paper's argument and does not report on the paper.** A chain is for a talk. How the paper is written, what it cites, what it leaves undone and where it could be faulted are not part of the talk. Earlier chains held such remarks at almost every step, and the person, reading a chain of their own paper, cut them.
- **The author writes the spine first: the paper's conclusion and the claims it rests on.** A step is a link of the spine, and the test for anything in the chain is whether the way to the conclusion still stands without it. Written section by section with no spine, a chain gave every part of the paper its steps and what is core was never decided. On the person's paper the chain went from 21 or 22 steps to 14.
- **A reason is a gist with a link.** A chain held to giving each reason in full came out longer than the paper it described. Every paragraph of the converted paper has an anchor, so the explanation stays in the paper and the chain links it.
- **A result is told as the paper claims it.** A table or a figure is set against the paper's words only where the claim no longer stands. One measure among several that goes the other way does not make a general claim false, and a chain that sets such places against the claim is reviewing the paper.
- **The rules state intent.** `prompts/rules.md` says what a chain is and three things that must hold, and they are judged as the person giving the talk would judge them. See "Rules made from one correction" below for what this replaced.
- **What a model already does well is not written.** The instruction files were cut to what an agent would not do or know unasked.

## How a run is built

- **The chain is written directly from the paper.** See "The file layer" below.
- **One author for the whole run.** How the sections connect is visible only to an agent that has read the whole paper.
- **A new reviewer for each review, started with five fixed lines.** An agent that shares the author's context shares its misreadings.
- **A reviewer reads the chain before the paper, and writes down where its reader gets stuck.** A reviewer that has read the paper supplies a missing reason without noticing. `docs/findings.md` has the test that showed it.
- **A reviewer reads the chain a second time by subject.** Two statements several steps apart are met together only that way.
- **One section at a time, and the author waits for each review.** Each section's steps build on reviewed steps, and a whole chain reviewed at once lets an early error carry into every later step.
- **The author judges every issue against the paper.** A reviewer can be wrong, and an issue that is right about the paper can still add what the chain should not hold. The author takes a reviewer's correction and not its sentence: a suggested wording has carried an overstatement into a chain.
- **Two rounds on an issue, then open.** Without a limit the loop need not end.
- **Changes that touch most of the chain get a final review, not a second look.** A second look has no reading of the chain alone. A rewrite of a whole chain dropped hedges in a third of its steps and a second look found none of them.
- **Agents exchange information only through files in the workspace, one writer per file.** A run can stop and resume, and nothing depends on one tool.
- **The reviewer's list of questions grows only with the person's approval.** When the person asks something no review asked, the author words it as a kind of question for any paper and the person decides.
- **The person is the final judge.** No command can judge a chain.

## Conversion

- **LaTeX is kept as written.** The convert script puts included files in place, removes comments and adds an anchor to every paragraph and item. It does not translate the LaTeX and does not compute the numbers the compiled paper prints. Agents read LaTeX directly and cite the right places.
- **A PDF is transcribed by an agent, with the agent tool's own PDF reading.** Nothing is installed for PDF. The transcription is written to a file, although the transcriber has already read the paper, because the chain needs anchors to link and every later agent needs the same text.
- **Figures and tables of a PDF are cut out as separate images.** A page image has too little resolution, and a transcription can garble a table with no sign of it in the text. The author and the reviewer check a table by looking.
- **A disagreement in the conversion stops the run for the person.** After conversion no agent opens the paper itself, so what conversion lost is invisible to all of them.

## Claude Code

- **The session's agent starts the author as a separate agent.** The person chose the model `opus` at the effort `high` for every agent of a run, and a session's own agent does not stay on a set model across the turns of a run. `docs/claude-code.md` has the rest.

## Codex

- **The Codex part is a second skill with the same agents and launch lines.** Codex starts an agent with the starter's whole conversation unless told not to, and the skill tells it not to at every start. `docs/codex.md` has the rest.
- **A run in Codex takes LaTeX source only.** Codex has no tool that reads a PDF, and nothing is installed for PDF.

## The plugin

- **The repository is the plugin and its own marketplace, for both tools.** A person installs it from the repository in two commands and runs it from any folder. Codex reads the marketplace file Claude Code reads, and `.codex-plugin/plugin.json` leads it to the Codex skill.
- **The plugin's folder holds the instructions and the scripts; the session's folder holds the workspace.** An installed plugin's folder is replaced by each update, and Codex's sandbox lets a command write only in the session's folder.
- **The starter passes the project folder to the author as an absolute path, and each role file names it as the folder that holds its `prompts/`.** An agent started with only a path cannot tell which folder a path such as `prompts/rules.md` is in, and the session's folder is no longer that folder.
- **The stage is called through its skill, not through an MCP server.** The person is building a pipeline (chain, then dialogue, then video) that an orchestrator built elsewhere assembles, and decided that the orchestrator asks for this skill. An MCP server was designed, with tools for conversion and the check and a tool naming the role files, and dropped: what it adds is tools a host can use without the skill, and nothing would use them, because the stage's work is starting the author and fresh reviewers, which only a skill directs a host's agent to do. The scripts know nothing of agents, so such a server can be put around them if a host ever needs the tools without the skill.
- **The scripts' environment is made in the plugin's folder on first use.** `uv run` makes it in Claude Code; in Codex the starter runs `uv sync` outside the sandbox. Nothing is installed by a step the person must remember.

## Tried and dropped

- **The file layer.** The earlier design put a file for every section, figure, table and theorem between the paper and the chain, with a manifest and a script that accounted for every paragraph. It was most of a run's cost. In the one run where a person read the chain, every gap they found was a place where those files held the content and the chain had dropped it.
- **Rules made from one correction.** Each sentence the person did not want first became a rule: no remark on what the paper leaves open, no label of the kind of support, no step for related work, no narration of a citation. Each rule was then applied where it did not fit, and the next chain had a new unwanted sentence of another form. The person asked for intent in place of the list. A correction is now met by finding which instruction produced the sentence. An example: an experiment's setup paragraph held every setting because the format said only that the conditions are given once.
- **Recording what the paper leaves open.** First at every step (74 remarks in one chain), then only where a claim rests on the answer, then not at all.
- **An answer key of places where a table seems to go against the text, as a pass condition for a run.** Such a place does not make a claim false (see "A result is told as the paper claims it"), and the person withdrew the condition.
- **pandoc for LaTeX.** It did not finish on the test paper's macro file.
- **LaTeXML for LaTeX.** It gives the compiled paper's numbers, and needed a matching TeX installation of 1.2 GB and about half an hour to install. The person judged the numbers not worth that.
- **A comparison of PDF converters.** The person chose the agent tool's own reading because it needs no install.
- **One agent per section, in parallel.** The links between sections then had to be made by a step that saw only summaries.
- **A talk brief as input.** A chain shaped for one talk cannot be reused. What changes a chain for a talk is the person's feedback.

## Open

- Whether the spine should wait for the person's confirmation before the sections are written. Today the person is shown the spine and the run goes on.
- How many papers one author can hold. Several papers in one chain are out of scope.
