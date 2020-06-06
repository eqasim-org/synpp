# Synthetic Population Pipeline (synpp)

[![Build Status](https://travis-ci.org/eqasim-org/synpp.svg?branch=develop)](https://travis-ci.org/eqasim-org/synpp)

The *synpp* module is a tool to chain different stages of a (population)
synthesis pipeline. This means that self-contained pieces of code can be
run, which are dependent on the outputs of other self-contained pieces
of code. Those pieces, or steps, are called *stages* in this module.

The following will describe the components of the pipeline and how it can
be set up and configured. Scroll to the bottom to find a full example of such
a pipeline which automatically downloads NYC taxi data sets, merges them together
and calculates the average vehicle occupancy during a predefined period.

## Installation

The `synpp` package releases can be installed via `pip`:

```sh
pip install synpp
```

Currently, version `1.2.2` is the active release version. Alternatively, you can
clone the `develop` branch of this repository to use the development version `1.2.2-dev`.
It can be installed by calling

```
pip install .
```

inside of the repository directoy.

## Concepts

A typical chain of stages could, for instance, be: **(C1)** load raw census data,
**(C2)** clean raw census data *(dependent on C1)*, **(H1)** load raw household travel survey data,
**(H2)** clean survey data *(dependent on C2)*, **(P1)** merge census *(C1)* and survey *(H2)* data,
**(P2)** generate a synthetic population from merged data *(P1)*.

In *synpp* each *stage* is defined by:

* A *descriptor*, which can be a Python module, a class or a class instance, or a string referencing a module or class.
* *Configuration options* that parameterize each *stage*.

The most common form of a *stage* is a Python module. A full stage would look
like this:

```python
def configure(context):
  pass

def execute(context):
  pass

def validate(context):
  pass
```

### Configuration and Parameterization

Whenever the pipeline explores a stage, *configure* is called first. Note that
in the example above we use a Python module, but the same procedure would work
analogously with a class. In *configure* one can the pipeline what the *stage*
expects in terms of other input *stages* and in terms of
*configuration options*:

```python
def configure(context):
  # Expect an output directory
  value = context.config("output_path")

  # Expect a random seed
  value = context.config("random_seed")

  # Expect a certain stage (no return value)
  context.stage("my.pipeline.raw_data")
```

We could add this stage (let's call it `my.pipeline.raw_data`)
as a dependency to another one. However, as we did not define a default
value with the `config` method, we need to explicitly set one, like so:

```python
def configure(context):
  context.stage("my.pipeline.raw_data", { "random_seed": 1234 })
```

Note that it is even possible to build recursive chains of stages using only
one stage definition:

```python
def configure(context):
  i = context.config("i")

  if i > 0:
    context.stage("this.stage", { "i": i - 1 })
```

Configuration options can also be defined globally in the pipeline. In case
no default value is given for an option in `configure` and in case that no
specific value is passed to the stage, a global configuration that is specific
to the pipeline will be used to look up the value.

### Execution

The requested configuration values and stages are afterwards available
to the `execute` step of a *stage*. There those values can be used to do the
"heavy work" of the stage. As the `configure` step already defined what kind
of values to expect, we can be sure that those values and dependencies are
present once `execute` is called.

```python
def execute(context):
  # Load some data from another stage
  df = context.stage("my.pipeline.census.raw")

  df = df.dropna()
  df["age"] = df["age"].astype(int)

  # We could access some values if we wanted
  value = context.config("...")

  return df
```

Note that the `execute` step returns a value. This value will be *pickled* (see
*pickle* package of Python) and cached on the hard drive. This means that whenever
the output of this stage is requested by another stage, it doesn't need to be
run again. The pipeline can simply load the cached result from hard drive.

If one has a very complex pipeline with many stages this means that changes in
one stage will likely not lead to a situation where one needs to re-run the
whole pipeline, but only a fraction. The *synpp* framework has intelligent
explorations algorithms included which figure out automatically, which
*stages* need to be re-run.

### Running a pipeline

A pipeline can be started using the `synpp.run` method. A typical run would
look like this:

```python
config = { "random_seed": 1234 }
working_directory = "~/pipeline/cache"

synpp.run([
    { "descriptor": "my.pipeline.final_population" },
    { "descriptor": "my.pipeline.paper_analysis", "config": { "font_size": 12 } }
], config = config, working_directory = working_directory)
```

Here we call the *stage* defined by the module `my.pipeline.final_population`
which should be available in the Python path. And we also want to run the
`my.pipeline.paper_analysis` path with a font size parameter of `12`. Note that
in both cases we could also have based the bare Python module objects instead
of strings.

The pipeline will now figure out how to run those *stages*. Probably they have
dependencies and the analysis *stage* may even depend on the other one. Therefore,
*synpp* explores the tree of dependencies as follows:

* Consider the requested stages (two in this case)
* Step by step, go through the dependencies of those stages
* Then again, go through the dependencies of all added stages, and so on

By that the pipeline traverses the whole tree of dependencies as they are defined
by the `configure` steps of all stages. At the same time it collects information
about which configuration options and parameters are required by each stage. Note
that a stage can occur twice in this dependency tree if it has different
parameters.

After constructing a tree of *stages*, *synpp* devalidates some of them according
to the following scheme. A *stage* is devalidated if ...

- ... it is requested by the `run` call
- ... it is new (no meta data from a previous call is present)
- ... if at least one of the requested configuration options has changed
- ... if at least one dependency has been re-run since the last run of the stage
- ... if list of dependencies has changed
- ... if manual *validation* of the stage has failed (see below)
- ... if any ascendant of a stage has been devalidated

This list of conditions makes sure that in almost any case of pipeline
modification we end up in a consistent situation (though we cannot prove it).
The only measure that may be important to enforce 'by convention' is to
*always run a stage after the code has been modified*. Though even this can
be automated.

### Validation

Each *stage* has an additional `validate` step, which also receives the
configuration options and the parameters. Its purpose is to return a hash
value that represents the environment of the *stage*. To learn about the concept
in general, search for "md5 hash", for instance. The idea is the following:
After the `execute` step, the `validate` step is called and
 it will return a certain value. Next time the pipeline
is resolved the `validate` step is called during devalidation, i.e. before
the stage is actually *executed*. If the return value of `validate` now differs
from what it was before, the stage will be devalidated.

This is useful to check the integrity of data that is not generated inside of
the pipeline but comes from the outside, for instance:

```python
def configure(context):
  context.config("input_path")

def validate(context):
  path = context.config("input_path")
  filesize = get_filesize(path)

  # If the file size has changed, the file must have changed,
  # hence we want to run the stage again.
  return filesize

def execute(context):
  pass # Do something with the file
```

### Cache paths

Sometimes, results of a *stage* are not easily representable in Python. Even
more, stages may call Java or Shell scripts which simply generate an output
file. For these cases each stage has its own *cache path*. It can be accessed
through the stage context:

```python
def execute(context):
  # In this case we write a file to the cache path of the current stage
  with open("%s/myfile.txt" % context.path()) as f:
    f.write("my content")

  # In this case we read a file from the cache path of another stage
  with open("%s/otherfile.txt" % context.path("my.other.stage")) as f:
    value = f.read()
```

As the example shows, we can also access cache paths of other stages. The pipeline
will make sure that you only have access to the cache path of stages that
have been defined as dependencies before. Note that the pipeline cannot enforce
that one stage is not corrupting the cache path of another stage. Therefore,
by convention, a stage should never *write* to the cache path of another stage.

### Parallel execution

The *synpp* package comes with some simplified ways of parallelizing code,
which are built on top of the `multiprocessing` package. To set up a parallel
routine, one can follow the following pattern:

```python
def run_parallel(context, x):
  return x**2 + context.data("y")

def execute(context):
  data = { "y": 5 }

  with context.parallel(data) as parallel:
    result = parallel.map(run_parallel, [1, 2, 3, 4, 5])
```

This approach looks similar to the `Pool` object of `multiprocessing` but has
some simplifications. First, the first argument of the parallel routine is a
context object, which provides configuration and parameters. Furthermore, it
provides data, which has been passed before in the `execute` function. This
simplifies passing data to all parallel threads considerably to the more
flexible approach in `multiprocessing`. Otherwise, the `parallel` object
provides most of the functionality of `Pool`, like, `map`, `async_map`,
`imap`, and `unordered_imap`.

### Info

While running the pipeline a lot of additional information may be interesting,
like how many samples of a data set have been discarded in a certain stage. However,
they often would only be used at the very end of the pipeline when maybe a paper,
a report or some explanatory graphics are generated. For that, the pipeline
provides the `set_info` method:

```python
def execute(context):
  # ...
  context.set_info("dropped_samples", number_of_dropped_samples)
  # ...
```

The information can later be retrieved from another stage (which has the
stage in question as a dependency):

```python
def execute(context):
  # ...
  value = context.get_info("my.other.stage", "dropped_samples")
  # ...
```

Note that the *info* functionality should only be used for light-weight
information like integers, short strings, etc.

### Progress

The *synpp* package provides functionality to show the progress of a stage
similar to `tqdm`. However, `tqdm` tends to spam the console output which is
especially undesired if pipelines have long runtimes and run, for instance, in
Continuous Integration environments. Therefore, *synpp* provides its own
functionality, although `tqdm` could still be used:

```python
def execute(context):
  # As a
  with context.progress(label = "My progress...", total = 100) as progress:
    i = 0

    while i < 100:
      progress.update()
      i += 1

  for i in context.progress(range(100)):
    pass
```

### Command-line tool

The `synpp` pipeline comes with a command line tool, which can be called like

```sh
python3 -m synpp [config_path]
```

If not config path is given, it will assume `config.yml`. This file should
contain everything to run a pipeline. A simple version would look like this:

```yaml
# General pipeline settings
working_directory: /path/to/my/working_directory

# Requested stages
run:
  - my_first_module.my_first_stage
  - my_first_parameterized_stage:
    param1: 123
    param2: 345

# These are configuration options that are used in the pipeline
config:
  my_option: 123
```

It receives the working directory, a list of stages (which may be parameterized)
and all configuration options. The stages listed above should be available
as Python modules or classes.

## NYC Taxi Example

This repository contains an example of the pipline. To run it, you will need
`pandas` as an additional Python dependency. For testing, you can clone this
repository to any directory on your machine. Inside the repository directory
you can find the `example` directory. If you did not install `synpp` yet,
you can do this by executing

```sh
pip install .
```

inside of the repository directory. Afterwards, open `examples/config.yml`
and adjust the `working_directory` path. This is a path that should exist on
your machine and it should be empty. The best is if you simply create a new
folder and add the path in `config.yml`.

You can now go to `examples` and call the pipeline code:

```sh
cd examples
python3 -m synpp
```

It will automatically discover `config.yml` (but you could path a different
config file path manually as a command line argument). It will then download
the NYC taxi data for January, February and March 2018 (see configuration
options in `config.yml`). Note that this is happening in one stage for which
you can find the code in `nyc_taxi.download`. It is parameterized by a month
and a year to download the respective data set. These data sets then go into
`nyc_taxi.aggregate`, where they are merged together. Finally, an average
occupancy value is printed out in `nyc_taxi.print_occupancy`. So the dependency
structure is as follows:

```
nyc_taxi.aggregate depends on multiple nyc_taxi.download(year, month)
nyc_taxi.print_occupancy depends on nyc_taxi.aggregate
```

After one successful run of the pipeline you can start it again. You will notice
that the pipeline does *not* download the data again, because nothing has changed
for those stages. However, if you would change the requested months in `config.yml`
the pipeline may download the additional data sets.
