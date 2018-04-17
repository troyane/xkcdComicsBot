import logging
import math
import urllib.request, json
from time import sleep

import latest_comics_checker as Checker

# Setup logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def getComics(request, maxTries=10):
    """ Returns current comics over given request as JSON object. In case of any problems function returns empty string.
        Function waits twice longer each time in case of problems with network requests (maximum tries is maxTries)."""
    tries = 1
    success = False
    response = ''
    while (not success) and (tries < maxTries):
        timeout = math.pow(2, tries) # wait twice longer each time
        try:
            with urllib.request.urlopen(request) as url:
                response = json.loads(url.read().decode())
        except:
            logger.warning("Problem with network or something. Increase timeout to {}s, it is try #{}."
                           .format(timeout, tries))
            tries = tries + 1
            sleep(timeout)
        else:
            success = True
    if response == '':
        logger.error("Something went wrong with request '{}'. Can't wait longer.".format(request))
    return response

def getCurrentComics():
    """ Returns current (latest one) comics. Link for latest comics is hardcoded here. """
    CURRENT_COMICS = 'https://xkcd.com/info.0.json'
    return getComics(CURRENT_COMICS)

def comicsAvailable(num):
    if (num > 0) and (num <= Checker.LatestComicsNumber):
        return True
    else:
        return False

def getComicsByNumber(num):
    """ Returns comics by its number. There is number check. """
    import numbers
    if isinstance(num, numbers.Number):
        if comicsAvailable(num):
            TEMPLATE_URL = 'https://xkcd.com/{}/info.0.json'.format(num)
            return getComics(TEMPLATE_URL)
    return ''