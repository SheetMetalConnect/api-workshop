How is it possible that Claude Sonnet 4.5 is able to work for 30 hours to build an app like Slack?!   The system prompts have been leaked and Sonnet 4.5's reveals its secret sauce!

Here’s how the prompt enables Sonnet 4.5 to autonomously grind out something Slack/Teams-like—i.e., thousands of lines of code over many hours—without falling apart:

It forces “big code” into durable artifacts. Anything over ~20 lines (or 1500 chars) is required to be emitted as an artifact, and only one artifact per response. That gives the model a persistent, append-only surface to build large apps module-by-module without truncation.

It specifies an iterative “update vs. rewrite” workflow. The model is told exactly when to apply update (small diffs, ≤20 lines/≤5 locations, up to 4 times) versus rewrite (structural change). That lets it evolve a large codebase safely across many cycles—how you get to 11k lines without losing state.

It enforces runtime constraints for long-running UI code. The prompt bans localStorage/sessionStorage, requires in-memory state, and blocks HTML forms in React iframes. That keeps generated chat UIs stable in the sandbox while the model iterates for hours.

It nails the dependency & packaging surface. The environment whitelists artifact types and import rules (single-file HTML, React component artifacts, CDNs), so the model can scaffold full features (auth panes, channels list, message composer) without fighting toolchain drift.

It provides a research cadence for “product-scale” tasks. The prompt defines a Research mode (≥5 up to ~20 tool calls) with an explicit planning → research loop → answer construction recipe, which supports the many information lookups a Slack-like build needs (protocol choices, UI patterns, presence models).

It governs tool use instead of guessing. The “Tool Use Governance” pattern tells the model to investigate with tools rather than assume, reducing dead-ends when selecting frameworks, storage schemas, or deployment options mid-build.

It separates “think” and “do” with mode switching. The Deliberation–Action Split prevents half-baked code sprees: plan (deliberation), then execute (action), user-directed. Over long sessions, this avoids trashing large artifacts and keeps scope disciplined.

It supports long-horizon autonomy via planning/feedback loops. The prompt’s pattern library cites architectures like Voyager (state + tools → propose code → execute → learn) and Generative Agents (memory → reflect → plan). Those loops explain how an LLM can sustain progress across dozens of hours.

It insists on full conversational state in every call. For stateful apps, it requires sending complete history/state each time. That’s crucial for a chat app where UI state, presence, and message history must remain coherent across many generation cycles.

It bakes in error rituals and guardrails. The pattern language’s “Error Ritual” and “Ghost Context Removal” encourage cleaning stale context and retrying with distilled lessons—vital when a big build hits integration errors at hour 12.

It chooses familiar, well-documented stacks. The guidance warns about the “knowledge horizon” and recommends mainstream frameworks (React, Flask, REST) and clean layering (UI vs. API). That drastically improves throughput and correctness for a Slack-like system.

It enables “Claude-in-Claude” style self-orchestration. The artifacts are allowed to call an LLM API from within the running artifact (with fetch), so the model can generate a dev tool that helps itself (e.g., codegen assistant, schema migrator) during the build.

It keeps outputs machine-parseable when needed. Strict JSON-only modes (and examples) let downstream scripts/tests wrap the app and auto-verify modules, enabling unattended iteration over many hours.

Put together, these prompts/patterns create the conditions for scale: a safe sandbox to emit large artifacts, iterative control over code evolution, disciplined research and tool usage, long-horizon memory/plan loops, and pragmatic tech choices. That’s how an LLM can realistically accrete ~10k+ lines for a Slack-style app over a long session without collapsing under its own complexity.
