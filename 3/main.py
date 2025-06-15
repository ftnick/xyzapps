import os

os.system("cls")
from modules._bot import Bot  # noqa: E402
import discord  # noqa: E402
import asyncio  # noqa: E402
import importlib  # noqa: E402
import config  # noqa: E402
from main_register import Register, registrationResults, errorFlip  # noqa: E402
from modules._LoggerModule import setup_logging  # noqa: E402
from modules._HookManager import HookManager  # noqa: E402
from utilities import censor_string, fetch_version, aCD  # noqa: E402
from suer import CrashHandler  # noqa: E402

hook_manager = HookManager()
hook_manager.load_plugins("plugins")
hook_manager.execute_hooks("pre_init")
logger = setup_logging("main_core")

logger.info("Checking versions...")
LOCAL_APP_VERSION = str(config.VERSION)
ONLINE_APP_VERSION = fetch_version()
if ONLINE_APP_VERSION:
    if LOCAL_APP_VERSION != ONLINE_APP_VERSION:
        logger.warning(
            f"Local version ({LOCAL_APP_VERSION}) does not match online version ({ONLINE_APP_VERSION})."
        )
        aCD(5, "Continuing...")
    else:
        logger.info(f"Local version ({LOCAL_APP_VERSION}) matches online version.")
else:
    raise CrashHandler(SystemExit("Warning: Failed online app version "), __file__)

logger.info("Setting Up Intents")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.moderation = True
intents.reactions = True

logger.info("Setting Up Config")

if not os.path.isfile(f"{os.path.realpath(os.path.dirname(__file__))}/config.py"):
    logger.critical("'config.py' not found! Please add it and try again.")
    raise SystemExit(1)
else:
    with open(f"{os.path.realpath(os.path.dirname(__file__))}/config.py") as file:
        import config

logger.info("Setting Up Prefix And Bot Const")

DEFAULT_PREFIX = str(config.PREFIX) or "?"
OWNERSHIP_PREFIX = str(config.OWNERSHIP_PREFIX) or DEFAULT_PREFIX


async def get_prefix(bot, message):
    if message.content.startswith(OWNERSHIP_PREFIX):
        return OWNERSHIP_PREFIX
    return DEFAULT_PREFIX


bot = Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None,
    case_insensitive=True,
)

logger.info("Registering Commands Dynamically")


def register_commands(commands_folder: str):
    for file in os.listdir(commands_folder):
        if file.endswith(".py"):
            if not file.startswith("_"):
                logger.debug(f"Pre-registering {file}...")
                module_name = f"{commands_folder}.{file[:-3]}"  # Remove .py extension
                module = importlib.import_module(module_name)
                if hasattr(module, "main"):
                    setup_function = getattr(module, "main")
                    Register(file[:-3].capitalize(), setup_function, bot)
            else:
                logger.debug(f"Skipping {file} as it is a private module (_ prefix)")
        else:
            logger.debug(f"Skipping {file} as it is not a .py file (.py expected)")


register_commands("required_cogs")
register_commands("cogs")
registrationResults()
Errored, Error = errorFlip()
if Errored:
    logger.critical("Errors occurred during registration.")
    raise CrashHandler(Error, __file__)

TOKEN = str(config.BOT_TOKEN) or "TOKEN_NOT_FOUND"
if not TOKEN:
    raise ValueError("Bot token not found in config.py file.")


hook_manager.execute_hooks("post_init")


@bot.event
async def on_message(message):
    await bot.process_commands(message)


async def validate_token(token):
    client = discord.Client(intents=intents)

    @client.event
    async def on_connect():
        logger.info(f"Validating b-token: {censor_string(token)}")

    @client.event
    async def on_ready():
        logger.info(f"Validate confirmed for b-token: {censor_string(token)}")
        logger.debug(f"Client User: {censor_string(str(client.user))}")
        logger.debug(f"Client User ID: {censor_string(str(client.user.id))}")
        logger.debug(f"Client Latency: {client.latency}")
        logger.debug(f"Client Intents: {client.intents}")
        await client.close()

    try:
        await client.start(token)
    except discord.errors.LoginFailure:
        logger.critical("Invalid bot token")
        raise SystemError("Invalid bot token")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")


async def main():
    # await validate_token(TOKEN)
    await bot.start(TOKEN)
    os._exit(0)


if __name__ == "__main__":
    hook_manager.execute_hooks("pre_runtime")
    asyncio.run(main())
    hook_manager.execute_hooks("post_runtime")
