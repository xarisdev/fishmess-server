import logging
from pathlib import Path

LOG_DIR = Path('logs')
LOG_FILE = LOG_DIR / 'log.log'
LOG_LEVEL = logging.INFO

def setup_logger(module_name: str):
    logger = logging.getLogger(module_name)
    logger.setLevel(LOG_LEVEL)

    if not logger.handlers:
        LOG_DIR.mkdir(exist_ok=True)
        formatter = logging.Formatter(
            f'%(asctime)s [{module_name.upper()}] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger