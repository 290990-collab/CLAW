## Orchestration: orchestrator and worker

This project's model, and the framework's default. The coordinator spawns the subagents and receives their report; **subagents do not communicate sideways**: a question outside the mandate goes back to the coordinator, who passes it to whoever needs it. Parallelism follows rule 1, session reuse rule 8.
