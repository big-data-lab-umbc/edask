import logging, os, time
LOG_DIR = os.path.expanduser("~/.edas/logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

timestamp = time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime() )
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler( "{}/edask-{}.log".format( LOG_DIR, timestamp ) )
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)