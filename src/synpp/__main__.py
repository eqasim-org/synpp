import logging
import os
import sys

import synpp

if __name__ == "__main__":
    logging.basicConfig(level = logging.INFO)
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yml"

    if not os.path.isfile(config_path):
        raise synpp.PipelineError("Config file does not exist: %s" % config_path)

    synpp.run_from_yaml(config_path)
