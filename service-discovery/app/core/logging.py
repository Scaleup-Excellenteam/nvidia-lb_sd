import logging
import os
"""
add this module into your project
"""

# constant of my service name - change per service
SERVICE_NAME = "Service-Discovery"

# Get log file path from environment variable
log_file = os.environ.get("LOG_FILE", "/app/logs/combined.log")

# Configure logging
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(message)s'
)

# set the logger name
logger = logging.getLogger(SERVICE_NAME)

# use case:
#   1. from logger import logger
#   2. logger.info("some log message")
#   3. logger.error("some error message")