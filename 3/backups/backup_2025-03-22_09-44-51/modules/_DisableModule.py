from discord.ext import commands


def command_disabled():
    async def predicate(ctx):
        raise commands.DisabledCommand("This command is currently disabled.")

    return commands.check(predicate)


def command_disabled_broken():
    async def predicate(ctx):
        raise commands.DisabledCommand(
            "This command has been automatically disabled due to a bot error."
        )

    return commands.check(predicate)
