import logging
import os
import sys

def logger(name, file_output=True, stdout_level=logging.INFO,stdout=True):
    """
    Creates logger object using default file and stdout settings. File outputs split into
    debug and info thresholds.

    Args:
        name (str): Logger name
        file_output (bool): Output logs to file for records
        stdout_level (logging.object): Threshold for stdout
        stdout (bool): Output logs to stdout

    Returns:

    """
    handlers = []

    # Stdout settings
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_formatter = logging.Formatter('[%(asctime)s] %(message)s', '%Y-%m-%d %H:%M:%S')
    stdout_handler.setFormatter(stdout_formatter)

    # Stdout threshold
    stdout_handler.setLevel(stdout_level)

    # Collate settings, initialise
    if stdout:
        handlers.append(stdout_handler)

    # Output logs to files if applicable
    if file_output:
        # File settings
        file_formatter = logging.Formatter('[%(asctime)s] - %(name)s - %(levelname)s - %(message)s',
                                           '%Y-%m-%d %H:%M:%S')

        # Generate log folder
        log_root_folder = os.getcwd()
        # log_root_folder = os.path.dirname(os.path.dirname(__file__))
        log_folder = os.path.join(log_root_folder, './logs')
        os.makedirs(log_folder, exist_ok=True)

        # debug.log file settings
        debug_file_handler = logging.FileHandler(filename='./logs/debug.log')
        debug_file_handler.setFormatter(file_formatter)
        debug_file_handler.setLevel(logging.DEBUG)

        # info.log file settings
        info_file_handler = logging.FileHandler(filename='./logs/info.log')
        info_file_handler.setFormatter(file_formatter)
        info_file_handler.setLevel(logging.INFO)

        handlers += [
            info_file_handler,
            debug_file_handler
        ]

    logging.basicConfig(handlers=handlers)
    logger_ = logging.getLogger(name)
    logger_.setLevel(logging.DEBUG)
    return logger_