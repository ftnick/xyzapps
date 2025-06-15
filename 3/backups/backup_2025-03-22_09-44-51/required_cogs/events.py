import discord
import difflib
import config
from discord.ext import commands
from modules._LoggerModule import setup_logging
from modules._ReplyModule import reply
import sys
import platform
import time

logger = setup_logging(__name__)
logger.debug(f"imported, id: {id(sys.modules[__name__])}")

def main(bot):
    @bot._event()
    async def on_connect():
        logger.info("Connected To Discord Servers")

    @bot._event()
    async def on_disconnect():
        logger.warning("Disconnected From Discord Servers")

    @bot._event()
    async def on_ready():
        logger.info(f"Logged in as {bot.user.name} ({bot.user.id})")
        logger.info(f"Bot latency: {bot.latency:.3f}s")
        logger.info(f"Bot version: {config.VERSION}")
        logger.info(f"discord.py API version: {discord.__version__}")
        logger.info(f"Python version: {platform.python_version()}")

        activity = discord.Activity(type=discord.ActivityType.listening, name="?cmds")
        await bot.change_presence(status=discord.Status.online, activity=activity)

        logger.info("Bot is ready!")

    @bot._event()
    async def on_error(event, *args, **kwargs):
        logger.exception(
            f"Unhandled error in event '{event}': args={args}, kwargs={kwargs}"
        )

    @bot._event()
    async def on_command_completion(context) -> None:
        """
        Executed every time a normal command has been successfully executed.
        """
        full_command_name = context.command.qualified_name
        executed_command = full_command_name.split(" ")[0]
        if context.guild is not None:
            logger.info(
                f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) "
                f"by {context.author} (ID: {context.author.id})"
            )
        else:
            logger.info(
                f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs"
            )

    @bot._event()
    async def on_command_error(ctx, error) -> None:
        """
        Global error handler for commands.
        """
        if isinstance(error, commands.CommandOnCooldown):
            logger.warning(
                f"{ctx.author} triggered a CommandOnCooldown for '{ctx.invoked_with}'; retry after {error.retry_after:.2f}s"
            )
            retry_timestamp = int(time.time() + error.retry_after)
            await reply(
                ctx,
                "Command On Cooldown",
                f"**Please slow down** - You can use this command again  <t:{retry_timestamp}:R>.",
            )

        elif isinstance(error, commands.DisabledCommand):
            logger.warning(
                f"{ctx.author} attempted a disabled command: '{ctx.invoked_with}'"
            )
            await reply(ctx, "Disabled Command", "This command has been disabled.")

        elif isinstance(error, commands.MissingRequiredArgument):
            logger.warning(
                f"{ctx.author} triggered MissingRequiredArgument in '{ctx.invoked_with}': {error}"
            )
            await reply(
                ctx,
                "Missing Required Argument(s)",
                f"Usage: ?{ctx.invoked_with} {ctx.command.signature}",
            )

        elif isinstance(error, commands.MissingRole):
            logger.warning(
                f"{ctx.author} triggered MissingRole in '{ctx.invoked_with}': {error}"
            )
            await reply(
                ctx,
                "Missing Role",
                f"You are missing the required role: `{error.missing_role}`.",
            )

        elif isinstance(error, commands.MissingAnyRole):
            logger.warning(
                f"{ctx.author} triggered MissingAnyRole in '{ctx.invoked_with}': {error}"
            )
            await reply(
                ctx,
                "Missing Roles",
                f"You are missing the required roles: `{', '.join(error.missing_roles)}`.",
            )

        elif isinstance(error, commands.NotOwner):
            if ctx.guild:
                logger.warning(
                    f"{ctx.author} (ID: {ctx.author.id}) attempted an owner-only command in "
                    f"{ctx.guild.name} (ID: {ctx.guild.id}), but is not an owner."
                )
            else:
                logger.warning(
                    f"{ctx.author} (ID: {ctx.author.id}) attempted an owner-only command in DMs, "
                    "but is not an owner."
                )
            await reply(
                ctx,
                "Not Owner",
                "Failed to run command, you are not the owner of the bot.",
            )

        elif isinstance(error, commands.MissingPermissions):
            logger.warning(
                f"{ctx.author} triggered MissingPermissions in '{ctx.invoked_with}': {error}"
            )
            await reply(
                ctx,
                "Missing Permissions",
                "You are missing the permission(s): "
                f"`{', '.join(error.missing_permissions)}` to execute this command!",
            )

        elif isinstance(error, commands.CommandNotFound):
            logger.warning(
                f"{ctx.author} triggered CommandNotFound: '{ctx.invoked_with}'"
            )
            attempted = ctx.invoked_with

            # Build a set of all available command names and their aliases
            available_commands = set()
            for cmd in bot.commands:
                available_commands.add(cmd.name)
                available_commands.update(cmd.aliases)

            # Find close matches using difflib
            suggestions = difflib.get_close_matches(attempted, list(available_commands))
            if suggestions:
                suggestion_text = (
                    f"Command not found. Did you mean: {', '.join(suggestions)}?"
                )
            else:
                suggestion_text = (
                    "Command not found. Please check the command and try again."
                )

            await reply(ctx, "Command Not Found", suggestion_text)

        else:
            logger.error(f"Unhandled error by {ctx.author}: {error}")
            raise error
