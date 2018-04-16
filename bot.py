import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from emoji import emojize
from time import sleep

import urllib.request, json

from vedis import Vedis

from bot_api_token import XKCD_BOT_API_TOKEN

import states
import utils
import math
import random

# Connect to database
db = Vedis('db')

# Setup logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

LatestComicsNumber = 1981
QuestionImage = "question.png"

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
    if (num > 0) and (num <= LatestComicsNumber):
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


# Inline keyboard menu with respective callbacks. Instantiated once.
keyboard = [
    [ InlineKeyboardButton(emojize("Show Newest Comics :new:", use_aliases=True),
                           callback_data=states.S_NEWEST) ],

    [ InlineKeyboardButton(emojize("Show Random Comics :twisted_rightwards_arrows:", use_aliases=True),
                           callback_data=states.S_RANDOM) ],

    [ InlineKeyboardButton(emojize("Show Comics by its Number :1234: ...", use_aliases=True),
                           callback_data=states.S_NUMBER) ]
    # TODO: Implement search
    # ,

    # [ InlineKeyboardButton(emojize("[WIP] Search Comics by Phrase :mag: ...", use_aliases=True),
    #                        callback_data=states.S_PHRASE) ]
]

def onStart(bot, update):
    """ Reaction on start command. Sends photo with menu of inline keyboard buttons. """
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_photo(photo=open('what_xkcd.png', 'rb'), reply_markup=reply_markup)

def getUserState(update):
    """ Get user state based on given update's chat_id. Returns one of states defined in states.py.
        In case of any error returns S_START. """
    chat_id = update.effective_chat.id
    if chat_id == '':
        return states.S_START
    chat_id_state = '{}/state'.format(chat_id)

    if db.exists(chat_id_state):
        state = db[chat_id_state]
        if state in states.STATES:
            return db[chat_id_state]
        else:
            logger.warning("Something strange. Can't find this state: {}".format(state))
    return states.S_START

def setUserState(update, state):
    chat_id = update.effective_chat.id
    chat_id_state = '{}/state'.format(chat_id)
    db[chat_id_state] = state

def prepareComicsToSend(comics):
    """ Expects JSON comics. Prepare it using Markdown formatting.
        Returns [formatted text, link to image]. In case of any problems -- returns empty list """

    problem = ["Something went wrong... Next time we'll try to find your comics! Open /menu again.",
               QuestionImage]

    if not comics:
        logger.warning("Empty comics given. Nothing to do here.")
        return problem

    if comics.keys() < {'day', 'month', 'year', 'title', 'num', 'alt', 'img'}:
        logger.warning("Not enough keys in comics. Check comics JSON: {}".format(comics))
        return problem

    date = '{}/{}/{}'.format(comics['day'], comics['month'], comics['year'])
    link = '["{}" comics on XKCD](https://xkcd.com/{})'.format(comics['title'], comics['num'])
    text2send = '*{}. {}*. {}\n\n_{}_, {}'.format(comics['num'], comics['title'], comics['alt'], date, link)
    return [text2send, comics['img']]

def sendComics(bot, cur_chat_id, prepared_comics):
    """ Sends prepared comics: first -- sends image, then -- formatted text related to comics. """
    if prepared_comics[1] == QuestionImage:
        bot.send_photo(chat_id=cur_chat_id, disable_notification=True, photo=open(QuestionImage, 'rb'))
    else:
        bot.send_photo(chat_id=cur_chat_id, disable_notification=True, photo=prepared_comics[1])
    bot.send_message(chat_id=cur_chat_id, disable_notification=False, parse_mode='Markdown', text=prepared_comics[0])
    logger.info("sent: {} -- {}".format(prepared_comics[0], prepared_comics[1]))

def onButtonClicked(bot, update):
    query = update.callback_query
    cur_chat_id = query.message.chat_id
    if query.data:
        # Remove MENU-message
        bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    else:
        return

    user_state = getUserState(update)

    if user_state == states.S_START:
        if query.data == states.S_NEWEST:
            prepared_comics = prepareComicsToSend(getCurrentComics())
            sendComics(bot, cur_chat_id, prepared_comics)
            setUserState(update, states.S_START)

        if query.data == states.S_NUMBER:
            text2send = "Please, enter integer number of XKCD comics (first one is `1` and last one is `{}`)"\
                        .format(LatestComicsNumber)
            bot.send_message(chat_id=cur_chat_id,
                             disable_notification=False,
                             parse_mode='Markdown',
                             text=text2send)
            setUserState(update, states.S_NUMBER)

        if query.data == states.S_RANDOM:
            random_number = random.randint(1, LatestComicsNumber + 1)
            prepared_comics = prepareComicsToSend(getComicsByNumber(random_number))
            sendComics(bot, cur_chat_id, prepared_comics)
            setUserState(update, states.S_START)


def onMessage(bot, update):
    state = getUserState(update)
    if state == states.S_NUMBER:
        msg = update.effective_message.text
        if utils.RepresentsInt(msg):
            num = int(msg)
            if comicsAvailable(num):
                prepared_comics = prepareComicsToSend(getComicsByNumber(num))
                sendComics(bot, update.effective_chat.id, prepared_comics)
                setUserState(update, states.S_START)
                return
            else:
                sendComics(bot, update.effective_chat.id,
                           ["Unfortunately there is comics with number `{}` :( \n"
                            "Let's hope that someday there will be even `{}` comics on XKCD! \n\n"                           
                            "But still you can use /menu for another requests.".format(num, num+1), QuestionImage])
                setUserState(update, states.S_START)
                return

        else:
            setUserState(update, states.S_NUMBER)
            sendComics(bot, update.effective_chat.id,
                       ["`{}` is not a valid integer number, you know it. \n\n"
                        "Please, send me *only* number, without any other symbols. "
                        "Examples of correct numbers: `13`, `42`, `666`, `1000`, ...".format(msg), QuestionImage])
            return

    # Problem happened
    sendComics(bot, update.effective_chat.id,
               ["Something wrong happened. Hope our admins will check logs and solve this problem. "
                "Meanwhile you can use /menu for another requests.", QuestionImage])
    setUserState(update, states.S_START)


def onHelp(bot, update):
    update.message.reply_text("Main command is /menu -- to see menu and finally start having fun here.")

def onError(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

UNDEFINED = -1

def numberOfComics(comics):
    if comics and 'num' in comics:
        return int(comics['num'])
    return UNDEFINED

needToCheckLastComics = True

def stopCheckingForLatestComics():
    global needToCheckLastComics
    needToCheckLastComics = False

def checkForLatestComics(delay=600):
    global needToCheckLastComics
    while needToCheckLastComics:
        LatestComicsNumber = numberOfComics(getComics('https://xkcd.com/info.0.json'))
        # write to DB
        logger.info("Checked. Latest number is {}. Next check will be done in {}s.".format(LatestComicsNumber, delay))
        for i in range(1, delay):
            if not needToCheckLastComics:
                logger.info("Stop checking for new comics.")
                return
            else:
                sleep(1)
    logger.info("Stop checking for new comics.")


import asyncio
from threading import Thread

def startCheckerForLatestComics(loop):
    """ Switch to new event loop and run forever """
    asyncio.set_event_loop(loop)
    loop.run_forever()

def main():
    # Create the new loop and worker thread
    checkerLoop = asyncio.new_event_loop()
    checker = Thread(target=startCheckerForLatestComics, args=(checkerLoop,))
    checker.start()
    checkerLoop.call_soon_threadsafe(checkForLatestComics)
    logger.info("Started new thread for checking latest comics.")


    # Create the Updater and pass it your bot's token
    updater = Updater(XKCD_BOT_API_TOKEN)

    updater.dispatcher.add_handler(CommandHandler('start', onStart))
    updater.dispatcher.add_handler(CommandHandler('menu', onStart))
    updater.dispatcher.add_handler(CallbackQueryHandler(onButtonClicked))
    updater.dispatcher.add_handler(CommandHandler('help', onHelp))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, onMessage))
    updater.dispatcher.add_error_handler(onError)

    # Start the Bot
    updater.start_polling()
    logger.info("Bot started")

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
    updater.idle()

    stopCheckingForLatestComics()
    checkerLoop.stop()
    checker.join()

if __name__ == '__main__':
    main()
