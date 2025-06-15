import os  # noqa: E402
import re
import string
import requests
import discord
from discord.ext import commands
import time
import sys
from modules._ReplyModule import reply, checkDMsMSG
from modules._LoggerModule import setup_logging

logger = setup_logging(__name__)
logger.debug(f"{__name__} imported, id: {id(sys.modules[__name__])}")


def download_xml(clothing_id):
    url = f"https://assetdelivery.roblox.com/v1/asset/?id={clothing_id}"
    response = requests.get(url)

    if response.status_code == 200:
        # Create a directory named 'xml_temp' if it doesn't exist
        if not os.path.exists("logs/xml_temp"):
            os.mkdir("logs/xml_temp")

        with open(f"logs/xml_temp/{clothing_id}.xml", "wb") as file:
            file.write(response.content)
        logger.debug(f"Successfully downloaded temporary file: {clothing_id}.xml")
    else:
        logger.error(f"Failed to download temporary file: {clothing_id}")


def extract_new_id(xml_file_path):
    with open(xml_file_path, "r") as file:
        xml_content = file.read()

    # Use regex to extract the new ID from the <url> tag
    match = re.search(r"<url>.*\?id=(\d+)</url>", xml_content)
    if match:
        return match.group(1)
    else:
        return None


# Function to sanitize a string
def sanitize_filename(name):
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    return "".join(char for char in name if char in valid_chars)


# Function to avoid overwriting
def add_suffix_if_exists(file_name):
    base_name, ext = os.path.splitext(file_name)
    index = 1
    while os.path.exists(file_name):
        file_name = f"{base_name}_{index}{ext}"
        index += 1
    return file_name


def download_clothing_image(clothing_id, new_id):
    item_name = clothing_id
    item_name = sanitize_filename(item_name)
    file_name = f"data/clothes/{item_name}.png"
    file_name = add_suffix_if_exists(file_name)

    url = f"https://assetdelivery.roblox.com/v1/asset/?id={new_id}"
    response = requests.get(url)

    if response.status_code == 200:
        # Create a directory named 'clothes' if it doesn't exist
        if not os.path.exists("data/clothes"):
            os.mkdir("data/clothes")

        # Save the image as a PNG file with the sanitized item name
        with open(file_name, "wb") as file:
            file.write(response.content)
        logger.debug(f"Successfully downloaded {file_name}")
    else:
        logger.error(f"Failed to download {file_name}")

    return file_name


if not os.path.exists("logs/xml_temp"):
    os.mkdir("logs/xml_temp")


def main(bot):
    @bot.command(
        name="downloadrbxclothing",
        help="Copy a piece of clothing on roblox and get the source image.",
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def clothingcopy(ctx, clothing_id: str):
        temp_message = await reply(ctx, None, f"Processing request for: {clothing_id}")
        start_time = time.time()  # Record start time

        try:
            download_xml(clothing_id)
            xml_file_path = f"logs/xml_temp/{clothing_id}.xml"
            new_id = extract_new_id(xml_file_path)

            if new_id:
                file = download_clothing_image(clothing_id, new_id)
                upload_file = discord.File(file, filename="asset.png")
                elapsed_time = time.time() - start_time  # Calculate elapsed time
                await temp_message.delete()
                await reply(ctx, None, f"Processed in {elapsed_time:.2f} seconds")
                await checkDMsMSG(ctx, "Clothing Copy", "for the source image.")
                await ctx.author.send(file=upload_file)
                if os.path.exists(file):
                    os.remove(file)
            else:
                elapsed_time = time.time() - start_time
                logger.error(f"Failed to extract new ID from {xml_file_path}")
                await temp_message.delete()
                await reply(ctx, None, f"Failed after {elapsed_time:.2f} seconds")
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.exception(f"Failed to process request: {e}")
            await temp_message.delete()
            await reply(
                ctx, None, f"Failed after {elapsed_time:.2f} seconds\n({str(e)})"
            )
        finally:
            if os.path.exists(xml_file_path):
                os.remove(xml_file_path)
