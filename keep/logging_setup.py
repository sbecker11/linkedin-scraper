# logging_setup.py
import logging
import sys

def setup_logging(log_file='app.log', console_level=logging.INFO, file_level=logging.DEBUG):
    # Create a root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set to lowest level to catch all logs

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create stdout handler and set level to console_level
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(console_level)
    stdout_handler.setFormatter(formatter)

    # Create file handler and set level to file_level
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    # Remove any existing handlers (to avoid duplicate logs)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add handlers to the root logger
    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(file_handler)

    return root_logger