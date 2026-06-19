import logging
import os


# ANSI escape sequences for colors
class LogColors:
    RED = "\033[91m"
    YELLOW = "\033[93m"
    ORANGE = "\033[38;5;208m"  # There is no standard orange color in ANSI escape codes, so using 208
    CYAN = "\033[36m"
    RESET = "\033[0m"


# Custom formatter class that applies colors
class CustomFormatter(logging.Formatter):
    COLOR_MAP = {
        logging.ERROR: LogColors.RED,
        logging.WARNING: LogColors.YELLOW,
        logging.INFO: LogColors.CYAN,
    }

    def format(self, record):
        color = self.COLOR_MAP.get(record.levelno)
        if color:
            record.msg = f"{color}{record.msg}{LogColors.RESET}"
        return super().format(record)

def getDefaultLogLevel():
    level: str = os.getenv("LOG_LEVEL", "INFO")
    if level.lower() in ["info"]:
        return logging.INFO
    if level.lower() in ["warning", "warn"]:
        return logging.WARNING
    if level.lower() in ["error"]:
        return logging.ERROR
    return logging.DEBUG

# Define a function to set up a custom formatter and add it to the logger
def getLogger(name=None, level=getDefaultLogLevel(), use_handler=False):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = True
    
    # Define the custom format
    log_format = "%(asctime)s - %(pathname)s:%(lineno)d - %(funcName)s - %(levelname)s - %(message)s"
    formatter = CustomFormatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    # Add a console handler if not already added
    if not logger.handlers and use_handler:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


LOG_PRIORITY_DICT = {
    "chardet.charsetprober": logging.INFO,
    "datasets": logging.WARNING,
    "httpcore.connection": logging.INFO,
    "httpcore.http11": logging.INFO,
    "langchain_community.vectorstores.milvus": logging.INFO,
    "multipart.multipart": logging.INFO,
    "passlib.registry": logging.INFO,
    "passlib.utils.compat": logging.INFO,
    "pdfminer.cmapdb": logging.INFO,
    "pdfminer.converter": logging.INFO,
    "pdfminer.encodingdb": logging.INFO,
    "pdfminer.pdfdocument": logging.INFO,
    "pdfminer.pdfinterp": logging.INFO,
    "pdfminer.pdfpage": logging.INFO,
    "pdfminer.pdfparser": logging.INFO,
    "pdfminer.psparser": logging.INFO,
    "psycopg.pq": logging.INFO,
    "uvicorn.error": logging.WARNING,
}

logger = getLogger(__name__)
for logs in LOG_PRIORITY_DICT:
    logger.debug(f"Setting logger {logs} to {LOG_PRIORITY_DICT[logs]} and above.")
    logging.getLogger(logs).setLevel(LOG_PRIORITY_DICT[logs])
