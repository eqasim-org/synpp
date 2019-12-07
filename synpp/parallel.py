import multiprocessing as mp
from .general import PipelineParallelError

class ParallelSlaveContext:
    def __init__(self, data, config, parameters):
        self._config = config
        self._parameters = parameters
        self._data = data

    def config(self, option):
        if not option in self._config:
            raise PipelineError("Config option is not available: %s" % option)

        return self._config[option]

    def parameter(self, name):
        if not name in self._parameters:
            raise PipelineError("Config option is not available: %s" % name)

        return self._parameters[name]

    def data(self, name):
        if not name in self._data:
            raise PipelineParallelError("Variable '%s' has not been passed to the parallel context" % name)

        return self._data[name]

    def stage(self, *kargs, **kwargs):
        raise PipelineParallelError("Cannot access stages from the parallel context")

    def parallel(self, *kargs, **kwargs):
        raise PipelineParallelError("Cannot spawn new parallel processes from a parallel process")

def pipeline_initializer(pipeline_data, pipeline_config, pipeline_parameters):
    global pipeline_parallel_context
    pipeline_parallel_context = ParallelSlaveContext(pipeline_data, pipeline_config, pipeline_parameters)

def pipeline_runner(args):
    global pipeline_parallel_context
    callable, args = args
    return callable(pipeline_parallel_context, args)

class wrap_callable:
    def __init__(self, callable, iterable):
        self.callable = callable
        self.iterable = iterable

    def __iter__(self):
        for element in self.iterable:
            yield (self.callable, element)

class ParallelMasterContext:
    def __init__(self, data, config, parameters, processes):
        if processes is None: processes = mp.cpu_count()
        
        self.processes = processes
        self.config = config
        self.parameters = parameters
        self.data = data
        self.pool = None

    def __enter__(self):
        if not self.pool is None:
            raise PipelineParallelError("Parallel context has already been entered")

        self.pool = mp.Pool(
            processes = self.processes,
            initializer = pipeline_initializer,
            initargs = (self.data, self.config, self.parameters)
        )

        return self

    def __exit__(self ,type, value, traceback):
        if self.pool is None:
            raise PipelineParallelError("Parallel context has not been entered")

        self.pool.close()
        self.pool = None

    def map(self, func, iterable, chunksize = 1):
        return self.pool.map(pipeline_runner, wrap_callable(func, iterable), chunksize)

    def map_async(self, func, iterable, chunksize = 1, callback = None):
        return self.pool.map_async(pipeline_runner, wrap_callable(func, iterable), chunksize, callback = callback)

    def imap(self, func, iterable, chunksize = 1):
        return self.pool.imap(pipeline_runner, wrap_callable(func, iterable), chunksize)

    def imap_unordered(self, func, iterable, chunksize = 1):
        return self.pool.imap_unordered(pipeline_runner, wrap_callable(func, iterable), chunksize)
