import logging

from logging import FileHandler, Formatter, Logger


def get_logger(module_name: str) -> Logger:
    logger: Logger = logging.getLogger(module_name)
    logger.setLevel(logging.INFO)

    formatter: Formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(name)s: %(message)s')

    file_handler: FileHandler = logging.FileHandler('temp/stock_action_20230703.log')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger
