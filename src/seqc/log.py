__author__ = 'ambrose'

import logging
from datetime import datetime
import os


def setup_logger(filename='seqc.log'):
    """create a simple log file in the cwd to track progress and any errors"""
    if os.path.isfile(filename):
        os.remove(filename)
    logging.basicConfig(filename=filename, filemode='w', level=logging.DEBUG)


def info(message):
    """print a timestamped update for the user"""
    logging.info(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ':' + message)


def exception():
    logging.exception(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ':main:')


def notify(message):
    """print a timestamped update for the user and log it to file"""
    info(message)
    print('SEQC: ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ': %s' % message)
