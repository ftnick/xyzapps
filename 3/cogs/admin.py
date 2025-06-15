from discord.ext import commands
import sys
from modules._ReplyModule import reply
from modules._LoggerModule import setup_logging
from modules._RolesModule import roleLocked

logger = setup_logging(__name__)
logger.debug(f"imported, id: {id(sys.modules[__name__])}")


def main(bot):
    @bot.command(name="_purge", help="Purge an amount of messages.")
    @roleLocked("developer", 1307619426757120041)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def purge(ctx, amount: int):
        try:
            await ctx.message.delete()

            purged_messages = await ctx.channel.purge(limit=amount + 1)

            await reply(ctx, None, f"Deleted {len(purged_messages)-1} messages.")

        except commands.MissingPermissions as e:
            await reply(
                ctx,
                None,
                f"Error: {ctx.author.mention}, you don't have permission to execute this command. Missing permissions: {e}",
            )

    @bot.command(name="_shutdown", help="Shutdown the bot.")
    @roleLocked("developer", 1307619426757120041)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def shutdown(ctx):
        if ctx.author.id == 701632642822701057:
            await reply(ctx, None, "Shutting down...")
            await bot.close()

        else:
            await reply(
                ctx,
                None,
                "You do not have permission to shut down the bot. (Owner Only)",
            )
