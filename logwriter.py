import logging

from colorama import Fore, Back, Style
from datetime import datetime

class LogHelper:
    def __init__(self):
        filename = datetime.now().strftime('logs/run_%H_%M_%d_%m_%Y.log')
        self.log = logging.getLogger()
        handler = logging.FileHandler(filename)
        self.log.addHandler(handler)

    def warning(self, kind, msg):
        print("[" + Fore.RED + kind + Style.RESET_ALL +"]: " + msg)
        self.log.warning("[" + kind + "] " + msg)
