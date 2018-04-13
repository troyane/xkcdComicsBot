import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from emoji import emojize

import urllib.request, json

from vedis import Vedis

from bot_api_token import XKCD_BOT_API_TOKEN

import states
import utils

# Connect to database
db = Vedis('db')

# Setup logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

LAST_AVAILABLE_XKCD = 1979

def getCurrentComics():
    CURRENT_COMICS = 'https://xkcd.com/info.0.json'
    with urllib.request.urlopen(CURRENT_COMICS) as url:
        return json.loads(url.read().decode())

def getComicsByNumber(num):
    import numbers
    if isinstance(num, numbers.Number):
        TEMPLATE_URL = 'https://xkcd.com/{}/info.0.json'
        with urllib.request.urlopen(TEMPLATE_URL.format(num)) as url:
            return json.loads(url.read().decode())
    else:
        return ''


keyboard = [
    [ InlineKeyboardButton(emojize("Show Newest Comics :new:", use_aliases=True),
                           callback_data=states.S_NEWEST) ],

    [ InlineKeyboardButton(emojize("[WIP] Show Random Comics :twisted_rightwards_arrows:", use_aliases=True),
                           callback_data=states.S_RANDOM) ],

    [ InlineKeyboardButton(emojize("Show Comics by its Number :1234: ...", use_aliases=True),
                           callback_data=states.S_NUMBER) ],

    [ InlineKeyboardButton(emojize("[WIP] Search Comics by Phrase :mag: ...", use_aliases=True),
                           callback_data=states.S_PHRASE) ]
]

def onStart(bot, update):
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_photo(photo=open('what_xkcd.png', 'rb'), reply_markup=reply_markup)

def getUserState(update):
    chat_id = update.effective_chat.id
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
    if not comics:
        logger.warning("Empty comics given. Nothing to do here.")
        return ""

    if comics.keys() < {'day', 'month', 'year', 'title', 'num', 'alt', 'img'}:
        logger.warning("Not enough keys in comics. Check comics JSON: {}".format(comics))
        return ""

    date = '{}/{}/{}'.format(comics['day'], comics['month'], comics['year'])
    link = '["{}" comics on XKCD](https://xkcd.com/{})'.format(comics['title'], comics['num'])
    text2send = '*{}*. {}\n\n_{}_, {}'.format(comics['title'], comics['alt'], date, link)
    return [text2send, comics['img']]

def sendComics(bot, cur_chat_id, prepared_comics):
    logger.warning("sent: {}\n\n{}".format(prepared_comics[0], prepared_comics[1]))
    bot.send_photo(chat_id=cur_chat_id,
                   disable_notification=True,
                   photo=prepared_comics[1])
    bot.send_message(chat_id=cur_chat_id,
                     disable_notification=False,
                     parse_mode='Markdown',
                     text=prepared_comics[0])

def onButtonClicked(bot, update):
    query = update.callback_query
    cur_chat_id = query.message.chat_id
    if query.data:
        # Remove MENU-message
        bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

    state = get_user_state(update)

    if state == states.S_START:
        if query.data == states.S_NEWEST:
            prepared_comics = prepare_comics_to_send(getCurrentComics())
            send_comics(bot, cur_chat_id, prepared_comics)
            set_user_state(update, states.S_START)

        if query.data == states.S_NUMBER:
            text2send = 'Please, enter integer number of XKCD comics (first one is #1 and last one is {})'.format(LAST_AVAILABLE_XKCD)
            bot.send_message(chat_id=cur_chat_id,
                             disable_notification=False,
                             parse_mode='Markdown',
                             text=text2send)
        set_user_state(update, states.S_NUMBER)


def onMessage(bot, update):
    state = get_user_state(update)
    if state == states.S_NUMBER:
        # TODO: Check msg type
        # msg = update.effective_message...
        msg = update.effective_message.text
        if utils.RepresentsInt(msg):
            prepared_comics = prepare_comics_to_send(getComicsByNumber(int(msg)))
            send_comics(bot, update.effective_chat.id, prepared_comics)
            set_user_state(update, states.S_START)

def onHelp(bot, update):
    update.message.reply_text("Use /start to start having fun here.")


def onError(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

def main():
    # Create the Updater and pass it your bot's token.
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

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()