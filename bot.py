import logging
import utils
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from emoji import emojize
from vedis import Vedis

import latest_comics_checker as Checker
import comics as Comics
import states
import bot_api_token as Secrets

# Connect to database
db = Vedis('db')

# Setup logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

QuestionImage = "images/question.png"

# Inline keyboard menu with respective callbacks. Instantiated once.
menu_keyboard = [
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
    reply_markup = InlineKeyboardMarkup(menu_keyboard)
    update.message.reply_photo(photo=open('images/what_xkcd.png', 'rb'), reply_markup=reply_markup)

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

def getUserComicsNumber(update):
    UNDEFINED = -1

    import numbers

    chat_id = update.effective_chat.id
    if chat_id == '':
        return UNDEFINED
    chat_id_num = '{}/num'.format(chat_id)

    if db.exists(chat_id_num):
        num = int(db[chat_id_num])
        if isinstance(num, numbers.Number):
            return int(db[chat_id_num])
        else:
            logger.warning("Something strange. Wrong user's num: {}".format(num))
    return UNDEFINED

def setUsersComicsNumber(update, num):
    chat_id = update.effective_chat.id
    chat_id_num = '{}/num'.format(chat_id)
    db[chat_id_num] = num

def prepareComicsToSend(comics):
    """ Expects JSON comics. Prepare it using Markdown formatting.
        Returns [formatted text, link to image]. In case of any problems -- returns empty list """

    problem = ["Something went wrong... Next time we'll try to find your comics! Open /menu again.",
               QuestionImage, Checker.UNDEFINED]

    if not comics:
        logger.warning("Empty comics given. Nothing to do here.")
        return problem

    if comics.keys() < {'day', 'month', 'year', 'title', 'num', 'alt', 'img'}:
        logger.warning("Not enough keys in comics. Check comics JSON: {}".format(comics))
        return problem

    date = '{}/{}/{}'.format(comics['day'], comics['month'], comics['year'])
    link = '["{}" comics on XKCD](https://xkcd.com/{})'.format(comics['title'], comics['num'])
    text2send = '*{}. {}*. {}\n\n_{}_, {}'.format(comics['num'], comics['title'], comics['alt'], date, link)
    return [text2send, comics['img'], comics['num']]

# Inline keyboard for comics with respective callbacks. Instantiated once.
comics_keyboard = InlineKeyboardMarkup([
    [   # First row
        InlineKeyboardButton(emojize("|<", use_aliases=True), callback_data=states.S_OLDEST),
        InlineKeyboardButton(emojize("< Prev", use_aliases=True), callback_data=states.S_PREV),
        InlineKeyboardButton(emojize("Random", use_aliases=True), callback_data=states.S_RANDOM),
        InlineKeyboardButton(emojize("Next >", use_aliases=True), callback_data=states.S_NEXT),
        InlineKeyboardButton(emojize(">|", use_aliases=True), callback_data=states.S_NEWEST)
    ]
    # ,
    # [   # Second row
    #     InlineKeyboardButton(emojize("Menu", use_aliases=True), callback_data="Menu"),
    #     InlineKeyboardButton(emojize("Search", use_aliases=True), callback_data="Search")
    # ]
])

def sendComics(bot, cur_chat_id, prepared_comics):
    """ Sends prepared comics: first -- sends image, then -- formatted text related to comics. """
    if prepared_comics[1] == QuestionImage:
        foto = open(QuestionImage, 'rb')
    else:
        foto = prepared_comics[1]
    bot.send_photo(chat_id=cur_chat_id, disable_notification=True, photo=foto)
    bot.send_message(chat_id=cur_chat_id, disable_notification=True, parse_mode='Markdown',
                     disable_web_page_preview=True, text=prepared_comics[0])
    bot.send_message(chat_id=cur_chat_id, disable_notification=True, parse_mode='Markdown',
                     text='What are you going to do next?', reply_markup=comics_keyboard)
    # logger.info("sent: {} -- {}".format(prepared_comics[0], prepared_comics[1]))

def onButtonClicked(bot, update):
    query = update.callback_query
    cur_chat_id = query.message.chat_id
    if query.data:
        # Remove MENU-message
        bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    else:
        return

    user_state = getUserState(update)
    # TODO: Use user_state later, when there will be search

    # if user_state == states.S_START:
    if query.data == states.S_NEWEST:
        prepared_comics = prepareComicsToSend(Comics.getLatestComics())
        sendComics(bot, cur_chat_id, prepared_comics)
        setUsersComicsNumber(update, prepared_comics[2])
        setUserState(update, states.S_START)

    # if user_state == states.S_START:
    if query.data == states.S_OLDEST:
        prepared_comics = prepareComicsToSend(Comics.getComicsByNumber(1))
        sendComics(bot, cur_chat_id, prepared_comics)
        setUsersComicsNumber(update, prepared_comics[2])
        setUserState(update, states.S_START)

    if query.data == states.S_NUMBER:
        text2send = "Please, enter integer number of XKCD comics (first one is `1` and last one is `{}`)"\
                    .format(Checker.LatestComicsNumber)
        bot.send_message(chat_id=cur_chat_id,
                         disable_notification=False,
                         parse_mode='Markdown',
                         text=text2send)
        setUserState(update, states.S_NUMBER)

    if query.data == states.S_RANDOM:
        random_number = random.randint(1, Checker.LatestComicsNumber + 1)
        prepared_comics = prepareComicsToSend(Comics.getComicsByNumber(random_number))
        sendComics(bot, cur_chat_id, prepared_comics)
        setUsersComicsNumber(update, prepared_comics[2])
        setUserState(update, states.S_START)

    if query.data == states.S_PREV:
        currentNum = getUserComicsNumber(update)
        if currentNum == Checker.UNDEFINED:
            newNum = Checker.LatestComicsNumber - 1
        newNum = currentNum - 1
        if Comics.isComicsAvailable(newNum):
            prepared_comics = prepareComicsToSend(Comics.getComicsByNumber(newNum))
            sendComics(bot, cur_chat_id, prepared_comics)
            setUsersComicsNumber(update, prepared_comics[2])
            setUserState(update, states.S_START)

    if query.data == states.S_NEXT:
        currentNum = getUserComicsNumber(update)

        newNum = currentNum + 1
        if Comics.isComicsAvailable(newNum):
            prepared_comics = prepareComicsToSend(Comics.getComicsByNumber(newNum))
            sendComics(bot, cur_chat_id, prepared_comics)
            setUsersComicsNumber(update, prepared_comics[2])
        else:
            prepared_comics = [QuestionImage,
                               "Unfortunately we can't get your {} comics. Probably it will be ready soon. "
                               "XKCD updates every Monday, Wednesday, and Friday.".format(currentNum)]
            sendComics(bot, cur_chat_id, prepared_comics)

    setUserState(update, states.S_START)

def onMessage(bot, update):
    state = getUserState(update)
    if state == states.S_NUMBER:
        msg = update.effective_message.text
        if utils.RepresentsInt(msg):
            num = int(msg)
            if Comics.isComicsAvailable(num):
                prepared_comics = prepareComicsToSend(Comics.getComicsByNumber(num))
                sendComics(bot, update.effective_chat.id, prepared_comics)
                setUserState(update, states.S_START)
                return
            else:
                sendComics(bot, update.effective_chat.id,
                           ["Unfortunately there is no comics with number `{}` :( \n"
                            "Let's hope that someday there will be even `{}` comics on XKCD! \n\n"                           
                            "But still you can use /menu for another requests.".format(num, num + 1), QuestionImage])
                setUserState(update, states.S_START)
                return

        else:
            setUserState(update, states.S_NUMBER)
            sendComics(bot, update.effective_chat.id,
                       ["`{}` is not a valid integer number, you know it. \n\n"
                        "Please, send me *only* number, without any other symbols. "
                        "Examples of correct numbers: `13`, `42`, `666`, `1000`, ...\n\n"
                        "Or you can use /menu as usual.".format(msg), QuestionImage])
            return

    # Problem happened
    sendComics(bot, update.effective_chat.id,
               ["We tried to understand your answer, but we forgot what was the question... "
                "Hope our admins will check logs and solve this problem in newer versions of this bot. \n\n"
                "Meanwhile you can use /menu for another requests.", QuestionImage])
    setUserState(update, states.S_START)


def onHelp(bot, update):
    update.message.reply_text("Main command is /menu -- to see menu and finally start having fun here.")

def onError(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

def main():
    # Create the new loop and worker thread
    Checker.startCheckerLoop()

    logger.info("Started new thread for checking latest comics.")

    # Create the Updater and pass it your bot's token
    updater = Updater(Secrets.XKCD_BOT_API_TOKEN)

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
    logger.info("Bot already stopped.")

    Checker.stopCheckerLoop()

if __name__ == '__main__':
    main()
