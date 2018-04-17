import logging
import asyncio
from time import sleep
from threading import Thread

import comics as Comics

LatestComicsNumber = 1981
needToCheckLastComics = True
UNDEFINED = -1

# Setup logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def numberOfComics(comics):
    if comics and 'num' in comics:
        return int(comics['num'])
    return UNDEFINED

def stopCheckingForLatestComics():
    global needToCheckLastComics
    needToCheckLastComics = False

def checkForLatestComics(delay=600):
    global needToCheckLastComics
    global LatestComicsNumber
    while needToCheckLastComics:
        newNum = numberOfComics(Comics.getComics('https://xkcd.com/info.0.json'))
        if newNum is not UNDEFINED:
            LatestComicsNumber = newNum
            logger.info("Checked. Latest number is {}. Next check will be done in {}s."
                        .format(LatestComicsNumber, delay))
            for i in range(1, int(delay/2)):
                if not needToCheckLastComics:
                    logger.info("Stop checking for new comics.")
                    return
                else:
                    sleep(2)
    logger.info("Stop checking for new comics.")

def startCheckerForLatestComics(loop):
    """ Switch to new event loop and run forever """
    asyncio.set_event_loop(loop)
    loop.run_forever()

checkerLoop = asyncio.new_event_loop()
checker = Thread(target=startCheckerForLatestComics, args=(checkerLoop,))

def startCheckerLoop():
    checker.start()
    checkerLoop.call_soon_threadsafe(checkForLatestComics)

def stopCheckerLoop():
    stopCheckingForLatestComics()
    checkerLoop.stop()
    checker.join()