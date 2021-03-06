import logging, os, time, socket

class EDASLogger:
    logger = None

    @classmethod
    def getLogger(cls):
        if cls.logger is None:
            LOG_DIR = os.path.expanduser("~/.edas/logs")
            if not os.path.exists(LOG_DIR):  os.makedirs(LOG_DIR)
            timestamp = time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime())
            cls.logger = logging.getLogger( "edas" )
            cls.logger.setLevel(logging.DEBUG)
            fh = logging.FileHandler("{}/edas-{}-{}.log".format(LOG_DIR, socket.gethostname(), timestamp))
            fh.setLevel(logging.DEBUG)
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('EDAS-%(asctime)s-%(levelname)s: %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            cls.logger.addHandler(fh)
            cls.logger.addHandler(ch)
        return cls.logger
