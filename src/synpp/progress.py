import logging, json, time
import zmq, threading
import synpp

def format_time(time):
    hours = time // 3600
    minutes = (time - hours * 3600) // 60
    seconds = int(time - hours * 3600 - minutes * 60)

    if hours > 0:
        return "%02d:%02d:%02d" % (hours, minutes, seconds)
    elif minutes > 0:
        return "%02d:%02d" % (minutes, seconds)
    else:
        return "%ds" % seconds

class ProgressTracker:
    def __init__(self, total = None, label = None, logger = logging.getLogger("synpp"), minimum_interval = 0):
        self.total = total
        self.value = 0
        self.start_time = time.time()
        self.last_report = time.time() - 1
        self.minimum_interval = minimum_interval
        self.logger = logger
        self.label = label

    def update(self, amount = 1):
        amount = max(amount, 1)
        self.value += amount
        current_time = time.time()

        if current_time > self.last_report + self.minimum_interval or self.value == self.total:
            self.last_report = current_time
            self.report()

    def report(self):
        current_time = time.time()
        if current_time == self.start_time:
            current_time = current_time + 1
        message = []

        if not self.label is None:
            message.append(self.label)

        if self.total is None:
            message.append("%d" % self.value)
        else:
            message.append("%d/%d (%.2f%%)" % (self.value, self.total, 100 * self.value / self.total))

        samples_per_second = self.value / (current_time - self.start_time)

        if samples_per_second >= 1.0:
            message.append("[%.2fit/s]" % samples_per_second)
        else:
            message.append("[%.2fs/it]" % (1.0 / samples_per_second,))

        message.append("RT %s" % format_time(current_time - self.start_time))

        if not self.total is None:
            remaining_time = (self.total - self.value) / samples_per_second
            message.append("ETA %s" % format_time(remaining_time))

        message = " ".join(message)
        self.logger.info(message)

class ProgressServer(threading.Thread):
    def __init__(self, tracker):
        threading.Thread.__init__(self)
        context = zmq.Context()

        self.socket = context.socket(zmq.PULL)
        self.port = self.socket.bind_to_random_port("tcp://*")
        self.running = True

        self.poller = zmq.Poller()
        self.poller.register(self.socket)

        self.tracker = tracker

    def run(self):
        while True:
            try:
                message = json.loads(self.socket.recv(flags = zmq.NOBLOCK))
                self.tracker.update(message["amount"])
            except zmq.Again:
                time.sleep(0.001)

                if not self.running:
                    return

    def stop(self):
        self.running = False

class ProgressClient:
    def __init__(self, port):
        context = zmq.Context()

        self.socket = context.socket(zmq.PUSH)
        self.socket.connect("tcp://localhost:%d" % port)

    def update(self, amount = 1):
        self.socket.send_string(json.dumps(dict(amount = amount)))

class ProgressContext:
    def __init__(self, iterable = None, total = None, label = None, logger = logging.getLogger("synpp"), minimum_interval = 0):
        self.tracker = ProgressTracker(total, label, logger, minimum_interval)
        self.iterable = iterable
        self.server = None

    def __enter__(self):
        if not self.server is None:
            raise synpp.PipelineError("Progress context is already open")

        self.server = ProgressServer(self.tracker)
        self.server.start()

        return self

    def __exit__(self, type, value, traceback):
        if self.server is None:
            raise synpp.PipelineError("Progress is not open")

        self.server.stop()
        self.server = None

    def __iter__(self):
        if self.iterable is None:
            raise RuntimeError("No iterable given.")

        with self:
            for item in self.iterable:
                yield item
                self.update()

    def update(self, amount = 1):
        self.tracker.update(amount)
