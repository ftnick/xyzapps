import discord
from discord.ext import commands
import os
import json
import sys
import time
import aiohttp
import asyncio
import base64

import config
from modules._LoggerModule import setup_logging
from modules._ReplyModule import reply
from modules._RolesModule import roleLocked

logger = setup_logging(__name__)
logger.debug(f"imported, id: {id(sys.modules[__name__])}")

# GitHub API settings
GITHUB_API_URL = "https://api.github.com/repos/ftnick/dbTest/contents/"
RATE_LIMIT = 60  # requests per minute


# --- GitHubDatabase Class ---
class GitHubDatabase:
    def __init__(self, token, rate_limit=RATE_LIMIT):
        self.token = token
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.rate_limit = rate_limit
        self.queue = asyncio.Queue()
        self.last_request_time = 0

    async def _rate_limit(self):
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < 60 / self.rate_limit:
            sleep_time = 60 / self.rate_limit - elapsed
            logger.info(f"Rate limiting active. Sleeping for {sleep_time:.2f} seconds.")
            await asyncio.sleep(sleep_time)
        self.last_request_time = time.time()

    async def _request(self, method, url, data=None):
        await self._rate_limit()
        async with aiohttp.ClientSession() as session:
            logger.info(f"Sending {method} request to {url} with data: {data}")
            async with session.request(
                method, url, headers=self.headers, json=data
            ) as response:
                if response.status == 403:
                    retry_after = int(response.headers.get("Retry-After", 1))
                    logger.warning(
                        f"Rate limit exceeded. Retrying after {retry_after} seconds."
                    )
                    await asyncio.sleep(retry_after)
                    return await self._request(method, url, data)
                response_data = await response.json()
                logger.info(f"Response: {response_data}")
                return response_data

    async def get_file_info(self, file_path):
        url = GITHUB_API_URL + file_path
        return await self._request("GET", url)

    async def create_or_update_file(self, file_path, content, message="Update data"):
        file_info = await self.get_file_info(file_path)
        data = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
        }
        if "sha" in file_info:
            data["sha"] = file_info["sha"]
        url = GITHUB_API_URL + file_path
        return await self._request("PUT", url, data)

    async def enqueue_request(self, method, file_path, content, message="Update data"):
        logger.info(f"Enqueuing request: {method} {file_path} with message: {message}")
        await self.queue.put((method, file_path, content, message))
        logger.info(f"Queue size: {self.queue.qsize()}")

    async def process_queue(self):
        while not self.queue.empty():
            method, file_path, content, message = await self.queue.get()
            logger.info(
                f"Processing request: {method} {file_path} with message: {message}"
            )
            if method == "PUT":
                response = await self.create_or_update_file(file_path, content, message)
                logger.info(f"Response: {response}")


# Create a global GitHubDatabase instance
github_db = GitHubDatabase(config.GIT_TOKEN)


# --- Ticket Data via GitHub ---
async def load_tickets_github():
    """Loads the tickets data from GitHub."""
    response = await github_db.get_file_info("tickets.json")
    if response.get("message") == "Not Found":
        logger.info("tickets.json not found on GitHub. Initializing empty tickets.")
        return {}
    try:
        content = base64.b64decode(response["content"]).decode()
        tickets = json.loads(content)
        logger.info("Loaded tickets from GitHub.")
        return tickets
    except Exception as e:
        logger.exception(f"Error parsing tickets.json from GitHub: {e}")
        return {}


async def update_github_tickets(tickets):
    """Updates the tickets file on GitHub."""
    content = json.dumps(tickets, indent=4)
    response = await github_db.create_or_update_file(
        "tickets.json", content, "Update tickets"
    )
    logger.info(f"Updated GitHub tickets file: {response}")


# --- Discord Ticket System ---
# Transcripts are still stored locally.
data_folder = os.path.join(os.path.realpath(os.path.dirname(__file__)), "..", "data")
transcripts_folder = os.path.join(data_folder, "transcripts")

# Set the ID for the category where ticket channels are created
CATEGORY_ID = 1352524343011442759  # Replace with your category ID

# Support staff role name (e.g., "Ticket Support")
SUPPORT_ROLE_NAME = "ticket support"


def main(bot):
    @bot.command(name="ticket")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def ticket(ctx):
        """
        Create a new ticket channel for the user.
        Usage: ?ticket
        """
        # Load tickets from GitHub
        tickets = await load_tickets_github()

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
            # Create the ticket channel
            channel = await guild.create_text_channel(channel_name, category=category)
            # Set permissions so that only the user and staff can view it
            await channel.set_permissions(guild.default_role, view_channel=False)
            await channel.set_permissions(ctx.author, view_channel=True)
            staff_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE_NAME)
            if staff_role:
                await channel.set_permissions(staff_role, view_channel=True)

            # Update tickets stored on GitHub
            tickets[f"id:{str(channel.id)}"] = {
                "user_id": str(ctx.author.id),
                "status": "open",
                "channel_name": channel_name,
            }
            await update_github_tickets(tickets)

            # Create an embed to welcome the user in the ticket channel
            embed = discord.Embed(
                title="New Ticket Created",
                description=(
                    f"Hello {ctx.author.mention}, a staff member will assist you shortly.\n\n"
                    "**Please describe your issue below.**"
                ),
                color=discord.Color.blue(),
            )
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
        # Load tickets from GitHub
        tickets = await load_tickets_github()
        channel = ctx.channel

        if f"id:{str(channel.id)}" not in tickets:
            await reply(ctx, None, "This channel is not a valid ticket.")
            return

        # Save the transcript locally
        transcript_path = os.path.join(
            transcripts_folder, f"{str(time.time())}_{channel.name}_transcript.txt"
        )
        os.makedirs(os.path.dirname(transcript_path), exist_ok=True)
        with open(transcript_path, "w") as f:
            async for message in channel.history(limit=None):
                f.write(f"{message.author}: {message.content}\n")

        # Mark the ticket as closed and update GitHub
        tickets[f"id:{str(channel.id)}"]["status"] = "closed"
        await update_github_tickets(tickets)

        # Notify and delete the ticket channel
        await channel.send("This ticket has been closed. Thank you for reaching out!")
        await channel.delete()
