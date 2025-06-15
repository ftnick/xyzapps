import discord
from discord import Embed
import config


async def reply(ctx, Title, Message, *args, **kwargs):
    embed = Embed(
        title=Title,
        description=str(Message),
        color=discord.Color(0),
    )
    embed.set_footer(text=f"feature | {config.VERSION}")
    return await ctx.reply(embed=embed, *args, **kwargs)


async def checkDMsMSG(ctx, commandName: str, Desc: str, *args, **kwargs):
    DMS_embed = Embed(
        title=commandName,
        description=f"Check your DMs {Desc}",
        color=discord.Color(0),
    )
    DMS_embed.set_footer(
        text="Bot isnt DMing you? Make sure you have DMs enabled for this server.",
    )
    return await ctx.reply(embed=DMS_embed, *args, **kwargs)
