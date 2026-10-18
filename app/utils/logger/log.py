import logging
import os
from datetime import datetime


def configure_logger(business_name: str="fastapi-starter"):
    """
    The `configure_logger` function sets up a logger named "my_app_logger" with both console and file
    handlers.
    :return: The function `configure_logger` is returning a logger object that has been configured with
    a console handler and a file handler, both using the specified formatter.
    """
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join("logs", business_name)
    os.makedirs(logs_dir, exist_ok=True)
    
    # Construct log file name with current date and time
    log_file = os.path.join(logs_dir, f"{business_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}.log")
    
    logger = logging.getLogger(business_name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:  # Only add handlers if none exist
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger

logs = configure_logger()
