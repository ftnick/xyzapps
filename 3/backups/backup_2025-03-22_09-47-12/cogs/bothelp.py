import os  # noqa: E402
import discord  # noqa: E402
from discord.ext import commands  # noqa: E402
from discord import Embed  # noqa: E402
import importlib  # For dynamic imports
import config
import inspect
from modules._LoggerModule import setup_logging
from modules._bot import Bot
import sys

logger = setup_logging(__name__)
logger.debug(f"imported, id: {id(sys.modules[__name__])}")


def get_command_info_from_scripts(commands_folder: str):
    command_info = {}
    logger.debug(f"Scanning folder: {commands_folder}")
    for file in os.listdir(commands_folder):
        logger.debug(f"Checking file: {file}")
        if file.endswith(".py") and not file.startswith("_"):
            module_name = f"{commands_folder}.{file[:-3]}"
            logger.debug(f"Importing module: {module_name}")
            try:
                module = importlib.import_module(module_name)
            except Exception as e:
                logger.exception(f"Failed to import {module_name}: {e}")
                continue
            if hasattr(module, "main"):
                logger.debug(f"Found main function in module: {module_name}")
                temp_bot = Bot(command_prefix="!", intents=discord.Intents.default())
                try:
                    main_function = getattr(module, "main")
                    main_function(temp_bot)
                except Exception as e:
                    logger.exception(f"Failed to execute main in {module_name}: {e}")
                    continue
                commands_in_module = []
                for command in temp_bot.commands:
                    if command.name == "help":
                        continue
                    commands_in_module.append(
                        {
                            "name": f"{config.PREFIX}{command.name}",
                            "aliases": (
                                ", ".join(command.aliases) if command.aliases else ""
                            ),
                        }
                    )
                if commands_in_module:
                    command_info[module_name] = commands_in_module
    logger.debug("Command info extraction complete.")
    return command_info


def main(bot):
    @bot.command(name="cmds", help="Lists all bot commands dynamically.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def cmds(ctx):
        command_info = get_command_info_from_scripts("cogs")
        embed = Embed(
            title="Available Commands",
            description="Use `?Help <command>` for more details on a specific command.",
            color=discord.Color(0),
        )
        for module, cmds_in_module in command_info.items():
            command_list = "\n".join(
                [
                    f"`{command['name']}`{' (' + command['aliases'] + ')' if command['aliases'] else ''}"
                    for command in cmds_in_module
                ]
            )
            embed.add_field(
                name=f"{module.replace('cogs.', '')}",
                value=command_list or "No commands found.",
                inline=False,
            )
        DMS_embed = Embed(
            title="?cmds",
            description="Check your DMs for the list of commands.",
            color=discord.Color(0),
        )
        DMS_embed.set_footer(
            text="Bot isn't DMing you? Enable DMs for this server.",
        )
        await ctx.reply(embed=DMS_embed)
        await ctx.author.send(embed=embed)

    @bot.command(name="Help", help="Get more information about a specific command.")
    async def help_command(ctx, command_name: str):
        command = bot.get_command(command_name)
        if command:
            # Extracting the signature of the target command (not the help command)
            signature = inspect.signature(command.callback)
            params = [str(param) for param in signature.parameters.values()]
            usage = " ".join(params)

            embed = Embed(
                title=f"Help for `{command_name}`",
                description=command.help or "No description provided.",
                color=discord.Color.blue(),
            )

            # Adding the aliases and usage
            embed.add_field(
                name="Aliases", value=", ".join(command.aliases) or "None", inline=False
            )
            embed.add_field(
                name="Usage",
                value=f"`{config.PREFIX}{command_name} {usage}`"
                or "No usage information.",
                inline=False,
            )

            await ctx.reply(embed=embed)
        else:
            await ctx.reply(f"No command named `{command_name}` found.")