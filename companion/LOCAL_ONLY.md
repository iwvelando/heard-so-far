# heard-so-far: local sources and practical enforcement

`AGENTS.md` is the reading protocol. It is an instruction layer, not an access
control boundary. A fresh task in this project should load it and read the saved
progress. Start in the project root, not an unrelated workspace. Keep reading
tasks separate from any conversations that have used outside book information.

The project config requests disabled web search and disabled outbound networking
for workspace-sandbox commands. These are documented Codex settings, but effective
permissions depend on the client, trust, and higher-priority policy. They do not
remove tools from an already-running conversation. Validate effective permissions
in a new task; a syntactically valid config is not proof that every tool is restricted.

This is not complete network isolation. Browser, Computer Use, app/connector,
and MCP access are separate surfaces. The reading instructions forbid their use
as outside sources. For stronger enforcement, disable those capabilities for the
reading environment as well. Project settings are defaults and can be overridden;
managed requirements or a restricted tool allowlist provide stronger enforcement.
Do not disable connections globally as part of a routine reading query.

`transcribe_section.py` loads cached weights with `HF_HUB_OFFLINE=1`. That prevents
the model loader from fetching missing weights; it is not an operating-system
firewall. GPU access may require execution outside the normal command sandbox
on macOS. Keep that permission narrowly scoped to the offline transcription
command. Do not grant broad network access for reading sessions. Model downloads
are a separate, explicit setup step.

The answering model is accessed through your agent client. Local-source answers mean
that the book evidence comes from local files, not that LLM inference happens
offline. Transcript excerpts read by the agent enter the model's context.
The supplied configuration template applies only to Codex; other clients must
configure their own tool permissions. CLAUDE.md imports the shared reading rules
but does not install a network policy.

The strongest separate setup would give the answering process only a prepared,
read-only directory of permitted excerpts, with no browser, connectors, general
shell, raw audiobook, or transcripts beyond the cutoff. A separate local
preprocessor would populate that directory. The current same-workspace agent can
access the audiobook and edit its tools, so its cutoff safeguards remain partly
instruction-based. This separate architecture has not been implemented.

Even a tool-restricted LLM can invent details or draw on training knowledge.
Timestamped evidence, narrow claims, explicit uncertainty, and the user's
corrections remain necessary; neither this file nor any sampling setting proves
that an answer contains zero unsupported or spoiler-bearing claims.

Official product references (consulted for setup, not book information):

- [Project instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Separate network and tool controls](https://learn.chatgpt.com/docs/agent-approvals-security)
