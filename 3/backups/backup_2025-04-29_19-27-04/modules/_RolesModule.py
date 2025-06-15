import discord
from discord.ext import commands

def isGuildAdministrator(user_id: int, guild: discord.Guild) -> bool:
    member = guild.get_member(user_id)
    if not member:
        return False
    return member.guild_permissions.administrator


def has_role_id(member: discord.Member, role_id: int) -> bool:
    return any(role.id == role_id for role in member.roles)


def roleLocked(role_name: str, role_id: int):
    def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name=role_name)
        if role:
            return True

        role = discord.utils.get(ctx.author.roles, id=role_id)
        if role:
            return True

        raise commands.MissingPermissions([f"Role '{role_name}' or ID '{role_id}' required"])
    return commands.check(predicate)