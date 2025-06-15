import discord
import json
import os
import sys
import config
from modules._LoggerModule import setup_logging
from modules._ReplyModule import reply

logger = setup_logging(__name__)
logger.debug(f"imported, id: {id(sys.modules[__name__])}")

user_channels = {}
USER_CHANNELS_FILE = (
    f"{os.path.realpath(os.path.dirname(__file__))}\\..\\data\\user_channels.json"
)

def save_user_channels():
    """Save the user_channels dictionary to a file."""
    try:
        # Convert integer keys back to strings when saving
        with open(USER_CHANNELS_FILE, "w") as f:
            json.dump(
                {str(key): value for key, value in user_channels.items()}, f, indent=4
            )
        logger.info("user_channels saved to file.")
    except Exception as e:
        logger.error(f"Error saving user_channels: {e}")


def load_user_channels():
    """Load the user_channels dictionary from a file."""
    global user_channels
    if os.path.exists(USER_CHANNELS_FILE):
        try:
            with open(USER_CHANNELS_FILE, "r") as f:
                # Convert string keys to integers
                user_channels = {int(key): value for key, value in json.load(f).items()}
            logger.info("user_channels loaded from file.")
        except Exception as e:
            logger.error(f"Error loading user_channels: {e}")
    else:
        logger.info("No saved user_channels file found.")


def is_owner_or_moderator(ctx):
    """Helper to check if the command invoker is the owner or a shared moderator."""
    # Use ctx.channel.id as an integer (since user_channels keys are integers)
    info = user_channels.get(ctx.channel.id)

    if info is None:
        logger.error(f"Channel {ctx.channel.id} not found in user_channels.")
        return False

    logger.info(
        f"Checking ownership. ctx.author.id: {ctx.author.id}, owner: {info['owner']}"
    )
    return int(ctx.author.id) == int(info["owner"]) or int(ctx.author.id) in map(
        int, info.get("moderators", [])
    )


def main(bot):

    load_user_channels()

    logger.debug(f"user_channels: {user_channels}")

    # ---------------- VC Control Events ----------------

    @bot._event()
    async def on_voice_state_update(member, before, after):
        logger.debug(
            f"Voice state update: member={member}, before={before.channel}, after={after.channel}"
        )
        if after.channel is not None and after.channel.name == "Create VC":
            guild = member.guild
            category = guild.get_channel(1337962706765873237)

            for info in user_channels.values():
                if info["owner"] == member.id:
                    existing_vc = guild.get_channel(info["voice_channel_id"])
                    if existing_vc:
                        # Move the user back to their existing VC
                        await member.move_to(existing_vc)
                        await member.send(
                            f"You already have a VC in *{guild}*: **{existing_vc.name}**. You were prevented from creating a new one and moved back to your existing one."
                        )
                        logger.debug(
                            f"Prevented duplicate VC creation and moved {member.display_name} back to their existing VC: {existing_vc.name}"
                        )
                    return  # Stop execution to prevent duplicate VC creation

            # Create a new voice channel for the member.
            new_voice = await guild.create_voice_channel(
                name=f"{member.display_name}'s VC", category=category
            )
            logger.info(f"Created new voice channel: {new_voice.name}")

            # Create a new text channel for VC control.
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                member: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True
                ),
            }
            new_text = await guild.create_text_channel(
                name=f"{member.display_name}-control",
                category=category,
                overwrites=overwrites,
            )
            logger.info(f"Created new text channel: {new_text.name}")

            embed = discord.Embed(
                title="Welcome to your new VC channel!",
                description=(
                    f"{member.mention}, you can use the following commands to manage your channel:\n\n"
                    f"• `{config.PREFIX}lockvc`: Locks your VC channel (denies @everyone connect).\n"
                    f"• `{config.PREFIX}unlockvc`: Unlocks your VC channel (restores @everyone connect permission).\n"
                    f"• `{config.PREFIX}removevc @member`: Removes a specified member from your VC channel.\n"
                    f"• `{config.PREFIX}renamevc new_name`: Renames your VC channel.\n"
                    f"• `{config.PREFIX}setlimitvc limit`: Sets a user limit for your VC channel.\n"
                    f"• `{config.PREFIX}muteallvc`: Mutes all members in your VC channel (except owner and shared moderators).\n"
                    f"• `{config.PREFIX}deafenallvc`: Deafens all members in your VC channel (except owner and shared moderators).\n"
                    f"• `{config.PREFIX}sharevc @member`: Grants control permissions to another user for your VC channel.\n"
                    f"• `{config.PREFIX}unsharevc @member`: Revokes control permissions from a previously shared user.\n"
                    f"• `{config.PREFIX}closevc`: Closes your VC channel and deletes the text and voice channels.\n"
                ),
                color=discord.Color.from_rgb(0, 0, 0),
            )
            await new_text.send(member.mention, embed=embed)

            await member.move_to(new_voice)
            logger.info(f"Moved member {member.display_name} to new voice channel")

            user_channels[new_text.id] = {
                "owner": member.id,
                "voice_channel_id": new_voice.id,
                "text_channel_id": new_text.id,
                "guild_id": guild.id,
                "moderators": [],
            }

            save_user_channels()

        for text_channel_id, info in list(user_channels.items()):
            if info["guild_id"] != member.guild.id:
                continue
            vc = member.guild.get_channel(info["voice_channel_id"])
            if vc is not None and len(vc.members) == 0:
                tc = member.guild.get_channel(info["text_channel_id"])
                if tc is not None:
                    await tc.delete(reason="Cleanup: VC is empty")
                    logger.info(f"Deleted text channel {tc.name} due to empty VC")
                await vc.delete(reason="Cleanup: VC is empty")
                logger.info(f"Deleted voice channel {vc.name} due to empty VC")
                del user_channels[text_channel_id]

        save_user_channels()

    # ---------------- VC Control Commands ----------------

    @bot.command()
    async def lockvc(ctx):
        """Locks your VC channel (denies @everyone connect)."""
        logger.debug(f"lockvc command invoked by {ctx.author}")

        if ctx.channel.id not in user_channels:
            return await reply(ctx, None, "This is not a VC control channel.")
        if not is_owner_or_moderator(ctx):
            return await reply(
                ctx, None, "You are not authorized to perform this action."
            )

        guild = ctx.guild
        info = user_channels[ctx.channel.id]
        vc = guild.get_channel(info["voice_channel_id"])
        if not vc:
            return await reply(ctx, None, "Voice channel not found.")

        overwrite = vc.overwrites_for(guild.default_role)
        overwrite.connect = False
        await vc.set_permissions(guild.default_role, overwrite=overwrite)
        await reply(ctx, None, "Voice channel locked.")
        logger.info(f"Voice channel {vc.name} locked by {ctx.author}")

        save_user_channels()

    @bot.command()
    async def unlockvc(ctx):
        """Unlocks your VC channel (restores @everyone connect permission)."""
        logger.debug(f"unlockvc command invoked by {ctx.author}")

        if ctx.channel.id not in user_channels:
            return await reply(ctx, None, "This is not a VC control channel.")
        if not is_owner_or_moderator(ctx):
            return await reply(
                ctx, None, "You are not authorized to perform this action."
            )

        guild = ctx.guild
        info = user_channels[ctx.channel.id]
        vc = guild.get_channel(info["voice_channel_id"])
        if not vc:
            return await reply(ctx, None, "Voice channel not found.")

        overwrite = vc.overwrites_for(guild.default_role)
        overwrite.connect = None
        await vc.set_permissions(guild.default_role, overwrite=overwrite)
        await reply(ctx, None, "Voice channel unlocked.")
        logger.info(f"Voice channel {vc.name} unlocked by {ctx.author}")

        save_user_channels()

    @bot.command()
    async def removevc(ctx, member: discord.Member):
        """Removes a specified member from your VC channel."""
        logger.debug(f"removevc command invoked by {ctx.author} for member {member}")

        if ctx.channel.id not in user_channels:
            return await reply(ctx, None, "This is not a VC control channel.")
        if not is_owner_or_moderator(ctx):
            return await reply(
                ctx, None, "You are not authorized to perform this action."
            )

        guild = ctx.guild
        info = user_channels[ctx.channel.id]
        vc = guild.get_channel(info["voice_channel_id"])
        if not vc:
            return await reply(ctx, None, "Voice channel not found.")

        if member not in vc.members:
            return await reply(
                ctx, None, f"{member.display_name} is not in your voice channel."
            )

        try:
            await member.move_to(None)
            await reply(
                ctx,
                None,
                f"{member.display_name} has been removed from the voice channel.",
            )
            logger.info(f"Removed {member.display_name} from voice channel {vc.name}")
        except Exception as e:
            await reply(
                ctx, None, "An error occurred while trying to remove the member."
            )
            logger.error(
                f"Error removing {member.display_name} from voice channel: {e}"
            )

        save_user_channels()

    @bot.command()
    async def renamevc(ctx, *, new_name: str):
        """Renames your VC channel."""
        logger.debug(
            f"renamevc command invoked by {ctx.author} with new name {new_name}"
        )

        if ctx.channel.id not in user_channels:
            return await reply(ctx, None, "This is not a VC control channel.")
        if not is_owner_or_moderator(ctx):
            return await reply(
                ctx, None, "You are not authorized to perform this action."
            )

        guild = ctx.guild
        info = user_channels[ctx.channel.id]
        vc = guild.get_channel(info["voice_channel_id"])
        if not vc:
            return await reply(ctx, None, "Voice channel not found.")

        try:
            await vc.edit(name=new_name)
            await reply(ctx, None, f"Voice channel renamed to **{new_name}**.")
            logger.info(
                f"Voice channel {vc.name} renamed to {new_name} by {ctx.author}"
            )
        except Exception as e:
            await reply(ctx, None, "An error occurred while renaming the channel.")
            logger.error(f"Error renaming voice channel: {e}")

        save_user_channels()

    @bot.command()
    async def setlimitvc(ctx, limit: int):
        """Sets a user limit for your VC channel."""
        logger.debug(f"setlimitvc command invoked by {ctx.author} with limit {limit}")

        if ctx.channel.id not in user_channels:
            return await reply(ctx, None, "This is not a VC control channel.")
        if not is_owner_or_moderator(ctx):
            return await reply(
                ctx, None, "You are not authorized to perform this action."
            )
        if limit < 0:
            return await reply(ctx, None, "User limit must be zero or positive.")

        guild = ctx.guild
        info = user_channels[ctx.channel.id]
        vc = guild.get_channel(info["voice_channel_id"])
        if not vc:
            return await reply(ctx, None, "Voice channel not found.")

        try:
            await vc.edit(user_limit=limit)
            await reply(ctx, None, f"Voice channel user limit set to {limit}.")
            logger.info(
                f"Voice channel {vc.name} user limit set to {limit} by {ctx.author}"
            )
        except Exception as e:
            await reply(ctx, None, "An error occurred while setting the user limit.")
            logger.error(f"Error setting user limit for voice channel: {e}")

    @bot.command()
    async def closevc(ctx):
        logger.debug(f"closevc command invoked by {ctx.author}")

        if ctx.channel.id not in user_channels:
            return await reply(ctx, None, "This is not a VC control channel.")
        if not is_owner_or_moderator(ctx):
            return await reply(
                ctx, None, "You are not authorized to perform this action."
            )

        guild = ctx.guild
        info = user_channels[ctx.channel.id]
        vc = guild.get_channel(info["voice_channel_id"])
        tc = guild.get_channel(info["text_channel_id"])

        # Inform the user before shutting down.
        await reply(ctx, None, "Shutting down your VC channel...")

        # Attempt deletion of both channels.
        try:
            if vc:
                await vc.delete(reason="Manual shutdown")
                logger.info(f"Deleted voice channel {vc.name} due to manual shutdown")
            if tc:
                await tc.delete(reason="Manual shutdown")
                logger.info(f"Deleted text channel {tc.name} due to manual shutdown")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

        # Remove mapping.
        del user_channels[ctx.channel.id]

        save_user_channels()
