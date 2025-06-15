import discord
from discord.ext import commands
import json
import os
import sys
from modules._LoggerModule import setup_logging
from modules._ReplyModule import reply

logger = setup_logging(__name__)
logger.debug(f"imported, id: {id(sys.modules[__name__])}")

# Ensure the data folder exists.
data_folder = os.path.join(os.path.realpath(os.path.dirname(__file__)), "..", "data")

# Build the file path in a cross-platform way.
afk_file = os.path.join(data_folder, "afk.json")


def load_afk():
    if os.path.exists(afk_file):
        try:
            with open(afk_file, "r") as f:
                data = json.load(f)
            # JSON stores keys as strings; convert them back to ints.
            return {int(user_id): reason for user_id, reason in data.items()}
        except Exception as e:
            logger.exception(f"Error loading {afk_file}: {e}")
            return {}
    else:
        return {}


def save_afk():
    try:
        with open(afk_file, "w") as f:
            # Convert keys to strings so JSON can serialize them.
            json.dump(
                {str(user_id): reason for user_id, reason in afk_users.items()},
                f,
                indent=4,
            )
    except Exception as e:
        logger.exception(f"Error saving {afk_file}: {e}")


# Load the current AFK statuses.
afk_users = load_afk()


def main(bot):
    @bot.command(name="afk")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def afk(ctx, *, reason: str = "AFK"):
        """
        Set your AFK status with an optional reason.
        Usage: ?afk [reason]
        """
        afk_users[ctx.author.id] = reason
        save_afk()
        await reply(ctx, None, f"{ctx.author.mention} is now AFK: {reason}")

    @bot._event()
    async def on_message(message):
        # Ignore messages from bots.
        if message.author.bot:
            return

        # If the message author was marked as AFK, remove their status.
        if message.author.id in afk_users:
            afk_users.pop(message.author.id)
            save_afk()
            try:
                await reply(
                    message,
                    None,
                    f"Welcome back, {message.author.mention}! Your AFK status has been removed.",
                    delete_after=5,
                )
            except discord.Forbidden:
                logger.warning(
                    f"Cannot send message in {message.channel} due to missing permissions."
                )

        # Check if any mentioned users are AFK and notify the sender.
        for user in message.mentions:
            if user.id in afk_users:
                reason = afk_users[user.id]
                await reply(
                    message,
                    None,
                    f"{user.mention} is currently AFK: {reason}",
                    delete_after=5,
                )
