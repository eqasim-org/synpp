import copy
import datetime
import hashlib
import importlib
import importlib.util
import inspect
import functools
import json
import logging
import os, stat, errno, sys
import pickle
import shutil
from typing import Dict, List, Union, Callable
from types import ModuleType
from collections.abc import MutableMapping

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

def flatten(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = str(parent_key) + sep + str(k) if parent_key else str(k)
        if isinstance(v, MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return copy.deepcopy(dict(items))

def unflatten(flatten, sep='.'):
    out = {}
    for key, value in flatten.items():
        parts = key.split(sep)
        d = out
        for part in parts[:-1]:
            if part.isdigit():
                part = int(part)
            if part not in d:
                d[part] = {}
            d = d[part]
        d[parts[-1]] = value
    return copy.deepcopy(out)

class NoDefaultValue:
    pass


class StageInstance:
    def __init__(self, instance, name, module_hash):
        self.instance = instance
        self.name = name
        self.module_hash = module_hash
        if not hasattr(self.instance, "execute"):
            raise RuntimeError("Stage %s does not have execute method" % self.name)

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
        return self.instance.execute(context)


def get_stage_hash(descriptor):
    source = inspect.getsource(descriptor)
    hash = hashlib.md5()
    hash.update(source.encode("utf-8"))
    return hash.hexdigest()

def synpp_import_module(name, package=None, externals={}):

    absolute_name = importlib.util.resolve_name(name, package)
    try:
        return sys.modules[absolute_name]
    except KeyError:
        pass

    if absolute_name in externals:
        spec = importlib.util.spec_from_file_location(absolute_name, externals[absolute_name])
    else:
        spec = importlib.util.find_spec(absolute_name)
        if spec is None:
            msg = f'No module named {absolute_name!r}'
            raise ModuleNotFoundError(msg, name=absolute_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[absolute_name] = module
    spec.loader.exec_module(module)
    return module


def resolve_stage(descriptor, externals: dict = {}, aliases: dict = {}):
    if descriptor in aliases:
        descriptor = aliases[descriptor]

    # Supported descriptors: module, class, @stage-decorated function or stage-looking object
    if isinstance(descriptor, str):
        # If a string, first try to get the actual object
        try:
            descriptor = synpp_import_module(descriptor, externals=externals)
        except ModuleNotFoundError:
            try:
                parts = descriptor.split(".")
                module = synpp_import_module(".".join(parts[:-1]), externals=externals)
                descriptor = getattr(module, parts[-1])
            except (ValueError, ModuleNotFoundError):
                return None  # definitely not a stage

    if inspect.ismodule(descriptor):
        stage_hash = get_stage_hash(descriptor)
        return StageInstance(descriptor, descriptor.__name__, stage_hash)

    if inspect.isclass(descriptor):
        stage_hash = get_stage_hash(descriptor)
        return StageInstance(descriptor(), "%s.%s" % (descriptor.__module__, descriptor.__name__), stage_hash)

    if inspect.isfunction(descriptor):
        if not hasattr(descriptor, 'stage_params'):
            raise PipelineError("Functions need to be decorated with @synpp.stage in order to be used in the pipeline.")
        function_stage = DecoratedStage(execute_func=descriptor, stage_params=descriptor.stage_params)
        stage_hash = get_stage_hash(descriptor)
        return StageInstance(function_stage, "%s.%s" % (descriptor.__module__, descriptor.__name__), stage_hash)

    if hasattr(descriptor, 'execute'):
        # Last option: arbitrary object which looks like a stage
        clazz = descriptor.__class__
        stage_hash = get_stage_hash(clazz)
        return StageInstance(descriptor, "%s.%s" % (clazz.__module__, clazz.__name__), stage_hash)

    # couldn't resolve stage (this is something else)
    return None

def get_config_path(name, config):
    if name in config:
        return name

def has_config_value(name, config):
    splitted_req = name.split(".")
    for key in flatten(config):
        found = True
        spltted_key = key.split(".")
        for idx in range(len(splitted_req)):
            if splitted_req[idx] != spltted_key[idx]:
                found = False
                break
        if found:
            return True
    return False


def get_config_value(name, config):
    flat = flatten(config)
    if name in flat:
        return flat[name]

    splitted_req = name.split(".")
    values = []
    keys = []
    for key in flat:
        found = True
        splitted_key = key.split(".")
        for idx in range(len(splitted_req)):
            if splitted_req[idx] != splitted_key[idx]:
                found = False
                break
        if found:
            keys.append(".".join(splitted_key[len(splitted_req):]))
            values.append(flat[key])
    return unflatten(dict(zip(keys, values)))

def configure_stage(instance, context, config):
    config_values = {}

    for name, default_value in context.required_config.items():
        if name in has_config_value(name, config):
            config_values[name] = get_config_value(name, config)
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
        hash.update(json.dumps(config, sort_keys = True).encode("utf-8"))
        return "%s__%s" % (name, hash.hexdigest())
    else:
        return name

def get_cache_prefix(stage_id, source_code):
    cache_prefix = stage_id + "__" + hashlib.md5(source_code.encode()).hexdigest()
    return cache_prefix

def get_cache_directory_path(working_directory, cache_id):
    return "%s/%s.cache" % (working_directory, cache_id)

def get_cache_file_path(working_directory, cache_id):
    return "%s/%s.p" % (working_directory, cache_id)

def get_info_path(working_directory, cache_id):
    return "%s/%s.info" % (working_directory, cache_id)

class ConfiguredStage:
    def __init__(self, instance, config, configuration_context):
        self.instance = instance
        self.config = config
        self.configuration_context = configuration_context

        self.configured_name = configure_name(instance.name, configuration_context.required_config)
        self.hashed_name = hash_name(instance.name, configuration_context.required_config)

    def configure(self, context):
        if hasattr(self.instance, "configure"):
            return self.instance.configure(context)

    def execute(self, context):
        return self.instance.execute(context)

    def validate(self, context):
        return self.instance.validate(context)


class Context:
    pass


class ConfigurationContext(Context):
    def __init__(self, base_config, config_definitions=[], externals={}, global_aliases={}):
        self.base_config = base_config
        self.config_requested_stages = [resolve_stage(d, externals, global_aliases).instance for d in config_definitions]

        self.required_config = {}

        self.required_stages = []
        self.aliases = {}

        self.ephemeral_mask = []

        self.externals = externals
        self.global_aliases = global_aliases

    def config(self, option, default = NoDefaultValue()):
        if has_config_value(option, self.base_config):
            self.required_config[option] = get_config_value(option, self.base_config)
        elif not isinstance(default, NoDefaultValue):
            if option in self.required_config and not self.required_config[option] == default:
                raise PipelineError("Got multiple default values for config option: %s" % option)

            self.required_config[option] = default

        if not option in self.required_config:
            raise PipelineError("Config option is not available: %s" % option)

        return self.required_config[option]

    def stage(self, descriptor, config = {}, alias = None, ephemeral = False):
        definition = {
            "descriptor": descriptor, "config": flatten(config)
        }

        if not definition in self.required_stages:
            self.required_stages.append(definition)
            self.ephemeral_mask.append(ephemeral)

            if not alias is None:
                self.aliases[alias] = definition

    def stage_is_config_requested(self, descriptor):
        if self.config_requested_stages:
            return resolve_stage(descriptor, self.externals, self.global_aliases).instance in self.config_requested_stages
        else:
            return False


class ValidateContext(Context):
    def __init__(self, required_config, cache_path):
        self.required_config = required_config
        self.cache_path = cache_path

    def config(self, option):
        if not option in self.required_config:
            raise PipelineError("Config option %s is not requested" % option)

        return self.required_config[option]

    def path(self):
        return self.cache_path


class ExecuteContext(Context):
    def __init__(self, required_config, required_stages, aliases, working_directory, dependencies, cache_path, pipeline_config, logger, cache, dependency_info, cache_ids):
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
        self.cache_ids = cache_ids

        self.progress_context = None

    def config(self, option):
        if not has_config_value(option, self.required_config):
            raise PipelineError("Config option %s is not requested" % option)

        return get_config_value(option, self.required_config)

    def stage(self, name, config = {}):
        dependency = self._get_dependency({ "descriptor": name, "config": config })

        if self.working_directory is None:
            return self.cache[dependency]
        else:
            if not dependency in self.dependency_cache:
                with open(get_cache_file_path(self.working_directory, self.cache_ids[dependency]), "rb") as f:
                    self.logger.info("Loading cache for %s ..." % dependency)
                    self.dependency_cache[dependency] = pickle.load(f)

            return self.dependency_cache[dependency]

    def path(self, name = None, config = {}):
        if self.working_directory is None:
            raise PipelineError("Cache paths don't work if no working directory was specified")

        if name is None and len(config) == 0:
            return self.cache_path

        dependency = self._get_dependency({ "descriptor": name, "config": config })
        return get_cache_directory_path(self.working_directory, self.cache_ids[dependency])

    def set_info(self, name, value):
        self.stage_info[name] = value

    def get_info(self, stage, name, config = {}):
        dependency = self._get_dependency({ "descriptor": stage, "config": config })

        if not name in self.dependency_info[dependency]:
            raise PipelineError("No info '%s' available for %s" % (name, dependency))

        return self.dependency_info[dependency][name]

    def parallel(self, data = {}, processes = None, serialize = False, maxtasksperchild = None):
        config = self.required_config

        if processes is None and "processes" in self.pipeline_config:
            processes = self.pipeline_config["processes"]

        if serialize:
            # Add mock context to run all parallel tasks in series and in
            # the same process. This can be useful for debugging and especially
            # for profiling the code.
            return ParalelMockMasterContext(data, config, self.progress_context)
        else:
            return ParallelMasterContext(data, config, processes, self.progress_context, maxtasksperchild)

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


def process_stages(definitions, global_config, externals={}, aliases={}):
    pending = copy.copy(definitions)
    stages = []

    for index, stage in enumerate(pending):
        stage["required-index"] = index

    global_config = flatten(global_config)

    while len(pending) > 0:
        definition = pending.pop(0)

        # Resolve the underlying code of the stage
        wrapper = resolve_stage(definition["descriptor"], externals, aliases)
        if wrapper is None:
            raise PipelineError(f"{definition['descriptor']} is not a supported object for pipeline stage definition!")

        # Call the configure method of the stage and obtain parameters
        config = copy.copy(global_config)

        if "config" in definition:
            config.update(definition["config"])

        # Obtain configuration information through configuration context
        context = ConfigurationContext(config, [d['descriptor'] for d in definitions], externals)
        wrapper.configure(context)
        required_config = flatten(context.required_config)
        definition = copy.copy(definition)
        definition.update({
            "wrapper": wrapper,
            "config": copy.copy(required_config),
            "required_config": copy.copy(required_config),
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
            passed_parameters = set(flatten(upstream["config"]).keys())

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
                explicit_config_keys = upstream["downstream-passed-parameters"] if "downstream-passed-parameters" in upstream else set()

                for key in upstream["config"].keys() - explicit_config_keys:
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


def run(definitions, config = {}, working_directory = None, flowchart_path = None, dryrun = False, verbose = False,
        logger = logging.getLogger("synpp"), rerun_required=True, ensure_working_directory=False,
        externals = {}, aliases = {}):
    # 0) Construct pipeline config
    pipeline_config = {}
    if "processes" in config: pipeline_config["processes"] = config["processes"]
    if "progress_interval" in config: pipeline_config["progress_interval"] = config["progress_interval"]

    if ensure_working_directory and working_directory is None:
        working_directory = '.synpp_cache'
    if working_directory is not None:
        if not os.path.isdir(working_directory) and ensure_working_directory:
            logger.warning("Working directory does not exist, it will be created: %s" % working_directory)
            os.mkdir(working_directory)

        working_directory = os.path.realpath(working_directory)

    # 1) Construct stage registry
    registry = process_stages(definitions, config, externals, aliases)

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

    # Concatenate source digest of dependencies
    source_digests = {}
    for hash in sorted_hashes:
        source_digests[hash] = ""
        for dependency_hash in sorted(nx.ancestors(graph, hash)):
            source_digests[hash] += registry[dependency_hash]["wrapper"].module_hash
        source_digests[hash] += registry[hash]["wrapper"].module_hash

    # Check where cache is available
    cache_available = {}

    if not working_directory is None:
        for hash in sorted_hashes:
            prefix = get_cache_prefix(hash, source_digests[hash])
            prefixed = [filename[:-2] for filename in os.listdir(working_directory) if filename.startswith(prefix) and filename.endswith(".p")]

            if prefixed:
                cache_available[hash] = [filename.split("__")[-1] for filename in prefixed]
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

    # 4) Devalidate stages
    sorted_cached_hashes = sorted_hashes - ephemeral_counts.keys()
    stale_hashes = set()

    # Get current validation tokens
    current_validation_tokens = {
        stage_id:
        str(
            registry[stage_id]["wrapper"].validate(
                ValidateContext(registry[stage_id]["config"], get_cache_directory_path(working_directory, stage_id))
            )
        ) for stage_id in sorted_hashes
    }

    # Cache mapper between stage id and cache id.
    cache_ids = {stage_id: get_cache_prefix(stage_id, source_digests[stage_id]) + "__" + str(current_validation_tokens[stage_id]) for stage_id in sorted_hashes}
    file_cache_paths = {stage_id: get_cache_file_path(working_directory, cache_id) for stage_id, cache_id in cache_ids.items()}
    dir_cache_paths = {stage_id: get_cache_directory_path(working_directory, cache_id) for stage_id, cache_id in cache_ids.items()}

    # 4.1) Devalidate if they are required (optional, otherwise will reload from cache)
    if rerun_required:
        stale_hashes.update(required_hashes)

    if working_directory is None:
        # If no working_directory, devalidate all dependencies
        for hash in list(stale_hashes):
            for dependency_hash in nx.ancestors(graph, hash):
                stale_hashes.add(dependency_hash)

    else:
        # 4.5) Devalidate if cache is not existant
        for hash in sorted_cached_hashes:
            if not hash in cache_available:
                stale_hashes.add(hash)

        # 4.8) Manually devalidate stages
        for hash in sorted_cached_hashes:
            if hash in cache_available and current_validation_tokens[hash] not in cache_available[hash]:
                stale_hashes.add(hash)

        # 4.6) Devalidate if parent has been updated
        for hash in sorted_cached_hashes:
            if not hash in stale_hashes:
                ctime = os.stat(file_cache_paths[hash]).st_mtime_ns
                for dependency_hash in nx.ancestors(graph, hash):
                    if dependency_hash not in stale_hashes and dependency_hash in cache_available:
                        dependency_ctime = os.stat(file_cache_paths[dependency_hash]).st_mtime_ns
                        if dependency_ctime > ctime:
                            stale_hashes.add(hash)
                            break

        # 4.9) Devalidate descendants of devalidated stages
        for hash in set(stale_hashes):
            for descendant_hash in nx.descendants(graph, hash):
                if not descendant_hash in stale_hashes:
                    stale_hashes.add(descendant_hash)

        # 4.10) Devalidate ephemeral stages if necessary
        pending = set(stale_hashes)

        while len(pending) > 0:
            for dependency_hash in registry[pending.pop()]["dependencies"]:
                if registry[dependency_hash]["ephemeral"]:
                    if not dependency_hash in stale_hashes:
                        pending.add(dependency_hash)

                    stale_hashes.add(dependency_hash)

    logger.info("Devalidating %d stages:" % len(stale_hashes))
    for hash in stale_hashes: logger.info("- %s" % hash)

    # 6) Execute stages
    results = [None] * len(definitions)
    cache = {}

    progress = 0

    infos = {}
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

            for dependency_hash in stage["dependencies"]:
                if dependency_hash not in infos and working_directory is not None:
                    with open(get_info_path(working_directory, cache_ids[dependency_hash]), "rb") as f:
                        infos[dependency_hash] = pickle.load(f)

            # Prepare cache path
            cache_path = dir_cache_paths[hash]

            if not working_directory is None:
                if os.path.exists(cache_path):
                    rmtree(cache_path)
                os.mkdir(cache_path)

            context = ExecuteContext(stage["config"], stage["required_stages"], stage["aliases"], working_directory, stage["dependencies"], cache_path, pipeline_config, logger, cache, infos, cache_ids)
            result = stage["wrapper"].execute(context)

            if hash in required_hashes:
                results[required_hashes.index(hash)] = result

            if working_directory is None:
                cache[hash] = result
            else:
                with open(file_cache_paths[hash], "wb+") as f:
                    logger.info("Writing cache for %s" % hash)
                    pickle.dump(result, f, protocol=4)
                with open(get_info_path(working_directory, cache_ids[hash]), "wb+") as f:
                    logger.info("Writing info for %s" % hash)
                    pickle.dump(context.stage_info, f, protocol=4)
            infos[hash] = context.stage_info

            # Clear cache for ephemeral stages if they are no longer needed
            if not working_directory is None:
                for dependency_hash in stage["dependencies"]:
                    if dependency_hash in ephemeral_counts:
                        ephemeral_counts[dependency_hash] -= 1

                        if ephemeral_counts[dependency_hash] == 0:
                            cache_directory_path = dir_cache_paths[dependency_hash]
                            cache_file_path = file_cache_paths[dependency_hash]

                            rmtree(cache_directory_path)
                            os.remove(cache_file_path)

                            logger.info("Removed ephemeral %s." % dependency_hash)
                            del ephemeral_counts[dependency_hash]

            logger.info("Finished running %s." % hash)

            progress += 1
            logger.info("Pipeline progress: %d/%d (%.2f%%)" % (
                progress, len(stale_hashes), 100 * progress / len(stale_hashes)
            ))

    if not rerun_required:
        # Load remaining previously cached results
        for hash in required_hashes:
            if results[required_hashes.index(hash)] is None:
                with open(file_cache_paths[hash], "rb") as f:
                    logger.info("Loading cache for %s ..." % hash)
                    results[required_hashes.index(hash)] = pickle.load(f)

    if verbose:
        info = {}

        for hash in infos.keys():
            info.update(infos[hash])

        return {
            "results": results,
            "stale": stale_hashes,
            "info": info,
            "flowchart": node_link_data(flowchart)
        }
    else:
        return results


def run_from_yaml(path):
    Synpp.build_from_yml(path).run_pipeline()


# Convenience class mostly for running stages individually (possibly interactively, e.g. in Jupyter)
class Synpp:
    def __init__(self, config: dict, working_directory: str = None, logger: logging.Logger = logging.getLogger("synpp"),
                 definitions: List[Dict[str, Union[str, Callable, ModuleType]]] = None, flowchart_path: str = None,
                 dryrun: bool = False, externals: Dict[str, str] = {}, aliases = {}):
        self.config = config
        self.working_directory = working_directory
        self.logger = logger
        self.definitions = definitions
        self.flowchart_path = flowchart_path
        self.dryrun = dryrun
        self.externals = externals
        self.aliases = aliases

    def run_pipeline(self, definitions=None, rerun_required=True, dryrun=None, verbose=False, flowchart_path=None):
        if definitions is None and self.definitions is None:
            raise PipelineError("A list of stage definitions must be available in object or provided explicitly.")
        elif definitions is None:
            definitions = self.definitions
        if dryrun is None:
            dryrun = self.dryrun
        return run(definitions, self.config, self.working_directory, flowchart_path=flowchart_path,
                   dryrun=dryrun, verbose=verbose, logger=self.logger, rerun_required=rerun_required,
                   ensure_working_directory=True, externals=self.externals, aliases=self.aliases)

    def run_single(self, descriptor, config={}, rerun_if_cached=False, dryrun=False, verbose=False):
        return run([{'descriptor': descriptor, 'config': config}], self.config, self.working_directory,
                   dryrun=dryrun, verbose=verbose, logger=self.logger, rerun_required=rerun_if_cached,
                   flowchart_path=self.flowchart_path, ensure_working_directory=True, externals=self.externals,
                   aliases=self.aliases)[0]

    @staticmethod
    def build_from_yml(config_path):
        with open(config_path) as f:
            settings = yaml.load(f, Loader=yaml.SafeLoader)

        definitions = []

        for item in settings["run"]:
            parameters = {}

            if type(item) == dict:
                key = list(item.keys())[0]
                parameters = item[key]
                item = key

            definitions.append({
                "descriptor": item, "config": parameters
            })

        config = settings["config"] if "config" in settings else {}
        working_directory = settings["working_directory"] if "working_directory" in settings else None
        flowchart_path = settings["flowchart_path"] if "flowchart_path" in settings else None
        dryrun = settings["dryrun"] if "dryrun" in settings else False
        externals = settings["externals"] if "externals" in settings else {}
        aliases = settings["aliases"] if "aliases" in settings else {}

        return Synpp(config=config, working_directory=working_directory, definitions=definitions,
                     flowchart_path=flowchart_path, dryrun=dryrun, externals=externals, aliases=aliases)


def stage(function=None, *args, **kwargs):
    def decorator(_func):
        functools.wraps(_func)
        _func.stage_params = kwargs
        return _func

    # parameterized decorator
    if function is None:
        return decorator
    # parameterized decorator where a non-function stage is passed
    # this should be used like @stage(arg=stage("path.stage"))
    elif not inspect.isfunction(function):
        stage = resolve_stage(function)
        if stage is not None:
            stage.instance.stage_params = kwargs
            return stage.instance
        else:
            raise PipelineError(f'{function} could not be resolved as a stage.')
    else:  # unparameterized decorator
        return decorator(function)


def get_context():
    stack = list(frame for frame in inspect.stack())
    for frame in stack:
        f_locals = dict(frame.frame.f_locals)
        for name, obj in f_locals.items():
            if name == 'context' and isinstance(obj, Context):
                return obj
    return None


class DecoratedStage:
    def __init__(self, execute_func: Callable, stage_params: dict):
        self.execute_func = execute_func
        self.stage_params = stage_params
        self.func_params = inspect.signature(self.execute_func).parameters

    def configure(self, context):
        self._resolve_params(context)

    def execute(self, context):
        return self.execute_func(**self._resolve_params(context))

    def _resolve_params(self, context):
        """
        This function is used both when configuring a stage as well as collecting the kwargs for execution.
        Stages may be decorated in three different ways:
        1. simple decoration:
                @synpp.stage
                def foo(bar='baz'): ...
            Which will look for 'bar' in the global context config (or else use the method's default if available).
        2. parameterized decoration:
                @synpp.stage(bar='bar_pipeline')
                def foo(bar): ...
            Which will try to decide whether:
             a. 'bar_pipeline' is an available stage, and pass the method its results, or
             b. an argument in the global context config (or else use the method's default if available).
             Note: the default value for 'bar' must be set in the actual function, not in the decorator.
        3. fully parameterized decoration, which can be used for configuring the stage dependencies:
                @synpp.stage(bar=synpp.stage('pipeline.bar', bar_argkey='bar_argval'))
                def foo(bar): ...
            Using synpp.stage() inside the decorator works in the same way as the decorator itself, simply pass the
            target stage as first argument, and the config kwargs following it.
        """
        func_kwargs = {}
        for name, param in self.func_params.items():
            arg = self.stage_params.get(name)
            if arg is None:
                # case 1: simple decoration
                config_kwargs = {'option': name}
                if isinstance(context, ConfigurationContext) and param.default is not inspect._empty:
                    config_kwargs.update({'default': param.default})
                func_kwargs[name] = context.config(**config_kwargs)
            elif resolve_stage(arg) is not None:
                # case 2 or 3: stages only
                func_kwargs[name] = context.stage(arg, config=getattr(arg, 'stage_params', {}))
            else:
                # case 2: config parameter
                func_kwargs[name] = context.config(arg)

        return func_kwargs
