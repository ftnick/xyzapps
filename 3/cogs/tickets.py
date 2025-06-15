import discord
from discord.ext import commands
import os
import json
import sys
from modules._LoggerModule import setup_logging
from modules._ReplyModule import reply
from modules._RolesModule import roleLocked
import time

logger = setup_logging(__name__)
logger.debug(f"imported, id: {id(sys.modules[__name__])}")

# Ensure the data folder exists.
data_folder = os.path.join(os.path.realpath(os.path.dirname(__file__)), "..", "data")
transcripts_folder = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), "..", "data", "transcripts"
)

# Set the ID for the category you want to create the ticket channels in
CATEGORY_ID = 1352524343011442759  # Replace with your category ID
TICKET_FILE = os.path.join(data_folder, "tickets.json")

# Support staff role name (e.g., "Ticket Support")
SUPPORT_ROLE_NAME = "ticket support"


# Load existing ticket data
def load_tickets():
    if os.path.exists(TICKET_FILE):
        try:
            with open(TICKET_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.exception(f"Error loading {TICKET_FILE}: {e}")
            return {}
    return {}


# Save ticket data to file
def save_tickets(tickets):
    try:
        with open(TICKET_FILE, "w") as f:
            json.dump(tickets, f, indent=4)
    except Exception as e:
        logger.exception(f"Error saving {TICKET_FILE}: {e}")


def main(bot):
    tickets = load_tickets()  # Load ticket data at bot startup

    @bot.command(name="ticket")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def ticket(ctx):
        """
        Create a new ticket channel for the user.
        Usage: ?ticket
        """
        guild = ctx.guild
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)

        if not category:
            await reply(ctx, None, "Error: Category for tickets not found!")
            return

        channel_name = f"{ctx.author.name}-ticket"
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)

        if existing_channel:
            await reply(
                ctx,
                None,
                f"You already have an open ticket: {existing_channel.mention}",
            )
            return

        try:
            # Create the channel
            channel = await guild.create_text_channel(channel_name, category=category)

            # Set permissions so only the user and staff can see it
            await channel.set_permissions(
                guild.default_role, view_channel=False
            )  # Hide from everyone
            await channel.set_permissions(
                ctx.author, view_channel=True
            )  # Give user access
            staff_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE_NAME)
            if staff_role:
                await channel.set_permissions(
                    staff_role, view_channel=True
                )  # Allow staff to access

            # Store the ticket information
            tickets[f"id:{str(channel.id)}"] = {
                "user_id": str(ctx.author.id),
                "status": "open",
                "channel_name": channel_name,
            }
            save_tickets(tickets)  # Save the ticket data

            # Create an embed for the ticket
            embed = discord.Embed(
                title="New Ticket Created",
                description=f"Hello {ctx.author.mention}, A staff member will assist you shortly.\n\n**Please describe your issue below.**",
                color=discord.Color.blue(),
            )
            # embed.set_footer(text="Ticket Support will assist you shortly!")

            # Ping the Ticket Support role
            staff_role_mention = staff_role.mention if staff_role else "@everyone"
            await channel.send(
                f"{staff_role_mention} | {ctx.author.mention}", embed=embed
            )

            await reply(ctx, None, f"Your ticket has been created: {channel.mention}")
        except Exception as e:
            logger.exception(f"Error creating ticket channel: {e}")
            await reply(
                ctx,
                None,
                "An error occurred while creating the ticket channel. Please try again later.",
            )

    @bot.command(name="closeticket")
    @roleLocked("ticket support", 1339866256865755137)
    async def close_ticket(ctx):
        """
        Close a ticket and save the transcript.
        This works automatically when run in the ticket channel.
        """
        channel = ctx.channel

        if f"id:{str(channel.id)}" not in tickets:
            await reply(ctx, None, "This channel is not a valid ticket.")
            return

        # Save the transcript to a file
        transcript_path = os.path.join(
            data_folder,
            f"{transcripts_folder}/{str(time.time())}_{channel.name}_transcript.txt",
        )
        os.makedirs(os.path.dirname(transcript_path), exist_ok=True)

        with open(transcript_path, "w") as f:
            # Write the ticket messages to the transcript file
            async for message in channel.history(limit=None):
                f.write(f"{message.author}: {message.content}\n")

        # Mark the ticket as closed and save
        tickets[f"id:{str(channel.id)}"]["status"] = "closed"
        save_tickets(tickets)

        # Close the ticket
        await channel.send("This ticket has been closed. Thank you for reaching out!")
        await channel.delete()
