import multiprocessing as mp
from .general import PipelineParallelError
from .progress import ProgressClient

class ParallelSlaveContext:
    def __init__(self, data, config, progress_port = None):
        self._config = config
        self._data = data

        if not progress_port is None:
            self.progress = ProgressClient(progress_port)

    def config(self, option):
        if not option in self._config:
            raise PipelineError("Config option is not available: %s" % option)

        return self._config[option]

    def data(self, name):
        if not name in self._data:
            raise PipelineParallelError("Variable '%s' has not been passed to the parallel context" % name)

        return self._data[name]

    def stage(self, *kargs, **kwargs):
        raise PipelineParallelError("Cannot access stages from the parallel context")

    def parallel(self, *kargs, **kwargs):
        raise PipelineParallelError("Cannot spawn new parallel processes from a parallel process")

def pipeline_initializer(pipeline_data, pipeline_config, pipeline_progress_port):
    global pipeline_parallel_context
    pipeline_parallel_context = ParallelSlaveContext(pipeline_data, pipeline_config, pipeline_progress_port)

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
    def __init__(self, data, config, processes, progress_context):
        if processes is None: processes = mp.cpu_count()

        self.processes = processes
        self.config = config
        self.data = data
        self.pool = None

        self.progress_context = progress_context

    def __enter__(self):
        if not self.pool is None:
            raise PipelineParallelError("Parallel context has already been entered")

        progress_port = None
        if not self.progress_context is None:
            if not self.progress_context.server is None:
                progress_port = self.progress_context.server.port

        self.pool = mp.Pool(
            processes = self.processes,
            initializer = pipeline_initializer,
            initargs = (self.data, self.config, progress_port)
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

class ParallelMockSlaveContext:
    def __init__(self, data, config, progress):
        self._config = config
        self._data = data
        self.progress = progress

    def config(self, option):
        if not option in self._config:
            raise PipelineError("Config option is not available: %s" % option)

        return self._config[option]

    def data(self, name):
        if not name in self._data:
            raise PipelineParallelError("Variable '%s' has not been passed to the parallel context" % name)

        return self._data[name]

    def stage(self, *kargs, **kwargs):
        raise PipelineParallelError("Cannot access stages from the parallel context")

    def parallel(self, *kargs, **kwargs):
        raise PipelineParallelError("Cannot spawn new parallel processes from a parallel process")

class ParalelMockMasterContext:
    def __init__(self, data, config, progress):
        self.config = config
        self.data = data
        self.entered = False

        self.progress = progress

    def __enter__(self):
        if self.entered:
            raise PipelineParallelError("Parallel context has already been entered")

        self.entered = True
        return self

    def __exit__(self ,type, value, traceback):
        if not self.entered:
            raise PipelineParallelError("Parallel context has not been entered")

        self.entered = False

    def map(self, func, iterable, chunksize = 1):
        if chunksize > 1:
            raise PipelineParallelError("Only allowed chunksize = 1 in simulated parallel mode")

        return [
            func(ParallelMockSlaveContext(self.data, self.config, self.progress), item)
            for item in iterable
        ]

    def map_async(self, func, iterable, chunksize = 1, callback = None):
        raise PipelineParallelError("Not possible ot use map_async in simulated parallel mode")

    def imap(self, func, iterable, chunksize = 1):
        return self.map(func, iterable, chunksize)

    def imap_unordered(self, func, iterable, chunksize = 1):
        return self.map(func, iterable, chunksize)
