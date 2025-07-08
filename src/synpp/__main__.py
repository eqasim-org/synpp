import logging
import os
import sys

import synpp

if __name__ == "__main__":
    logging.basicConfig(level = logging.INFO)
    synpp.run_from_cmd(sys.argv[1:])
