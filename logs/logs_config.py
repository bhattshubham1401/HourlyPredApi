import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler('app_log.log', maxBytes=1024 * 1024 * 10, backupCount=3)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
