# TODO

- [ ] ...

# Dependencies (Not In Standard Python)

- `redis`
- `psycopg`

# Overview

- The **Reporter** system behaves similarly to the **Agent**; files (plugins)
  found in the directory `massaffect/report` are enumerated and run, some with
  optional TOML configurations. It is typically run *alongside* the
  **Controller**.

- Each `massaffect.report.Report` evaluates conditions and returns results that
  describe the current health state of one or more **Agents**.

- Reports operate in one of two execution modes:

  - *PER_AGENT* (default)

    The **Reporter** enumerates all known agents (via the Redis key
    `ma:agent:index`) and calls the report once per agent:

        evaluate(ctx, agent) → (status, info)

    The report returns:

      - `status` — a boolean indicating whether the report condition is
        currently active (`True`) or normal (`False`) for the given agent.

      - `info` — a JSON-serializable payload containing contextual information
        relevant to the evaluation (for example load averages, disk usage,
        request counts, etc.).

  - *GLOBAL*

    Some reports need to evaluate multiple agents together (for example cluster
    health or hypervisor/VM relationships). In this mode the report performs its
    own enumeration and yields results:

        yield (agent, status, info)

- The **Reporter** uses Redis to track the current alert state for each
  `(agent, report)` pair using the key:

      ma:agent:{agent}:report:{report}

  The presence of this key indicates that the alert is currently active.

- When the **Reporter** evaluates a result, it compares the returned `status`
  against the Redis state key to detect transitions:

      False → True   → alert triggered
      True  → False  → alert resolved

  Only transitions generate notifications or persisted report events.

- When a transition occurs, the **Reporter** records the event in the `reports`
  table in Postgres for historical analysis and auditing.

# Redis State

ma:agent:{agent}:report:{report}

Key exists -> alert currently active
Key missing -> normal state
