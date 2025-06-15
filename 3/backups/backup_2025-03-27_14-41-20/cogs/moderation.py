import discord
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from modules._LoggerModule import setup_logging
from modules._ReplyModule import reply
from modules._RolesModule import roleLocked

logger = setup_logging(__name__)
logger.debug(f"imported, id: {id(sys.modules[__name__])}")

# --- Punishments Persistence ---
PUNISHMENTS_FILE = (
    f"{os.path.realpath(os.path.dirname(__file__))}\\..\\data\\punishments.json"
)

# Load punishments from file (or initialize an empty list)
if os.path.isfile(PUNISHMENTS_FILE):
    try:
        with open(PUNISHMENTS_FILE, "r") as f:
            punishments_data = json.load(f)
    except json.JSONDecodeError:
        punishments_data = []
else:
    punishments_data = []


def save_punishments():
    """Save the current punishments_data to disk."""
    with open(PUNISHMENTS_FILE, "w") as f:
        json.dump(punishments_data, f, indent=4)


def add_punishment(
    user_id, guild_id, punishment_type, reason, duration=None, active=True
):
    """Add a punishment record and save it."""
    record = {
        "user_id": user_id,
        "guild_id": guild_id,
        "punishment_type": punishment_type,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration": duration,  # Duration in seconds (or None)
        "active": active,
    }
    punishments_data.append(record)
    save_punishments()


# --- Main Registration Function ---
def main(bot):
    # --- Timeout Command ---
    @bot.command(name="timeout")
    @roleLocked("discord staff", 1340133492880572416)
    async def timeout(
        ctx, user: discord.Member, duration: int, *, reason: str = "No reason provided"
    ):
        """
        Timeout a user for a specified duration (in seconds).
        Usage: ?timeout @user duration reason
        """
        try:
            until = datetime.now(timezone.utc) + timedelta(seconds=duration)
            await user.timeout(until, reason=reason)
            await reply(
                ctx,
                None,
                f"{user.mention} has been timed out for {duration} seconds. Reason: {reason}",
            )
            add_punishment(
                user.id, ctx.guild.id, "timeout", reason, duration=duration, active=True
            )
            logger.info(
                f"User {user} timed out for {duration} seconds. Reason: {reason}"
            )
        except Exception as e:
            logger.exception(f"Error timing out {user}: {e}")
            await reply(ctx, None, f"Failed to timeout {user.mention}.")

    # --- Revoke Timeout Command ---
    @bot.command(name="revoketimeout")
    @roleLocked("discord staff", 1340133492880572416)
    async def revoketimeout(ctx, user: discord.Member):
        """
        Revoke a user's timeout.
        Usage: ?revoketimeout @user
        """
        try:
            await user.timeout(None, reason="Revoked by moderator")
            await reply(ctx, None, f"Timeout revoked for {user.mention}.")
            # Mark any active timeout punishment records as inactive
            for record in punishments_data:
                if (
                    record["user_id"] == user.id
                    and record["guild_id"] == ctx.guild.id
                    and record["punishment_type"] == "timeout"
                    and record["active"]
                ):
                    record["active"] = False
            save_punishments()
            logger.info(f"Timeout revoked for user {user}.")
        except Exception as e:
            logger.exception(f"Error revoking timeout for {user}: {e}")
            await reply(ctx, None, f"Failed to revoke timeout for {user.mention}.")

    # --- Ban Command ---
    @bot.command(name="ban")
    @roleLocked("discord staff", 1340133492880572416)
    async def ban(ctx, user: discord.Member, *, reason: str = "No reason provided"):
        """
        Ban a user from the server.
        Usage: ?ban @user reason
        """
        try:
            await user.ban(reason=reason)
            await reply(ctx, None, f"{user.mention} has been banned. Reason: {reason}")
            add_punishment(user.id, ctx.guild.id, "ban", reason, active=True)
            logger.info(f"Banned {user} for: {reason}")
        except Exception as e:
            logger.exception(f"Error banning {user}: {e}")
            await reply(ctx, None, f"Failed to ban {user.mention}.")

    # --- Unban Command Using User ID ---
    @bot.command(name="unban")
    @roleLocked("discord staff", 1340133492880572416)
    async def unban(ctx, user_id: int):
        """
        Unban a user using their user ID.
        Usage: ?unban user_id
        """
        try:
            # Convert the async generator into a list
            banned_users = [ban async for ban in ctx.guild.bans()]
            for ban_entry in banned_users:
                if ban_entry.user.id == user_id:
                    await ctx.guild.unban(
                        ban_entry.user, reason="Unban requested by moderator"
                    )
                    await reply(ctx, None, f"<@{ban_entry.user.id}> has been unbanned.")
                    add_punishment(
                        ban_entry.user.id,
                        ctx.guild.id,
                        "unban",
                        "User unbanned",
                        active=False,
                    )
                    logger.info(
                        f"Unbanned {ban_entry.user} as requested by {ctx.author}"
                    )
                    return
            await reply(
                ctx, None, f"User with ID `{user_id}` not found in the banned list."
            )
        except Exception as e:
            logger.exception(f"Error unbanning user with ID {user_id}: {e}")
            await reply(ctx, None, f"Failed to unban user with ID `{user_id}`.")

    # --- Kick Command ---
    @bot.command(name="kick")
    @roleLocked("discord staff", 1340133492880572416)
    async def kick(ctx, user: discord.Member, *, reason: str = "No reason provided"):
        """
        Kick a user from the server.
        Usage: ?kick @user reason
        """
        try:
            await user.kick(reason=reason)
            await reply(ctx, None, f"{user.mention} has been kicked. Reason: {reason}")
            add_punishment(user.id, ctx.guild.id, "kick", reason, active=True)
            logger.info(f"Kicked {user} for: {reason}")
        except Exception as e:
            logger.exception(f"Error kicking {user}: {e}")
            await reply(ctx, None, f"Failed to kick {user.mention}.")

    # --- Warning Command ---
    @bot.command(name="warn")
    @roleLocked("discord staff", 1340133492880572416)
    async def warn(ctx, user: discord.Member, *, reason: str = "No reason provided"):
        """
        Warn a user.
        Usage: ?warn @user reason
        """
        try:
            await reply(ctx, None, f"{user.mention} has been warned. Reason: {reason}")
            add_punishment(user.id, ctx.guild.id, "warning", reason, active=False)
            logger.info(f"Issued warning to {user} for: {reason}")
        except Exception as e:
            logger.exception(f"Error warning {user}: {e}")
            await reply(ctx, None, f"Failed to warn {user.mention}.")

    # --- View Punishments Command ---
    @bot.command(name="punishments")
    @roleLocked("discord staff", 1340133492880572416)
    async def view_punishments(ctx, user: discord.Member = None):
        """
        View the punishment history for a user.
        Usage: ?punishments [@user]
        If no user is mentioned, the command invoker's punishments are shown.
        """
        target = user or ctx.author
        records = [
            record
            for record in punishments_data
            if record["user_id"] == target.id and record["guild_id"] == ctx.guild.id
        ]
        if not records:
            await reply(ctx, None, f"No punishments found for {target.mention}.")
            return

        lines = []
        for rec in records:
            ts = rec["timestamp"]
            p_type = rec["punishment_type"]
            reason = rec["reason"]
            duration = rec["duration"] if rec["duration"] is not None else "N/A"
            active = rec["active"]
            lines.append(
                f"Type: {p_type} | Reason: {reason} | Duration: {duration} | Active: {active} | Time: {ts}"
            )

        # If too many punishments, you might need to paginate. For now, we join them in one message.
        await reply(ctx, None, "\n".join(lines))
