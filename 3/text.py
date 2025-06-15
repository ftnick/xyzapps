import discord
from discord.ext import commands


class Lockdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def modify_channels(self, ctx, lock: bool):
        """Helper function to lock/unlock all text channels with an embedded message for community members."""
        guild = ctx.guild
        action = (
            "🔒 Full Server Lockdown Enabled" if lock else "🔓 Server Lockdown Lifted"
        )
        color = discord.Color.red() if lock else discord.Color.green()
        reason = (
            "Server is under lockdown."
            if lock
            else "Lockdown lifted. Channels are open again."
        )

        embed = discord.Embed(
            title=action,
            description=(
                "The server has been placed under **full lockdown**.\n\n"
                if lock
                else "The server lockdown has been **lifted**."
            ),
            color=color,
        )

        if lock:
            embed.add_field(
                name="❗ What this means:",
                value="• All text channels are **temporarily locked**.\n"
                "• Members **cannot send messages** until further notice.\n"
                "• Please remain patient while the situation is handled.",
                inline=False,
            )
        else:
            embed.add_field(
                name="✅ You Can Now Chat Again!",
                value="• All channels have been **unlocked**.\n"
                "• Please follow server rules as usual.\n"
                "• Thank you for your patience!",
                inline=False,
            )

        embed.set_footer(
            text=f"Action performed by {ctx.author}",
            icon_url=(
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            ),
        )

        for channel in guild.text_channels:
            overwrite = channel.overwrites_for(guild.default_role)
            overwrite.send_messages = (
                None if not lock else False
            )
            await channel.set_permissions(
                guild.default_role, overwrite=overwrite, reason=reason
            )
            await channel.send(embed=embed)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx):
        """Locks all text channels and notifies members (Admins only)."""
        await self.modify_channels(ctx, lock=True)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unlockdown(self, ctx):
        """Unlocks all text channels and notifies members (Admins only)."""
        await self.modify_channels(ctx, lock=False)

    @lockdown.error
    @unlockdown.error
    async def lockdown_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need **Administrator** permissions to use this command.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)


# Setup function to load the cog
async def setup(bot):
    await bot.add_cog(Lockdown(bot))
