# Host note: no-comments

`SKILL.md` beside this note is upstream pstack `no-comments` at `005d8f6e8ec0`, minus one sentence that pointed at the poteto-mode skill. `comment-sicko.md` is an unmodified copy of upstream `pstack/agents/comment-sicko.md`. See [THIRD_PARTY_NOTICES](../../THIRD_PARTY_NOTICES).

Step 1 spawns the `comment-sicko` agent. A GJC plugin cannot register agents, so copy `comment-sicko.md` into the agent directory's `agents/` folder, for example `~/.gjc/agent/agents/`, or into a project's `.gjc/agents/`. Run the skill from a main session or a lane. The critic cannot run it, because the critic has no `task` or edit tools.

Step 2 mentions `/why` and step 3 mentions `/architect`. GJC has no `why` skill. `/architect` reaches GJC's own architect agent, not pstack's.
