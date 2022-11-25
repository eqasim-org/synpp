# CHANGELOG

**Under development**

- Fix: Gracefully close zmq Context and Socket at progress server close
- Add global stage aliases to provide drop-in replacement for existing stages
- Add *externals* support

**1.5.0**

- Information of which stages are requested in config now available in context,
which allows improved handling of optional stages
- Decorated stages improved and better documented

**1.4.0**

- Running functions as stages now possible with @synpp.stage decorator
- Added a wrapper class for interactive use, e.g. in Jupyter
- Devalidation less sensible for class-stages
- Added option to load required stages directly from cache without devalidating

**1.3.1**

- Bugfix: hashing of input files

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
