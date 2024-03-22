import logging
import colorlog

class LoggerDefinition(): # TODO: This log class isn't properly implemented, maybe change it to a simple function?
    @staticmethod
    def logger():
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)

            log_colors = {
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white'
            }

            formatter = colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                log_colors=log_colors)
            
            ch.setFormatter(formatter)
            logger.addHandler(ch)

        return logger