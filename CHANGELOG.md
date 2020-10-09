# CHANGELOG

**Under development**

- No changes yet

**1.3.0**

- Allow hierarchical configuration options
- Devalidate stages if code has changed

**1.2.2**

- Make deletion available for write-protected directories in Windows

**1.2.1**

- Make working directory absolute

**1.2.0**

- Change behaviour of ephemeral stages, use as much caching as possible
- Add option to serialize parallel contexts for profiling
- Increment pickle protocol to version 4
- Export pipeline flowchart as json
- Keep backup when writing pipeline.json
- Show overall progress of pipeline
- Add ephemeral stages
- Fix cycle detection with implicit chains
- Fix progress indicator for long iterations
- BC: Implicitly open new dependency chains with explicitly passed config values

**1.1.0**

- BC: Remove "parameter" functionality and unify "config" concept

**1.0.1**

- Add functionality for parallel progress
- Fix total value for progress
- Change default log level to INFO

**1.0.0**

- Setting up for Travis
