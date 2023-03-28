import importlib
import logging
import os
import random
import subprocess
from datetime import datetime, timedelta

import mysql.connector
import pytz
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (ApplicationBuilder, CallbackContext,
                          CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, filters)

load_dotenv()
tz = pytz.timezone('Europe/Berlin')
at_chat_id = os.environ.get('AT_CHATID')
db_table = os.environ.get('DB_TABLE')
messages = {
    'de': {
        'welcome': {},
        'language_confirm': {},
        'first_send_confirm': {},
        'send_pseudo': {},
        'help' : {}
    },
    'en': {
        'welcome': {},
        'language_confirm': {},
        'first_send_confirm': {},
        'send_pseudo': {},
        'help' : {}
    }
}
users = {}
pseudos = {}
at_reply_chat_id = ""
at_reply_message = ""
at_message_edit = {}

#async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
#    """Log Errors caused by Updates."""
#    logger.error(msg="Exception while handling an update:", exc_info=context.error)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_dependencies():
    with open('requirements.txt') as f:
        requirements = f.read().splitlines()
    missing_deps = []
    for req in requirements:
        try:
            importlib.import_module(req)
        except ImportError:
            missing_deps.append(req)
    if missing_deps:
        print(f"The following dependencies are missing: {', '.join(missing_deps)}")
        print("Installing dependencies. Please wait...")
        subprocess.run(['pip', 'install'] + list(missing_deps), check=True)
    else:
        print("All dependencies are installed.")

def initialize_data_from_db():
    global users
    global pseudos
    global messages
    global at_message_edit
    global db_table
    global at_chat_id
    
    if at_chat_id:
        at_chat_id = int(at_chat_id)
    
    load_dotenv()
    at_message_edit['edit'] = None
    
    try:
        # Connect to the MySQL database
        db = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        cursor=db.cursor(dictionary=True)
        query = f"SELECT chat_id, pseudo, user_state, language_code, updated_at FROM {db_table}"
        cursor.execute(query)
        result = cursor.fetchall()
    except mysql.connector.Error as error:
        print("Failed to retrieve data from the database: {}".format(error))
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

    if result:
        for dbuser in result:
            users[int(dbuser['chat_id'])]={}
            users[int(dbuser['chat_id'])]['pseudo']=dbuser['pseudo']
            users[int(dbuser['chat_id'])]['user_state']=dbuser['user_state']
            users[int(dbuser['chat_id'])]['language_code']=dbuser['language_code']
            users[int(dbuser['chat_id'])]['updated_at']=dbuser['updated_at']
            pseudos[dbuser['pseudo']]='burned'


async def create_db_user(chat_id):
    load_dotenv()

    global users
    global db_table

    try:
        # Connect to the MySQL database
        db = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        pseudo=users[chat_id]['pseudo']
        state=users[chat_id]['user_state']
        lang=users[chat_id]['language_code']
        cursor = db.cursor()
        query = f"INSERT INTO {db_table} (chat_id,pseudo,user_state,language_code) VALUES (%s,%s,%s,%s)"
        values = (chat_id,pseudo,state,lang,)
        cursor.execute(query, values)
        db.commit()
    except mysql.connector.Error as error:
        print("Failed to insert record into the database: {}".format(error))
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()
    
async def update_db_user(chat_id):
    try:
        load_dotenv()
        global users
        global pseudos
        global db_table
        users[chat_id]['updated_at']=datetime.now()
        # Connect to the MySQL database
        db = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        cursor = db.cursor(dictionary=True)
        query = f"SELECT pseudo, user_state, language_code, updated_at FROM {db_table} WHERE chat_id = %s"
        values = (chat_id,)
        cursor.execute(query, values)
        result=cursor.fetchone()
        pseudo=users[chat_id]['pseudo']
        state=users[chat_id]['user_state']
        lang=users[chat_id]['language_code']
        if result:
            if result['pseudo'] != pseudo:
                old_pseudonumber = ''
                if result['user_state']!='new':
                    old_pseudonumber = int(str(result['pseudo'])[-2:])
                    users[old_pseudonumber]={}
                    users[old_pseudonumber]['pseudo']=result['pseudo']
                    users[old_pseudonumber]['user_state']='burned'
                    users[old_pseudonumber]['language_code']='de'
                    pseudos[result['pseudo']]='burned'
                query = f"UPDATE {db_table} SET pseudo = %s WHERE chat_id = %s"
                values = (pseudo,chat_id,)
                cursor.execute(query, values)
                db.commit()
                await create_db_user(old_pseudonumber)
            if result['user_state'] != state:
                query = f"UPDATE {db_table} SET user_state = %s WHERE chat_id = %s"
                values = (state,chat_id,)
                cursor.execute(query, values)
                db.commit()
            if result['language_code'] != lang:
                query = f"UPDATE {db_table} SET language_code = %s WHERE chat_id = %s"
                values = (lang,chat_id,)
                cursor.execute(query, values)
                db.commit()
            updatedelta = users[chat_id]['updated_at'] - result['updated_at']
            if updatedelta > timedelta(minutes=3):
                query = f"UPDATE {db_table} SET updated_at = CURRENT_TIMESTAMP WHERE chat_id = %s"
                values = (chat_id,)
                cursor.execute(query, values)
                db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"An error occurred while updating user {chat_id}: {e}")
    finally:
        if (db.is_connected()):
            cursor.close()
            db.close()

async def user_is_blocked(chat_id:int):
    global users
    if chat_id in users.keys():
        if users[int(chat_id)]['user_state'] == 'blocked':
            updatedelta = datetime.now() - users[chat_id]['updated_at']
            if updatedelta < timedelta(days=365):
                return True
            else:
                users[chat_id]['user_state'] = 'new'
                await update_db_user(chat_id=chat_id)
                return False
        else:
            return False
    else:
        return False
    
def generate_pseudo():
    global users
    used_pseudos = []
    number = random.randint(10, 99)
    pseudonym = f"Anonymous{number}"
    for user in users.values():
        used_pseudos.extend(user.values())
    while pseudonym in used_pseudos:
        number = random.randint(10, 99)
        pseudonym = f"Anonymous{number}"
    return pseudonym

async def set_language(chat_id :int, lang):
    global users
    if not await user_is_blocked(chat_id=chat_id):
        users[chat_id]['language_code'] = lang
        await update_db_user(chat_id)

async def send_language_confirm(callback_query, chat_id):
    global users
    global messages
    language = users[chat_id]['language_code']
    if language == 'de':
        await callback_query.edit_message_text(text="Du hast Deutsch gewählt.")
    if language == 'en':
        await callback_query.edit_message_text(text="You have chosen English")

async def send_pseudo_info(context : ContextTypes.DEFAULT_TYPE, chat_id):
    global users
    language = users[chat_id]['language_code']
    if language == 'de':
        await context.bot.send_message(chat_id=chat_id, text=f"Dieser Bot leitet deine Nachrichten an das Awarenessteam weiter. Deine Nachrichten und Medien können nicht vom Awarenessteam weitergeleitet oder heruntergeladen. Deine Telefonnummer und dein Name bleiben dabei so lange anonym, bis du selbst entscheidest sie mit uns zu teilen. Dir wird automatisch ein Pseudonym zugeteilt. Dein Pesudonym lautet: {users[chat_id]['pseudo']}.\n\nMehr Informationen in der Beschreibung und unter dem /help Command.\n\nJede Nachricht die du nun schreibst wird an das Awarenessteam weitergeleitet.")
    if language == 'en':
        await context.bot.send_message(chat_id=chat_id, text=f"This Bot will forward your Messages to the Awarenessteam. Your messages and media cannot be forwarded or downloaded by the awareness team. You will automatically be assigned a pseudonym. Your data will remain absolutely anonymous until you decide to share them with us. Your Pseudonym is: {users[chat_id]['pseudo']}.\n\nFind more information in the description our through the /help Command.\n\nAny message you send here will automatically be forwarded to the awareness team.")

async def send_time_warning(context: ContextTypes.DEFAULT_TYPE, chat_id):
    global users
    if users[chat_id]['language_code'] == 'de':
        await context.bot.send_message(chat_id=chat_id, text="Deine letzte Nachricht liegt über vier Wochen zurück. Wenn es sich um einen neuen Fall handelt, möchtest du vielleicht dein Pseudonym wechseln um weiterhin Anonym zu bleiben.\n\nDeine Nachricht wird nach der Auswahl weitergeleitet.", reply_markup=get_pseudo_renew_keyboard())
    if users[chat_id]['language_code'] == 'en':
        await context.bot.send_message(chat_id=chat_id, text="Your last message is over four weeks old. If this is a new case, you may want to change your pseudonym to remain anonymous.\n\nYour message will be forwarded after selection.", reply_markup=get_pseudo_renew_keyboard())

async def send_block_note(context: ContextTypes.DEFAULT_TYPE, chat_id):
    global users
    block_date = users[chat_id]['updated_at'] + timedelta(days=365)
    date_str = block_date.strftime("%d.%m.%Y")
    if users[chat_id]['language_code'] == 'de':
        await context.bot.send_message(chat_id=chat_id, text=f"Du wurdest vom Awarenessteam bis zum {date_str} geblockt. Bitte wende dich über einen anderen Kommunikationsweg ans Awarenessteam.")
    if users[chat_id]['language_code'] == 'en':
        await context.bot.send_message(chat_id=chat_id, text=f"You are blocked till {date_str}. Please choose another way to contact the awarenessteam.")

def get_language_keyboard():
    german_button = InlineKeyboardButton("Deutsch", callback_data="lang-de")
    english_button = InlineKeyboardButton("English", callback_data="lang-en")
    keyboard = [[german_button],[english_button]]
    return InlineKeyboardMarkup(keyboard)

def get_pseudo_renew_keyboard():
    keyboard = [[InlineKeyboardButton("Erneuern/Renew", callback_data="renew")],[InlineKeyboardButton("Abbrechen/Cancel", callback_data="renew-cancel")]]
    return InlineKeyboardMarkup(keyboard)

def get_at_messages_keyboard():
    global messages
    message_keys = list(messages['de'].keys())
    keyboard = []
    for key in message_keys:
        callback_key = str(key)
        button = InlineKeyboardButton(text=f"{key}", callback_data=f"messsage-{callback_key}")
        keyboard.append([button])
    keyboard.append([InlineKeyboardButton(text="Cancel", callback_data="message-cancel")])
    return InlineKeyboardMarkup(keyboard)

def get_at_messages_cancel_keyboard():
    keyboard= [[InlineKeyboardButton(text="Cancel", callback_data="message-cancel")]]
    return InlineKeyboardMarkup(keyboard)

def get_at_messages_edit_keyboard(key, lang):
    keyboard = [[InlineKeyboardButton("Cancel", callback_data="message-cancel")], [InlineKeyboardButton("Edit", callback_data=f"message-edit-{lang}-{key}")]]
    return InlineKeyboardMarkup(keyboard)

def get_at_messages_confirm_keyboard():
    keyboard = [[InlineKeyboardButton("Cancel", callback_data="message-cancel")], [InlineKeyboardButton("Confirm", callback_data=f"message-confirm")]]
    return InlineKeyboardMarkup(keyboard)

def get_at_block_confirm_keyboard(chat_id):
    confirm_button = InlineKeyboardButton("Confirm", callback_data=f"at-block-{chat_id}-confirm")
    cancel_button = InlineKeyboardButton("Cancel", callback_data=f"at-block-{chat_id}-cancel")
    keyboard = [[confirm_button, cancel_button]]
    return InlineKeyboardMarkup(keyboard)

def get_awareness_reply_keyboard(chat_id):
    reply_button = InlineKeyboardButton("Antworten", callback_data=f"at-reply-{chat_id}")
    block_button = InlineKeyboardButton("Blockieren", callback_data=f"at-block-{chat_id}")
    keyboard = [[reply_button],[block_button]]
    return InlineKeyboardMarkup(keyboard)

def get_awareness_reply_confirm_keyboard():
    confirm_button = InlineKeyboardButton("Bestätigen", callback_data="at-confirm-sending")
    cancel_button = InlineKeyboardButton("Abbrechen", callback_data="at-cancel-sending")
    keyboard = [[confirm_button, cancel_button]]
    return InlineKeyboardMarkup(keyboard)

def get_awareness_reply_cancel_keyboard():
    cancel_button = InlineKeyboardButton("Abbrechen", callback_data="at-cancel-sending")
    keyboard = [[cancel_button]]    
    return InlineKeyboardMarkup(keyboard)

def get_menu_keyboard():
    keyboard = [[InlineKeyboardButton("Pseudo Erneuern/Renew", callback_data="renew-plain")]]
    return InlineKeyboardMarkup(keyboard)

async def get_blocked_user_keyboard():
    global users
    blocked_users = []
    for chat_id in users.keys():
        if await user_is_blocked(chat_id=chat_id):
            blocked_users.append(chat_id)
    keyboard = []
    for blocked_user in blocked_users:
        keyboard.append([InlineKeyboardButton(text=f"{users[blocked_user]['pseudo']}", callback_data=f"unban-{blocked_user}")])
    keyboard.append([InlineKeyboardButton(text="Cancel", callback_data="unban-cancel")])
    return InlineKeyboardMarkup(keyboard)

def get_unban_confirm_keyboard(chat_id : int):
    confirm_button = InlineKeyboardButton(text="Confirm", callback_data=f"unban-{chat_id}-confirm")
    cancel_button = InlineKeyboardButton(text="Cancel", callback_data="unban-cancel")
    return InlineKeyboardMarkup([[confirm_button],[cancel_button]])

# Define a function to handle the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global users
    chat_id = int(update.effective_chat.id)
    if await user_is_blocked(chat_id=chat_id):
        await send_block_note(context=context, chat_id=chat_id)
        return
    if chat_id not in users.keys():
        users[chat_id] = {}
        pseudonym = generate_pseudo()
        users[chat_id]['pseudo']=pseudonym
        users[chat_id]['language_code']='de'
        users[chat_id]['user_state']='new'
        users[chat_id]['updated_at']=datetime.now()
        await create_db_user(chat_id)
    
    await context.bot.send_message(chat_id=chat_id, text="Wähle eine Sprache:\n\n Choose a language:", reply_markup=get_language_keyboard())

# Define a function to handle the /language command
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global users
    chat_id = update.effective_chat.id
    if await user_is_blocked(chat_id=chat_id):
        await send_block_note(context=context, chat_id=chat_id)
        return
    await context.bot.send_message(chat_id=chat_id, text="Wähle eine Sprache:\n\n Choose a language:", reply_markup=get_language_keyboard())

# Define a function to handle the /renew_pseudo command
async def renew_pseudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global users
    chat_id = update.effective_chat.id
    if await user_is_blocked(chat_id):
        await send_block_note(context, chat_id)
        return
    pseudonym = generate_pseudo()
    users[chat_id]['pseudo']=pseudonym
    await update_db_user(chat_id=chat_id)
    await send_pseudo_info(context=context, chat_id=chat_id)

# Define a function to handle the /messages command
async def setup_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global messages
    global at_chat_id
    chat_id = update.effective_chat.id
    
    if chat_id != at_chat_id:
        await context.bot.send_message(chat_id=chat_id, text="You do not have the necessary permissions")
        return
    
    await context.bot.send_message(chat_id=chat_id, text="Wähle die Nachricht, welche du bearbeiten möchtest:", reply_markup=get_at_messages_keyboard())
    
# Define a function to handle the /menu command
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Alle Funktionen:", reply_markup=get_menu_keyboard())  

# Define a function to handle the /chatid command
async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Your chat ID is {chat_id}")

# Define a functin to handle the /help command
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global users
    chat_id = update.effective_chat.id
    if users[chat_id]['language_code'] == 'de':
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Dieser Telegram-Bot wurde programmiert um einen einfachen und Anonymen Kommunikationsweg mit dem Awarenessteam zu etablieren.\n\nDie Nachrichten, welche du schreibst, werden dem Awarenessteam mit dem Zusatz \"PseudonymXY schrieb:\" weitergeleitet, damit sie verschiedene Fälle auseinanderhalten können. Dein Name wird dabei nicht geteilt.\n\nÜber den Bot ist es auch möglich Bilder und andere Medien, bis hin zu Standorten mit dem Awarenessteam zu teilen. Deine Nachrichten und Medien können nicht vom Awarenessteam weitergeleitet oder heruntergeladen. Weitere technische Infos können unter github.com/hack2c/AwarenessteamTelegramBot eingesehen werden, wo der Bot quelloffen zugänglich ist.\n\nMit dem Befehl /renew_pseudo kannst du dir ein neues Pseudonym zuweisen lassen. Dies ist vor allem dann nützlich, wenn du bereits in einem anderen Fal mit dem Awarenessteam zu tun hattest.\nMit dem Befehl /language lässt sich die Sprachauswahl erneut aufrufen.\n\nACHTUNG: Mit diesen Bot erreichst du immer BEIDE Teile des Awarenessteams gleichzeitig.", reply_markup=get_menu_keyboard(), disable_web_page_preview=True)
    if users[chat_id]['language_code'] == 'en':
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"This Telegram bot was programmed to establish a simple and anonymous communication channel with the awareness team.\n\nThe messages you write will be forwarded to the awareness team with the addition \"PseudonymXY wrote:\" so they can differentiate between different cases. Your name will not be shared.\n\nThrough the bot, it is also possible to share pictures and other media, up to locations, with the awareness team. Further technical information can be found at github.com/hack2c/AwarenessteamTelegramBot, where the bots code is openly accessible.\n\nWith the command /renew_pseudo you can assign yourself a new pseudonym. This is especially useful if you have already dealt with the awareness team in another case.\nWith the command /language the language selection can be called up again.\n\nWARNING: With this bot, you always reach BOTH parts of the awareness team at the same time", reply_markup=get_menu_keyboard(), disable_web_page_preview=True)
        

# Define a function to handle the /unban command
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global users
    global at_chat_id
    chat_id = update.effective_chat.id
    if chat_id != int(at_chat_id):
        await context.bot.send_message(chat_id=chat_id, text="You do not have the necessary permissions")
        return
    await context.bot.send_message(chat_id=at_chat_id, text="Chosse a User, you want to unban:", reply_markup=await get_blocked_user_keyboard())


# Define a function to handle the "Language" button callback
async def handle_lang_callback(update: Update, context: CallbackContext):
    global users
    callback_query = update.callback_query
    callback_data = update.callback_query.data
    chat_id = update.callback_query.message.chat_id
    await callback_query.answer()
    await callback_query.edit_message_reply_markup(reply_markup=None)
    if await user_is_blocked(chat_id=chat_id):
        await send_block_note(context=context, chat_id=chat_id)
        return
    lang = callback_data.split("-")[-1]
    await set_language(chat_id=chat_id, lang=lang)
    await send_language_confirm(callback_query, chat_id)
    await send_pseudo_info(context, chat_id)

async def handle_renew_callback(update: Update, context: CallbackContext):
    global users
    global at_chat_id
    callback_query = update.callback_query
    callback_data = update.callback_query.data
    chat_id = update.callback_query.message.chat_id
    await callback_query.answer()
    await callback_query.edit_message_reply_markup(reply_markup=None)
    if await user_is_blocked(chat_id=chat_id):
        await send_block_note(context=context, chat_id=chat_id)
        return
    callback_split = callback_data.split("-")
    pseudonym = users[chat_id]['pseudo']

    if len(callback_split) > 1:
        if callback_split[1] == "cancel":
            if users[chat_id]['language_code'] == 'de':
                await callback_query.edit_message_text("Deine Nachricht wurde erfolgreich weitergeleitet.")
            if users[chat_id]['language_code'] == 'en':
                await callback_query.edit_message_text("Your Message was successfully forwarded.")
        if callback_split[1] == "plain":
            await renew_pseudo(update=update, context=context)
            return
        message_id = users[chat_id]['time_message_id']
        await context.bot.send_message(chat_id=at_chat_id, text=f"{pseudonym} wrote:")
        await context.bot.copy_message(chat_id=at_chat_id, from_chat_id=chat_id, message_id=message_id, reply_markup=get_awareness_reply_keyboard(chat_id))
        return
    
    message_id = users[chat_id]['time_message_id']
    pseudonym = generate_pseudo()
    users[chat_id]['pseudo']=pseudonym
    await update_db_user(chat_id=chat_id)
    await send_pseudo_info(context=context, chat_id=chat_id)
    await context.bot.send_message(chat_id=at_chat_id, text=f"{pseudonym} wrote:")
    await context.bot.copy_message(chat_id=at_chat_id, from_chat_id=chat_id, message_id=message_id, reply_markup=get_awareness_reply_keyboard(chat_id))
    if users[chat_id]['language_code'] == 'de':
        await callback_query.edit_message_text("Deine Nachricht wurde erfolgreich weitergeleitet.")
    if users[chat_id]['language_code'] == 'en':
        await callback_query.edit_message_text("Your Message was successfully forwarded.")

# Define a function to handle the "Messages" button callback
async def handle_setup_messages_callback(update: Update, context: CallbackContext):
    global messages
    global at_message_edit
    callback_query = update.callback_query
    callback_data = update.callback_query.data
    chat_id = update.callback_query.message.chat_id
    await callback_query.answer()

    key = callback_data.split("-")[1]

    if key == "cancel":
        await callback_query.edit_message_text(text="You canceld the edit.", reply_markup=None)
        at_message_edit = {}
        return
    
    message_keys = list(messages['de'].keys())
    if key in message_keys:
        at_message_edit['key'] = key
        await callback_query.edit_message_text("Select the Message, that you want to edit:", reply_markup=get_at_messages_cancel_keyboard())
        try:
            await context.bot.copy_message(chat_id=chat_id, from_chat_id=messages['de'][key][chat_id], message_id=messages["de"][key][chat_id], reply_markup=get_at_messages_edit_keyboard(key, lang='de'))
        except:
            await context.bot.send_message(chat_id=chat_id, text="There is no Custom Message set", reply_markup=get_at_messages_edit_keyboard(key, lang='de'))
        try:
            await context.bot.copy_message(chat_id=chat_id, from_chat_id=messages['en'][key][chat_id], message_id=messages["en"][key][chat_id], reply_markup=get_at_messages_edit_keyboard(key, lang='en'))
        except:
            await context.bot.send_message(chat_id=chat_id, text="There is no Custom Message set", reply_markup=get_at_messages_edit_keyboard(key, lang='en'))
    
    if key == "edit":
        at_message_edit['edit'] = True
        await context.bot.send_message(chat_id=chat_id, text="Please enter the new Message:")

    if key == "confirm":
        messages[at_message_edit["lang"]][at_message_edit["key"]]['chat_id']=at_message_edit["chat_id"]
        messages[at_message_edit["lang"]][at_message_edit["key"]]['message_id']=at_message_edit["message_id"]
        at_message_edit = {}
        await callback_query.edit_message_text("Edit Successfull")       

# Define a function to handle the "AT-Reply" button callback
async def handle_at_reply_callback(update: Update, context: CallbackContext):
    global at_reply_chat_id
    global users
    callback_query = update.callback_query
    callback_data = update.callback_query.data
    user_chat_id = callback_data.split("-")[-1]
    at_reply_chat_id = user_chat_id
    at_chat_id = int(os.environ.get('AT_CHATID'))
    pseudonym = users[int(at_reply_chat_id)]['pseudo']
    await context.bot.send_chat_action(chat_id=at_reply_chat_id, action="typing")
    await context.bot.send_message(chat_id=at_chat_id, text=f"Your next message will be forwarded to the User with the pseudonym:{pseudonym}.", reply_markup = get_awareness_reply_cancel_keyboard())
    await callback_query.answer()

# Define a function to handle the Awarenessteam "Cancel" callback
async def handle_at_cancel_sending_callback(update: Update, context: CallbackContext):
    global at_reply_chat_id
    global at_reply_message
    callback_query = update.callback_query
    callback_data = update.callback_query.data
    at_chat_id = int(os.environ.get('AT_CHATID'))
    at_reply_chat_id=""
    at_reply_message=""
    await callback_query.edit_message_text(text="Your Message was not send. Please press the reply Button again.", reply_markup=None)
    await callback_query.answer()

# Define a function to handle the Awarenessteam "Confirm" callback
async def handle_at_confirm_sending_callback(update: Update, context: CallbackContext):
    global users
    global at_reply_chat_id
    global at_reply_message
    callback_query = update.callback_query
    callback_data = update.callback_query.data
    at_chat_id = int(os.environ.get('AT_CHATID'))
    if users[int(at_reply_chat_id)]['user_state'] == 'pending':
        if users[int(at_reply_chat_id)]['language_code'] == 'de':
            await context.bot.send_message(chat_id= int(at_reply_chat_id), text="Das Awarenessteam schrieb:")
        elif users[int(at_reply_chat_id)]['language_code'] == 'en':
            await context.bot.send_message(chat_id= int(at_reply_chat_id), text="The Awarenessteam replied:")
        users[int(at_reply_chat_id)]['user_state'] = 'active'
        await update_db_user(chat_id=int(at_reply_chat_id))
    await context.bot.copy_message(chat_id = int(at_reply_chat_id), from_chat_id=at_chat_id, message_id=at_reply_message)
    at_reply_chat_id=""
    at_reply_message=""
    await context.bot.send_message(chat_id=at_chat_id, text="Your Message was send successfully.", reply_markup=None)
    await callback_query.edit_message_reply_markup(None)
    await callback_query.answer()

# Define a function to handle the Block Button Callback
async def handle_at_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global users
    global at_chat_id
    callback_query = update.callback_query
    await callback_query.answer()
    callback_data = update.callback_query.data
    callback_split = callback_data.split("-")
    chat_id = int(callback_split[2])
    block_date = users[chat_id]['updated_at'] + timedelta(days=365)
    date_str = block_date.strftime("%d.%m.%Y")

    if len(callback_split) > 3:
        if callback_split[3] == 'cancel':
            await callback_query.edit_message_text("Block Canceled")
            return
        
        if callback_split[3] == 'confirm':
            users[chat_id]['user_state']='blocked'
            await callback_query.edit_message_text(text=f"{users[chat_id]['pseudo']} is blocked till {date_str}.")
            await update_db_user(chat_id=chat_id)
            await send_block_note(chat_id=chat_id, context=context)
            return
        
    await context.bot.send_message(chat_id=at_chat_id, text=f"You are about to block {users[chat_id]['pseudo']} for one year ({date_str}). Are you sure about that?", reply_markup=get_at_block_confirm_keyboard(chat_id))

# Define a function to handle the unabn Button Callback
async def handle_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global users
    global at_chat_id
    callback_query = update.callback_query
    await callback_query.answer()
    callback_data = update.callback_query.data

    callback_split = callback_data.split("-")

    if len(callback_split) < 3:
        if callback_split[1] == 'cancel':
            await callback_query.edit_message_text("Unban canceled.")
            return
        chat_id = int(callback_split[1])
        await callback_query.edit_message_text(f"Your about to unban {users[chat_id]['pseudo']}. Are you sure about that?")
        await callback_query.edit_message_reply_markup(reply_markup=get_unban_confirm_keyboard(chat_id))
        return
    
    if len(callback_split) >= 3:
        if callback_split[2] == 'confirm':
            chat_id = int(callback_split[1])
            users[chat_id]['user_state'] = 'new'
            await update_db_user(chat_id=chat_id)
            if users[chat_id]['language_code'] == 'de':
                await context.bot.send_message(chat_id=chat_id, text="Du wurdest vom Awarenessteam entbannt.")
            if users[chat_id]['language_code'] == 'en':
                await context.bot.send_message(chat_id=chat_id, text="You have been unbanned by the Awareness Team.")
            await callback_query.edit_message_text(f"User {users[chat_id]['pseudo']} is unbaned")
    

# Define a function to handle a message without command
async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global users
    global at_reply_message
    global at_reply_chat_id
    global at_chat_id
    global at_message_edit
    chat_id = update.effective_chat.id

    if chat_id != at_chat_id:
        if await user_is_blocked(chat_id):
            await send_block_note(context, chat_id)
            return
        updatedelta = datetime.now() - users[chat_id]['updated_at']
        if updatedelta > timedelta(weeks=4):
            await send_time_warning(context, chat_id)
            users[chat_id]['time_message_id'] = update.effective_message.id
            await update_db_user(chat_id=chat_id)
            return
        if users[chat_id]['user_state'] == 'new':
            if users[chat_id]['language_code'] == 'de':
                await context.bot.send_message(chat_id=chat_id, text="Deine Nachricht wurde erfolgreich an das Awarenssteam weitergeleitet.")
            elif users[int(at_reply_chat_id)]['language_code'] == 'en':
                await context.bot.send_message(chat_id=chat_id, text="Your Message was successfully send to the Awarenessteam.")
            users[chat_id]['user_state'] = 'pending'
        await update_db_user(chat_id=chat_id)
        pseudonym = users[chat_id]['pseudo']
        message_id = update.effective_message.id
        await context.bot.send_message(chat_id=at_chat_id, text=f"{pseudonym} wrote:")
        await context.bot.copy_message(chat_id=at_chat_id, from_chat_id=chat_id, message_id=message_id, reply_markup=get_awareness_reply_keyboard(chat_id), protect_content=True)

    if chat_id == at_chat_id:
        if at_reply_chat_id:
            pseudonym = users[int(at_reply_chat_id)]['pseudo']
            at_reply_message=update.effective_message.id
            await context.bot.send_message(chat_id = at_chat_id, text = f"The folloowing Message will be send to {pseudonym}:")
            await context.bot.copy_message(chat_id = at_chat_id, from_chat_id=at_chat_id, message_id=at_reply_message, reply_markup=get_awareness_reply_confirm_keyboard())
        if at_message_edit['edit']:
            at_message_edit['chat_id'] = chat_id
            at_message_edit['message_id'] = update.effective_message.id
            await context.bot.send_message(chat_id=at_chat_id, text=f"You will update {at_message_edit['key']}, language {at_message_edit['lang']} to:")
            await context.bot.copy_message(chat_id=at_chat_id, from_chat_id=at_message_edit["chat_id"], message_id=at_message_edit["message_id"])
            await context.bot.send_message(chat_id=at_chat_id, text="Are you sure?", reply_markup=get_at_messages_confirm_keyboard())

def main() -> None:
    load_dotenv()
    check_dependencies()
    token = str(os.environ.get('TELEGRAM_API_TOKEN'))
    secret_token = str(os.environ.get('SECRET_TOKEN'))
    webserver = str(os.environ.get('WEBSERVER'))
    url_path = str(os.environ.get('URL_PATH'))
    webhook = str(os.environ.get('SERVE_AS_WEBHOOK'))
    port = int(str(os.environ.get('WEBHOOK_PORT')))
    keypath = str(os.environ.get('SSL_KEY_PATH'))
    certpath = str(os.environ.get('SSL_CERT_PATH'))
    mainurl = str(os.environ.get('PUBLIC_DOMAIN'))
    if token is None:
        print("Error: TELEGRAM_API_TOKEN environment variable not set")
        exit(1)

    initialize_data_from_db()

    application = ApplicationBuilder().token(token).build()
    
    start_handler = CommandHandler('start', start)
    language_handler = CommandHandler('language', language)
    renewpseudo_handler = CommandHandler('renew_pseudo', renew_pseudo)
    setupmessages_handler = CommandHandler('setup_messages', setup_messages)
    chatid_handler = CommandHandler('chatid', chatid)
    menu_handler = CommandHandler('menu',menu)
    help_handler = CommandHandler('help', help)
    unban_handler = CommandHandler('unban', unban)
    all_handler = MessageHandler(filters.ALL & (~filters.COMMAND), handle_all)

    replybutton_handler = CallbackQueryHandler(handle_at_reply_callback, pattern='^at-reply-.*')
    confirmsendingbutton_handler = CallbackQueryHandler(handle_at_confirm_sending_callback, pattern='^at-confirm-sending$')
    cancelsendingbutton_handler = CallbackQueryHandler(handle_at_cancel_sending_callback, pattern='^at-cancel-sending$')
    blockbutton_handler = CallbackQueryHandler(handle_at_block, pattern='^at-block-.*')
    languagebutton_handler = CallbackQueryHandler(handle_lang_callback, pattern='^lang-.*')
    messagesbutton_handler = CallbackQueryHandler(handle_setup_messages_callback, pattern='^message-.*')
    renewbutton_handler = CallbackQueryHandler(handle_renew_callback, pattern='^renew.*')
    unbanbutton_handler = CallbackQueryHandler(handle_unban, pattern='^unban.*')

    application.add_handler(start_handler)
    application.add_handler(chatid_handler)
    application.add_handler(renewpseudo_handler)
    application.add_handler(language_handler)
    application.add_handler(setupmessages_handler)
    application.add_handler(help_handler)
    application.add_handler(unban_handler)
    application.add_handler(all_handler)
    application.add_handler(unbanbutton_handler)
    application.add_handler(replybutton_handler)
    application.add_handler(confirmsendingbutton_handler)
    application.add_handler(cancelsendingbutton_handler)
    application.add_handler(blockbutton_handler)
    application.add_handler(languagebutton_handler)
    application.add_handler(messagesbutton_handler)
    application.add_handler(renewbutton_handler)
    application.add_handler(menu_handler)

    #application.add_error_handler(error_handler)

    if webhook == "True":
        if webserver == "True":
            application.run_webhook(
                listen='127.0.0.1',
                port=port,
                url_path=url_path,
                secret_token=secret_token,
                cert=certpath,
                webhook_url=mainurl + "/" + url_path
            )
        else:
            application.run_webhook(
                listen='0.0.0.0',
                port = port,
                secret_token=secret_token,
                key=keypath,
                cert=certpath,
                webhook_url=mainurl + ':' + str(port))
    else:
        application.run_polling(poll_interval=1,timeout=60)

if __name__ == '__main__':
    main()