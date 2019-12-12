import time, logging

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

class ProgressContext:
    def __init__(self, iterable = None, total = None, label = None, logger = logging.getLogger("synpp"), minimum_interval = 0):
        self.iterable = iterable

        if not iterable is None:
            try:
                self.total = len(iterable)
            except TypeError:
                pass

        self.total = total
        self.label = label
        self.logger = logger
        self.minimum_interval = minimum_interval

        self.reset(0)

    def reset(self, value = 0, total = None):
        self.start_time = time.time()
        self.start_value = value
        self.current_value = value
        self.last_report = time.time() - 1
        self.total = total

    def set(self, value):
        self.current_value = value

    def __enter__(self):
        self.reset(0)
        return self

    def __exit__(self, type, value, traceback):
        pass

    def __iter__(self):
        if self.iterable is None:
            raise RuntimeError("No iterable given.")

        with self:
            for item in self.iterable:
                yield item
                self.update()

    def update(self, amount = 1):
        self.current_value += amount

        current_time = time.time()
        if current_time > self.last_report + self.minimum_interval or self.current_value == self.total:
            self.last_report = current_time
            self.report()

    def report(self):
        current_time = time.time()
        message = []

        if not self.label is None:
            message.append(self.label)

        if self.total is None:
            message.append("%d" % self.current_value)
        else:
            message.append("%d/%d (%.2f%%)" % (self.current_value, self.total, 100 * self.current_value / self.total))

        samples_per_second = (self.current_value - self.start_value) / (current_time - self.start_time)

        if samples_per_second >= 1.0:
            message.append("[%dit/s]" % samples_per_second)
        else:
            message.append("[%ds/it]" % (1.0 / samples_per_second,))

        message.append("RT %s" % format_time(current_time - self.start_time))

        if not self.total is None:
            remaining_time = (self.total - self.current_value) / samples_per_second
            message.append("ETA %s" % format_time(remaining_time))

        message = " ".join(message)
        self.logger.info(message)
