import copy
import datetime
import hashlib
import importlib
import inspect
import json
import logging
import os, stat, errno
import pickle
import shutil

import networkx as nx
import yaml
from networkx.readwrite.json_graph import node_link_data

from .general import PipelineError
from .parallel import ParallelMasterContext, ParalelMockMasterContext
from .progress import ProgressContext

# The following two functions extend shutil.rmtree, because by default it
# refuses to delete write-protected files on Windows. However, we often want
# to delete .git directories, which are protected.
def handle_rmtree_error(delegate, path, exec):
  if delegate in (os.rmdir, os.remove) and exec[1].errno == errno.EACCES:
      os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
      delegate(path)
  else:
      raise

def rmtree(path):
    return shutil.rmtree(path, ignore_errors = False, onerror = handle_rmtree_error)


class NoDefaultValue:
    pass


class StageInstance:
    def __init__(self, instance, name):
        self.instance = instance
        self.name = name

    def parameterize(self, parameters):
        return ParameterizedStage(self.instance, self.name)

    def configure(self, context):
        if hasattr(self.instance, "configure"):
            return self.instance.configure(context)

    def validate(self, context):
        if hasattr(self.instance, "validate"):
            return self.instance.validate(context)

        return None

    def execute(self, context):
        if hasattr(self.instance, "execute"):
            return self.instance.execute(context)
        else:
            raise RuntimeError("Stage %s does not have execute method" % self.name)


def resolve_stage(descriptor):
    if isinstance(descriptor, str):
        try:
            # Try to get the module referenced by the string
            descriptor = importlib.import_module(descriptor)
        except ModuleNotFoundError:
            # Not a module, but maybe a class?
            parts = descriptor.split(".")

            module = importlib.import_module(".".join(parts[:-1]))
            constructor = getattr(module, parts[-1])
            descriptor = constructor()

    if inspect.ismodule(descriptor):
        return StageInstance(descriptor, descriptor.__name__)

    if inspect.isclass(descriptor):
        return StageInstance(descriptor(), "%s.%s" % (descriptor.__module__, descriptor.__name__))

    clazz = descriptor.__class__
    return StageInstance(descriptor, "%s.%s" % (clazz.__module__, clazz.__name__))


def configure_stage(instance, context, config):
    config_values = {}

    for name, default_value in context.required_config.items():
        if name in config:
            config_values[name] = config[name]
        elif not type(default_value) == NoDefaultValue:
            config_values[name] = default_value
        else:
            raise PipelineError("Config option '%s' missing for stage '%s'" % (name, instance.name))

    return ConfiguredStage(instance, config, context)


def configure_name(name, config):
    values = ["%s=%s" % (name, value) for name, value in config.items()]
    return "%s(%s)" % (name, ",".join(values))


def hash_name(name, config):
    if len(config) > 0:
        hash = hashlib.md5()
        hash.update(json.dumps(config, sort_keys = True).encode("ascii"))
        return "%s__%s" % (name, hash.hexdigest())
    else:
        return name


class ConfiguredStage:
    def __init__(self, instance, config, configuration_context):
        self.instance = instance
        self.config = config
        self.configuration_context = configuration_context

        self.configured_name = configure_name(instance.name, configuration_context.required_config)
        self.hashed_name = hash_name(instance.name, configuration_context.required_config)

    def configure(self, context):
        return self.instance.configure(context)

    def execute(self, context):
        return self.instance.execute(context)

    def validate(self, context):
        return self.instance.validate(context)


class ConfigurationContext:
    def __init__(self, base_config):
        self.base_config = base_config

        self.required_config = {}

        self.required_stages = []
        self.aliases = {}

        self.ephemeral_mask = []

    def config(self, option, default = NoDefaultValue()):
        if option in self.base_config:
            self.required_config[option] = self.base_config[option]
        elif not isinstance(default, NoDefaultValue):
            if option in self.required_config and not self.required_config[option] == default:
                raise PipelineError("Got multiple default values for config option: %s" % option)

            self.required_config[option] = default

        if not option in self.required_config:
            raise PipelineError("Config option is not available: %s" % option)

        return self.required_config[option]

    def stage(self, descriptor, config = {}, alias = None, ephemeral = False):
        definition = {
            "descriptor": descriptor, "config": config
        }

        if not definition in self.required_stages:
            self.required_stages.append(definition)
            self.ephemeral_mask.append(ephemeral)

            if not alias is None:
                self.aliases[alias] = definition


class ValidateContext:
    def __init__(self, required_config, cache_path):
        self.required_config = required_config
        self.cache_path = cache_path

    def config(self, option):
        if not option in self.required_config:
            raise PipelineError("Config option %s is not requested" % option)

        return self.required_config[option]

    def path(self):
        return self.cache_path


class ExecuteContext:
    def __init__(self, required_config, required_stages, aliases, working_directory, dependencies, cache_path, pipeline_config, logger, cache, dependency_info):
        self.required_config = required_config
        self.working_directory = working_directory
        self.dependencies = dependencies
        self.pipeline_config = pipeline_config
        self.cache_path = cache_path
        self.logger = logger
        self.stage_info = {}
        self.dependency_cache = {}
        self.cache = cache
        self.dependency_info = dependency_info
        self.aliases = aliases
        self.required_stages = required_stages

        self.progress_context = None

    def config(self, option):
        if not option in self.required_config:
            raise PipelineError("Config option %s is not requested" % option)

        return self.required_config[option]

    def stage(self, name, config = {}):
        dependency = self._get_dependency({ "descriptor": name, "config": config })

        if self.working_directory is None:
            return self.cache[dependency]
        else:
            if not dependency in self.dependency_cache:
                with open("%s/%s.p" % (self.working_directory, dependency), "rb") as f:
                    self.logger.info("Loading cache for %s ..." % dependency)
                    self.dependency_cache[dependency] = pickle.load(f)

            return self.dependency_cache[dependency]

    def path(self, name = None, config = {}):
        if self.working_directory is None:
            raise PipelineError("Cache paths don't work if no working directory was specified")

        if name is None and len(config) == 0:
            return self.cache_path

        dependency = self._get_dependency({ "descriptor": name, "config": config })
        return "%s/%s.cache" % (self.working_directory, dependency)

    def set_info(self, name, value):
        self.stage_info[name] = value

    def get_info(self, stage, name, config = {}):
        dependency = self._get_dependency({ "descriptor": stage, "config": config })

        if not name in self.dependency_info[dependency]:
            raise PipelineError("No info '%s' available for %s" % (name, dependency))

        return self.dependency_info[dependency][name]

    def parallel(self, data = {}, processes = None, serialize = False):
        config = self.required_config

        if processes is None and "processes" in self.pipeline_config:
            processes = self.pipeline_config["processes"]

        if serialize:
            # Add mock context to run all parallel tasks in series and in
            # the same process. This can be useful for debugging and especially
            # for profiling the code.
            return ParalelMockMasterContext(data, config, self.progress_context)
        else:
            return ParallelMasterContext(data, config, processes, self.progress_context)

    def progress(self, iterable = None, label = None, total = None, minimum_interval = 1.0):
        if minimum_interval is None and "progress_interval" in self.pipeline_config:
            minimum_interval = self.pipeline_config["progress_interval"]

        self.progress_context = ProgressContext(iterable, total, label, self.logger, minimum_interval)
        return self.progress_context

    def _get_dependency(self, definition):
        if definition["descriptor"] in self.aliases:
            if len(definition["config"]) > 0:
                raise PipelineError("Cannot define parameters for aliased stage")

            definition = self.aliases[definition["descriptor"]]

        if not definition in self.required_stages:
            raise PipelineError("Stage '%s' with parameters %s is not requested" % (definition["descriptor"], definition["config"]))

        return self.dependencies[self.required_stages.index(definition)]


def process_stages(definitions, global_config):
    pending = copy.copy(definitions)
    stages = []

    for index, stage in enumerate(pending):
        stage["required-index"] = index

    while len(pending) > 0:
        definition = pending.pop(0)

        # Resolve the underlying code of the stage
        wrapper = resolve_stage(definition["descriptor"])

        # Call the configure method of the stage and obtain parameters
        config = copy.copy(global_config)

        if "config" in definition:
            config.update(definition["config"])

        # Obtain configuration information through configuration context
        context = ConfigurationContext(config)
        wrapper.configure(context)

        definition = copy.copy(definition)
        definition.update({
            "wrapper": wrapper,
            "config": copy.copy(context.required_config),
            "required_config": copy.copy(context.required_config),
            "required_stages": context.required_stages,
            "aliases": context.aliases
        })

        # Check for cycles
        cycle_hash = hash_name(definition["wrapper"].name, definition["config"])

        if "cycle_hashes" in definition and cycle_hash in definition["cycle_hashes"]:
            print(definition["cycle_hashes"])
            print(cycle_hash)
            raise PipelineError("Found cycle in dependencies: %s" % definition["wrapper"].name)

        # Everything fine, add it
        stages.append(definition)
        stage_index = len(stages) - 1

        # Process dependencies
        for position, upstream in enumerate(context.required_stages):
            passed_parameters = list(upstream["config"].keys())

            upstream_config = copy.copy(config)
            upstream_config.update(upstream["config"])

            cycle_hashes = copy.copy(definition["cycle_hashes"]) if "cycle_hashes" in definition else []
            cycle_hashes.append(cycle_hash)

            upstream = copy.copy(upstream)
            upstream.update({
                "config": upstream_config,
                "downstream-index": stage_index,
                "downstream-position": position,
                "downstream-length": len(context.required_stages),
                "downstream-passed-parameters": passed_parameters,
                "cycle_hashes": cycle_hashes,
                "ephemeral": context.ephemeral_mask[position] or ("ephemeral" in definition and definition["ephemeral"])
            })
            pending.append(upstream)

    # Now go backwards in the tree to find intermediate config requirements and set up dependencies
    downstream_indices = set([
        stage["downstream-index"]
        for stage in stages if "downstream-index" in stage
    ])

    source_indices = set(range(len(stages))) - downstream_indices

    # Connect downstream stages with upstream stages via dependency field
    pending = list(source_indices)

    while len(pending) > 0:
        stage_index = pending.pop(0)
        stage = stages[stage_index]

        if "downstream-index" in stage:
            downstream = stages[stage["downstream-index"]]

            # Connect this stage with the downstream stage
            if not "dependencies" in downstream:
                downstream["dependencies"] = [None] * stage["downstream-length"]

            downstream["dependencies"][stage["downstream-position"]] = stage_index

            pending.append(stage["downstream-index"])

    # Update configuration requirements based dependencies
    pending = list(source_indices)

    while len(pending) > 0:
        stage_index = pending.pop(0)
        stage = stages[stage_index]

        if "dependencies" in stage:
            passed_config_options = {}

            for upstream_index in stage["dependencies"]:
                upstream = stages[upstream_index]

                upstream_config_keys = upstream["config"].keys()
                explicit_config_keys = upstream["downstream-passed-parameters"] if "downstream-passed-parameters" in upstream else set()

                for key in upstream_config_keys - explicit_config_keys:
                    value = upstream["config"][key]

                    if key in passed_config_options:
                        assert passed_config_options[key] == value
                    else:
                        passed_config_options[key] = value

            for key, value in passed_config_options.items():
                if key in stage["config"]:
                    assert stage["config"][key] == value
                else:
                    stage["config"][key] = value

        if "downstream-index" in stage:
            pending.append(stage["downstream-index"])

    # Hash all stages
    required_hashes = {}

    for stage in stages:
        stage["hash"] = hash_name(stage["wrapper"].name, stage["config"])

        if "required-index" in stage:
            index = stage["required-index"]

            if stage["hash"] in required_hashes:
                assert required_hashes[stage["hash"]] == index
            else:
                required_hashes[stage["hash"]] = index

    # Reset ephemeral stages
    ephemeral_hashes = set([stage["hash"] for stage in stages]) - set([stage["hash"] for stage in stages if not "ephemeral" in stage or not stage["ephemeral"]])
    for stage in stages: stage["ephemeral"] = stage["hash"] in ephemeral_hashes

    # Collapse stages again by hash
    registry = {}

    for stage in stages:
        registry[stage["hash"]] = stage

        stage["dependencies"] = [
            stages[index]["hash"] for index in stage["dependencies"]
        ] if "dependencies" in stage else []

    for hash in required_hashes:
        registry[hash]["required-index"] = required_hashes[hash]

    return registry


def update_json(meta, working_directory):
    if os.path.exists("%s/pipeline.json" % working_directory):
        shutil.move("%s/pipeline.json" % working_directory, "%s/pipeline.json.bk" % working_directory)

    with open("%s/pipeline.json.new" % working_directory, "w+") as f:
        json.dump(meta, f)

    shutil.move("%s/pipeline.json.new" % working_directory, "%s/pipeline.json" % working_directory)


def run(definitions, config = {}, working_directory = None, flowchart_path = None, dryrun = False, verbose = False, logger = logging.getLogger("synpp")):
    # 0) Construct pipeline config
    pipeline_config = {}
    if "processes" in config: pipeline_config["processes"] = config["processes"]
    if "progress_interval" in config: pipeline_config["progress_interval"] = config["progress_interval"]

    if not working_directory is None:
        if not os.path.isdir(working_directory):
            raise PipelineError("Working directory does not exist: %s" % working_directory)

        working_directory = os.path.realpath(working_directory)

    # 1) Construct stage registry
    registry = process_stages(definitions, config)

    required_hashes = [None] * len(definitions)
    for stage in registry.values():
        if "required-index" in stage:
            required_hashes[stage["required-index"]] = stage["hash"]

    logger.info("Found %d stages" % len(registry))

    # 2) Order stages
    graph = nx.DiGraph()
    flowchart = nx.MultiDiGraph() # graph to later plot

    for hash in registry.keys():
        graph.add_node(hash)

    for stage in registry.values():
        stage_name = stage['descriptor']

        if not flowchart.has_node(stage_name):
            flowchart.add_node(stage_name)

        for hash in stage["dependencies"]:
            graph.add_edge(hash, stage["hash"])

            dependency_name = registry.get(hash)['descriptor']
            if not flowchart.has_edge(dependency_name, stage_name):
                flowchart.add_edge(dependency_name, stage_name)

    # Write out flowchart
    if not flowchart_path is None:
        flowchart_directory = os.path.dirname(os.path.abspath(flowchart_path))
        if not os.path.isdir(flowchart_directory):
            raise PipelineError("Flowchart directory does not exist: %s" % flowchart_directory)

        logger.info("Writing pipeline flowchart to : {}".format(flowchart_path))
        with open(flowchart_path, 'w') as outfile:
            json.dump(node_link_data(flowchart), outfile)

    if dryrun:
        return node_link_data(flowchart)

    for cycle in nx.cycles.simple_cycles(graph):
        cycle = [registry[hash]["hash"] for hash in cycle] # TODO: Make more verbose
        raise PipelineError("Found cycle: %s" % " -> ".join(cycle))

    sorted_hashes = list(nx.topological_sort(graph))

    # Check where cache is available
    cache_available = set()

    if not working_directory is None:
        for hash in sorted_hashes:
            directory_path = "%s/%s.cache" % (working_directory, hash)
            file_path = "%s/%s.p" % (working_directory, hash)

            if os.path.exists(directory_path) and os.path.exists(file_path):
                cache_available.add(hash)
                registry[hash]["ephemeral"] = False

    # Set up ephemeral stage counts
    ephemeral_counts = {}

    for stage in registry.values():
        for hash in stage["dependencies"]:
            dependency = registry[hash]

            if dependency["ephemeral"] and not hash in cache_available:
                if not hash in ephemeral_counts:
                    ephemeral_counts[hash] = 0

                ephemeral_counts[hash] += 1

    # 3) Load information about stages
    meta = {}

    if not working_directory is None:
        try:
            with open("%s/pipeline.json" % working_directory) as f:
                meta = json.load(f)
                logger.info("Found pipeline metadata in %s/pipeline.json" % working_directory)
        except FileNotFoundError:
            logger.info("Did not find pipeline metadata in %s/pipeline.json" % working_directory)

    # 4) Devalidate stages
    sorted_cached_hashes = sorted_hashes - ephemeral_counts.keys()

    # 4.1) Devalidate if they are required
    stale_hashes = set(required_hashes)

    # 4.2) Devalidate if not in meta
    for hash in sorted_cached_hashes:
        if not hash in meta:
            stale_hashes.add(hash)

    # 4.3) Devalidate if configuration values have changed
    # This devalidation step is obsolete since we have implicit config parameters

    # 4.3) Devalidate if cache is not existant
    if not working_directory is None:
        for hash in sorted_cached_hashes:
            directory_path = "%s/%s.cache" % (working_directory, hash)
            file_path = "%s/%s.p" % (working_directory, hash)

            if not hash in cache_available:
                stale_hashes.add(hash)

    # 4.4) Devalidate if parent has been updated
    for hash in sorted_cached_hashes:
        if not hash in stale_hashes and hash in meta:
            for dependency_hash, dependency_update in meta[hash]["dependencies"].items():
                if not dependency_hash in meta:
                    stale_hashes.add(hash)
                else:
                    if meta[dependency_hash]["updated"] > dependency_update:
                        stale_hashes.add(hash)

    # 4.5) Devalidate if parents are not the same anymore
    for hash in sorted_cached_hashes:
        if not hash in stale_hashes and hash in meta:
            cached_hashes = set(meta[hash]["dependencies"].keys())
            current_hashes = set(registry[hash]["dependencies"] if "dependencies" in registry[hash] else [])

            if not cached_hashes == current_hashes:
                stale_hashes.add(hash)

    # 4.6) Manually devalidate stages
    for hash in sorted_cached_hashes:
        stage = registry[hash]
        cache_path = "%s/%s.cache" % (working_directory, hash)
        context = ValidateContext(stage["config"], cache_path)

        validation_token = stage["wrapper"].validate(context)
        existing_token = meta[hash]["validation_token"] if hash in meta and "validation_token" in meta[hash] else None

        if not validation_token == existing_token:
            stale_hashes.add(hash)

    # 4.7) Devalidate descendants of devalidated stages
    for hash in set(stale_hashes):
        for descendant_hash in nx.descendants(graph, hash):
            if not descendant_hash in stale_hashes:
                stale_hashes.add(descendant_hash)

    # 4.8) Devalidate ephemeral stages if necessary
    pending = set(stale_hashes)

    while len(pending) > 0:
        for dependency_hash in registry[pending.pop()]["dependencies"]:
            if registry[dependency_hash]["ephemeral"]:
                if not dependency_hash in stale_hashes:
                    pending.add(dependency_hash)

                stale_hashes.add(dependency_hash)

    logger.info("Devalidating %d stages:" % len(stale_hashes))
    for hash in stale_hashes: logger.info("- %s" % hash)

    # 5) Reset meta information
    for hash in stale_hashes:
        if hash in meta:
            del meta[hash]

    if not working_directory is None:
        update_json(meta, working_directory)

    logger.info("Successfully reset meta data")

    # 6) Execute stages
    results = [None] * len(definitions)
    cache = {}

    progress = 0

    for hash in sorted_hashes:
        if hash in stale_hashes:
            logger.info("Executing stage %s ..." % hash)
            stage = registry[hash]

            # Load the dependencies, either from cache or from file
            #stage_dependencies = []
            #stage_dependency_info = {}

            #if name in dependencies:
            #    stage_dependencies = dependencies[name]
            #
            #    for parent in stage_dependencies:
            #        stage_dependency_info[parent] = meta[parent]["info"]
            #stage_dependencies =

            stage_dependency_info = {}
            for dependency_hash in stage["dependencies"]:
                stage_dependency_info[dependency_hash] = meta[dependency_hash]["info"]

            # Prepare cache path
            cache_path = "%s/%s.cache" % (working_directory, hash)

            if not working_directory is None:
                if os.path.exists(cache_path):
                    rmtree(cache_path)
                os.mkdir(cache_path)

            context = ExecuteContext(stage["config"], stage["required_stages"], stage["aliases"], working_directory, stage["dependencies"], cache_path, pipeline_config, logger, cache, stage_dependency_info)
            result = stage["wrapper"].execute(context)
            validation_token = stage["wrapper"].validate(ValidateContext(stage["config"], cache_path))

            if hash in required_hashes:
                results[required_hashes.index(hash)] = result

            if working_directory is None:
                cache[hash] = result
            else:
                with open("%s/%s.p" % (working_directory, hash), "wb+") as f:
                    logger.info("Writing cache for %s" % hash)
                    pickle.dump(result, f, protocol=4)

            # Update meta information
            meta[hash] = {
                "config": stage["config"],
                "updated": datetime.datetime.utcnow().timestamp(),
                "dependencies": {
                    dependency_hash: meta[dependency_hash]["updated"] for dependency_hash in stage["dependencies"]
                },
                "info": context.stage_info,
                "validation_token": validation_token
            }

            if not working_directory is None:
                update_json(meta, working_directory)

            # Clear cache for ephemeral stages if they are no longer needed
            if not working_directory is None:
                for dependency_hash in stage["dependencies"]:
                    if dependency_hash in ephemeral_counts:
                        ephemeral_counts[dependency_hash] -= 1

                        if ephemeral_counts[dependency_hash] == 0:
                            cache_directory_path = "%s/%s.cache" % (working_directory, dependency_hash)
                            cache_file_path = "%s/%s.p" % (working_directory, dependency_hash)

                            rmtree(cache_directory_path)
                            os.remove(cache_file_path)

                            logger.info("Removed ephemeral %s." % dependency_hash)
                            del ephemeral_counts[dependency_hash]

            logger.info("Finished running %s." % hash)

            progress += 1
            logger.info("Pipeline progress: %d/%d (%.2f%%)" % (
                progress, len(stale_hashes), 100 * progress / len(stale_hashes)
            ))

    if verbose:
        info = {}

        for hash in sorted(meta.keys()):
            info.update(meta[hash]["info"])

        return {
            "results": results,
            "stale": stale_hashes,
            "info": info,
            "flowchart": node_link_data(flowchart)
        }
    else:
        return results


def run_from_yaml(path):
    with open(path) as f:
        settings = yaml.load(f, Loader = yaml.SafeLoader)

    definitions = []

    for item in settings["run"]:
        parameters = {}

        if type(item) == dict:
            key = list(item.keys())[0]
            parameters = item[key]
            item = key

        definitions.append({
            "descriptor": item, "parameters": parameters
        })

    config = settings["config"] if "config" in settings else {}
    working_directory = settings["working_directory"] if "working_directory" in settings else None
    flowchart_path = settings["flowchart_path"] if "flowchart_path" in settings else None
    dryrun = settings["dryrun"] if "dryrun" in settings else False

    run(definitions=definitions, config=config, working_directory=working_directory, flowchart_path=flowchart_path, dryrun=dryrun)
