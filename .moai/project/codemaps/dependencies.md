# Dependency Graph

---

## Brain Intra-Package Import Graph

```mermaid
graph LR
    %% Leaf nodes (no brain imports)
    logging_setup["logging_setup"]
    config["config"]
    state["state"]
    analysis["analysis"]
    ytdlp["ytdlp"]
    knowledge["knowledge"]
    voice["voice"]
    website["website"]

    %% First-level consumers
    library["library"] --> config
    library["library"] --> logging_setup
    slskd["slskd"] --> config
    slskd["slskd"] --> logging_setup
    metadata["metadata"] --> config
    metadata["metadata"] --> logging_setup
    llm["llm"] --> logging_setup
    ytdlp["ytdlp"] --> logging_setup
    voice["voice"] --> config
    voice["voice"] --> logging_setup
    website["website"] --> config
    knowledge["knowledge"] --> logging_setup

    %% Second-level consumers
    acquire["acquire"] --> config
    acquire["acquire"] --> library
    acquire["acquire"] --> logging_setup
    acquire["acquire"] --> slskd
    acquire["acquire"] --> ytdlp

    enrich["enrich"] --> config
    enrich["enrich"] --> library
    enrich["enrich"] --> logging_setup
    enrich["enrich"] --> metadata

    research["research"] --> config
    research["research"] --> library
    research["research"] --> knowledge
    research["research"] --> logging_setup

    analyzer["analyzer"] --> config
    analyzer["analyzer"] --> library
    analyzer["analyzer"] --> state
    analyzer["analyzer"] --> logging_setup
    analyzer["analyzer"] --> analysis
    analyzer["analyzer"] --> metadata

    talk["talk"] --> config
    talk["talk"] --> library
    talk["talk"] --> logging_setup
    talk["talk"] --> llm
    talk["talk"] --> voice

    server["server"] --> config
    server["server"] --> library
    server["server"] --> logging_setup

    %% Third-level consumer
    director["director"] --> config
    director["director"] --> acquire
    director["director"] --> library
    director["director"] --> llm
    director["director"] --> logging_setup

    %% Orchestrator
    main["main"] --> config
    main["main"] --> logging_setup
    main["main"] --> state
    main["main"] --> library
    main["main"] --> director
    main["main"] --> acquire
    main["main"] --> analyzer
    main["main"] --> enrich
    main["main"] --> talk
    main["main"] --> knowledge
    main["main"] --> research
    main["main"] --> server
    main["main"] --> website

    %% Highlight hubs
    style config fill:#f96,stroke:#c00,color:#000
    style logging_setup fill:#f96,stroke:#c00,color:#000
    style library fill:#fa0,stroke:#c60,color:#000
    style state fill:#fc6,stroke:#c60,color:#000
```

---

## Adjacency List

| Module | Imports (brain-internal only) |
|--------|-------------------------------|
| main | config, logging_setup, state, library, director, acquire, analyzer, enrich, talk, knowledge, research, server, website |
| director | config, acquire, library, llm, logging_setup |
| acquire | config, library, logging_setup, slskd, ytdlp |
| analyzer | config, library, state, logging_setup, analysis, metadata |
| enrich | config, metadata, logging_setup, library |
| research | config, library, knowledge, logging_setup |
| talk | config, library, logging_setup, llm, voice |
| server | config, library, logging_setup |
| library | config, logging_setup |
| slskd | config, logging_setup |
| metadata | config, logging_setup |
| voice | config, logging_setup |
| website | config |
| knowledge | logging_setup |
| llm | logging_setup |
| analysis | _(none)_ |
| ytdlp | logging_setup |
| state | _(none)_ |
| config | _(none)_ |
| logging_setup | _(none)_ |

---

## High Fan-In Hub Modules

| Module | Fan-In (imported by) | Role |
|--------|----------------------|------|
| `logging_setup` | 14 of 20 modules | Universal structured logging; true root leaf — no dependencies of its own |
| `config` | 11 of 20 modules | All subsystem configuration; only imports stdlib |
| `library` | 7 modules (director, acquire, analyzer, enrich, research, talk, server) | Central music index; writer bottleneck for scan+persist |
| `state` | 2 modules (main, analyzer); also read by server at runtime | Ground-truth now-playing and rotation state |

---

## Circular Dependency Analysis

**No circular dependencies detected.**

The import graph is a strict DAG:

- `config` and `logging_setup` are pure leaf nodes imported by everyone — they import nothing internal.
- `state` and `library` are second-tier leaves — they import only `config`/`logging_setup`.
- `director` imports `acquire` and `library`, but neither imports `director`.
- `acquire` imports `library`, but `library` does not import `acquire`.
- `talk` imports `llm` and `voice`, but neither imports `talk`.
- `main` imports everything but is imported by nothing.

The fan-out from `main` is deep but acyclic: `main → director → acquire → slskd` and `main → director → llm` have no back-edges.

---

## Go radiod Internal Dependencies

| Package | Imports (internal/) |
|---------|---------------------|
| main (cmd/radiod) | config, state, store, library, slskd, acquire, director, web |
| director | acquire, library, state |
| acquire | library, slskd, state, store |
| scheduler | library, playout, state |
| web | library, state |
| library | store |
| slskd | _(none)_ |
| state | _(none)_ |
| store | _(none)_ |
| playout | _(none)_ |
| config | _(none)_ |

No circular dependencies in the Go component. `scheduler` is dead code (not imported by main).
