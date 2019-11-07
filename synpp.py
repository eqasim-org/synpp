import importlib
import inspect
import hashlib, json
import networkx as nx

class NoDefaultValue:
    pass

class PipelineError(Exception):
    pass

class ConfigurationContext:
    def __init__(self, base_config, base_params):
        self.base_config = base_config
        self.base_params = base_params

        self.required_config = {}
        self.required_params = {}

        self.required_stages = []
        self.aliases = {}

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

    def param(self, name, default = NoDefaultValue()):
        if name in self.base_params:
            self.required_params[name] = self.base_params[name]
        elif not isinstance(default, NoDefaultValue):
            if name in self.required_params and not self.required_params[name] == default:
                raise PipelineError("Got multiple default values for parameter: %s" % name)

            self.required_params[name] = default

        if not name in self.required_params:
            raise PipelineError("Config option is not available: %s" % name)

        return self.required_params[name]

    def stage(self, stage, params = {}, alias = None):
        if not (stage, params) in self.required_stages:
            self.required_stages.append((stage, params))

            if not alias is None:
                self.aliases[alias] = (stage, params)

class StageWrapper:
    def __init__(self, delegate, type, base_name):
        self.delegate = delegate
        self.type = type
        self.base_name = base_name

    def configure(self, context):
        if hasattr(self.delegate, "configure"):
            return self.delegate.configure(context)

    def execute(self, context):
        if hasattr(self.delegate, "execute"):
            return self.delegate.execute(context)
        else:
            raise RuntimeError("Stage %s does not have execute method" % self.name)

class StageContext:
    def __init__(self, name, configuration_context, result_cache):
        self.name = name
        self.configuration_context = configuration_context
        self.result_cache = result_cache

    def param(self, name):
        if not name in self.configuration_context.required_params:
            raise PipelineError("Parameter %s is not requested for stage %s" % (name, self.name))

        return self.configuration_context.required_params[name]

    def config(self, name):
        if not name in self.configuration_context.required_config:
            raise PipelineError("Config option %s is not requested for stage %s" % (name, self.name))

        return self.configuration_context.required_config[name]

    def stage(self, name, params = {}):
        if name in self.configuration_context.aliases:
            if len(params) > 0:
                raise PipelineError("Cannot defined parameters for aliased stage")

            name, params = self.configuration_context.aliases[name]

        name = StageName(name, params)
        return self.result_cache[name.hashed()]

class StageName:
    def __init__(self, name, params):
        self.base_name = name
        self.params = params

    def _get_parameter_list_string(self):
        values = ["%s=%s" % (name, value) for name, value in self.params.items()]
        return ", ".join(sorted(values))

    def base(self):
        return self.base_name

    def parameterized(self):
        return "%s(%s)" % (self.base_name, self._get_parameter_list_string())

    def hashed(self):
        if len(self.params) > 0:
            hash = hashlib.md5()
            hash.update(json.dumps(self.params, sort_keys = True).encode("ascii"))
            return "%s_p_%s" % (self.base_name, hash.hexdigest())
        else:
            return self.base_name

    def __str__(self):
        return self.parameterized()

class ParameterizedStage:
    def __init__(self, delegate, name, configuration_context):
        self.delegate = delegate
        self.name = name
        self.configuration_context = configuration_context

    def execute(self, result_cache):
        context = StageContext(self.name, self.configuration_context, result_cache)
        return self.delegate.execute(context)

def resolve_stage(stage):
    if inspect.ismodule(stage):
        return StageWrapper(stage, "module", stage.__name__)

    if inspect.isclass(stage):
        return StageWrapper(stage(), "class", "%s.%s" % (stage.__module__, stage.__name__))

    if isinstance(stage, str):
        try:
            stage = importlib.import_module(stage)
            return StageWrapper(stage, "module by string",stage.__name__)
        except ModuleNotFoundError:
            parts = stage.split(".")
            module = importlib.import_module(".".join(parts[:-1]))
            constructor = getattr(module, parts[-1])
            stage = constructor()
            return StageWrapper(stage, "class by string", "%s.%s" % (constructor.__module__, constructor.__name__))

    clazz = stage.__class__
    return StageWrapper(stage, "instance", "%s.%s" % (clazz.__module__, clazz.__name__))

def process_stage_definition(stage_definition, config):
    stage_descriptor, stage_parameters = stage_definition
    stage_wrapper = resolve_stage(stage_descriptor)

    configuration_context = ConfigurationContext(config, stage_parameters)
    stage_wrapper.configure(configuration_context)

    stage_name = StageName(stage_wrapper.base_name, configuration_context.required_params)
    return ParameterizedStage(stage_wrapper, stage_name, configuration_context)

def run(required_definitions, config = {}, working_directory = None):
    configuration_contexts = {}

    # 1) Construct stage objects
    pending_definitions = required_definitions[:]

    parameterized_stages = {}
    required_parameterized_stages = []

    stage_dependencies = {}

    while len(pending_definitions) > 0:
        stage_definition = pending_definitions.pop(0)
        stage = process_stage_definition(stage_definition, config)

        if stage.name.hashed() in parameterized_stages:
            continue # Just to make sure the user does not define duplicates

        parameterized_stages[stage.name.hashed()] = stage
        stage_dependencies[stage.name.hashed()] = []

        if stage_definition in required_definitions:
            required_parameterized_stages.append(stage.name.hashed())

        for stage_definition in stage.configuration_context.required_stages:
            dependency = process_stage_definition(stage_definition, config)
            stage_dependencies[stage.name.hashed()].append(dependency.name.hashed())

            if not stage_definition in pending_definitions and not dependency.name.hashed() in parameterized_stages:
                pending_definitions.append(stage_definition)

    # 2) Order stages
    graph = nx.DiGraph()

    for key in parameterized_stages.keys():
        graph.add_node(key)

    for key, dependency_keys in stage_dependencies.items():
        for dependency_key in dependency_keys:
            graph.add_edge(dependency_key, key)

    for cycle in nx.cycles.simple_cycles(graph):
        cycle = [parameterized_stages[item].name.parameterized() for item in cycle]
        raise PipelineError("Found cycle: %s" % " -> ".join(cycle))

    sorted_stages = list(nx.topological_sort(graph))

    # 3) Devalidate stages

    # 4) Execute stages
    required_results = [None] * len(required_definitions)
    result_cache = {}

    for stage_name in sorted_stages:
        stage = parameterized_stages[stage_name]
        result = stage.execute(result_cache)

        result_cache[stage_name] = result

        if stage.name.hashed() in required_parameterized_stages:
            index = required_parameterized_stages.index(stage.name.hashed())
            required_results[index] = result

    return required_results





















#
