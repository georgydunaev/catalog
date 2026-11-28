# What the operator asked for (summary of collected inputs)

Source: `collect_operator_inputs.py` (in this folder) read the logs of Claude Code, opencode and
Antigravity ("agy") on 2026-11-28. Prompts that agents generated for other agents are filtered out.
That left 246 operator messages: Antigravity 161, Claude Code 44, opencode 41. The raw file
`raw/operator_inputs.jsonl` stays on this machine only (git-ignored), because some messages are
private. This summary keeps only instructions about the work. Where an instruction recurs, it is
stated once, in its latest form.

## 1. Clarity before features
- The biggest risk is a reader (for example an academic administrator) who does not understand
  something. Clarity matters more than features.
- Reduce informational noise. Delete more text than you add. Remove hallucinations,
  falsifications and contradictions. Resolve sources of confusion systematically, with tools where
  possible. Do not finish everything in one session.
- No decorative separators (`----`, `====`), no emoji in code, tests, logs or commits.
- Be honest and realistic. "We produced a lot of slop together": written text is not therefore
  true. Claims on public pages need a proof or a citation. AI-written claims such as "proves
  Con(ZFC)", "Dedukti certificates" or "verified in Isabelle" are to be treated as unfounded.

## 2. Define, then generate
- Define what an entity *is* as an SML datatype (for example: what a symbol is). Generate the
  displays from the definitions.
- Every displayed thing should have a corresponding datatype.
- Reuse files; avoid duplicated code and text. A string used twice or more should be a constant.
- Prefer SML to Python for the project's own algorithms.

## 3. Names and notions
- Use exactly `MKTD1-framework`, `MKTD1-theory`, `MKTD1-system` (`-prover` is a synonym), and the
  same for MKTD2. No other wording.
- Facts are named, not numbered.
- Symbols are predicate or functional symbols in the logical sense. A multi-word symbol such as
  "concentrated set values" is one symbol. Symbols have types.
- Substitution is shown with all three arguments (what, instead of what, where).
- Keep `EpsIndAx` exactly as written (∈-induction); regularity may be derived from it when needed.
- In the classical ontology of 𝘛 / 𝘍, ω is one object however it is defined; a defined constant
  such as ω cannot be redefined (`ω := V` must be impossible).
- Definitions exist at three moments: kernel constructors, definitions present when the REPL
  starts (standard library), and user definitions. The mechanism for the last two is the same.
- Several proofs of one statement, or an axiom equal to a theorem, are fine; mention it in a comment.

## 4. Mathematics and the kernel
- Kernel soundness and a clear type theory first. Write idealised mathematical models of MKTD1 and
  MKTD2 as two LaTeX articles to see what must improve.
- Long-term: answer metatheoretical questions with theorems of the system itself (for example,
  define substitution inside the theory), starting with a small reduced case.
- Prefer good principles ("simplify, but do not oversimplify") over fast ad-hoc solutions. Maintain
  a declaration of principles.

## 5. Book and sites
- The book (`foundations`) must contain coherent, clear text, and must not contradict the prover.
  AI-written parts become separate books in subfolders; keep the mathematics, remove unfounded
  "formalised in MKTD" claims.
- Every notion in "Theory at a Glance" links to a glossary: a plain white page that only says what
  words mean.
- The personal site contains no mathematical definitions, diagrams or invented milestones, and is
  fact-checked. CSS must not restyle standard elements; use classes.

## 6. Working method
- Commit each verified block and run the synchronisation scripts.
- Step by step when asked; otherwise act without asking about details, and ask only about real
  mathematics or architecture decisions.
- Keep commands short (2-minute limit), respect the 4 GiB memory limit, never use `/hostramdisk`,
  never copy the whole workspace.
- Maintenance projects get git upkeep only, no new features.
- Sub-agents are allowed and encouraged when work is independent.

## Where these are written down
Workspace rules: `/botworkspace/AGENTS.md`. Definitions: `set_theory_prover/FACTBOOK.md`. Meanings
of words: `set_theory_prover/docs/glossary.txt`. Design answers:
`set_theory_prover/docs/decisions.txt`. To refresh this summary, rerun the collector and update
this file by hand.
