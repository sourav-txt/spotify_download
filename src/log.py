import errno
import logging, sys, os
from logging.handlers import RotatingFileHandler

from src.config import load as load_config

config = load_config()

# Validate logging level
if config["LOGGING_LEVEL"] not in ['INFO', 'DEBUG']:
    raise Exception('Logging level should be either INFO or DEBUG')

# Configure root logger
logFormatter = logging.Formatter('[%(asctime)s] %(levelname)-9s %(name)-12s : %(message)s')
rootLogger = logging.getLogger()
rootLogger.setLevel(config["LOGGING_LEVEL"])

# Console logger, log to stdout instead of stderr
consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

# File logger
if config["LOGGING_PATH"] == '':
    log_file = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'logs', 'spotify_download.log'))
else:
    log_file = config["LOGGING_PATH"]

if not os.path.exists(os.path.dirname(log_file)):
    try:
        os.makedirs(os.path.dirname(log_file))
    except OSError as exc: # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise

fileHandler = RotatingFileHandler(
    log_file,
    maxBytes=2097152,
    backupCount=5,
    encoding='utf-8'
)

fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

# Set external module logging policy
if config["LOGGING_LEVEL"] == 'DEBUG':
    #logging.getLogger('urllib3').setLevel(logging.DEBUG)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('spotipy').setLevel(logging.DEBUG)
    logging.getLogger('deemix').propagate = True
else:
    # Decrease modules logging
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('spotipy').setLevel(logging.ERROR)
    logging.getLogger('deemix').propagate = False
