from discord.ext import commands
import sys
from modules._ReplyModule import reply
from modules._LoggerModule import setup_logging
from modules._RolesModule import roleLocked
import os
import time
import importlib
import psutil
import threading
import asyncio
import discord

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

    @bot.command(name="_reloadcogs", help="Reload all custom cogs.")
    @roleLocked("developer", 1307619426757120041)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def reloadcogs(ctx):
        from main_register import Register, registrationResults, errorFlip

        logger.info("Reloading all custom cogs...")

        for command in list(bot.commands):
            bot.remove_command(command.name)

        for file in os.listdir("cogs"):
            if file.endswith(".py") and not file.startswith("_"):
                module_name = f"cogs.{file[:-3]}"
                if module_name in importlib.sys.modules:
                    importlib.reload(importlib.sys.modules[module_name])
                    logger.info(f"Reloaded: {module_name}")

        for file in os.listdir("cogs"):
            if file.endswith(".py"):
                if not file.startswith("_"):
                    logger.debug(f"Pre-registering {file}...")
                    module_name = f"{"cogs"}.{file[:-3]}"  # Remove .py extension
                    module = importlib.import_module(module_name)
                    if hasattr(module, "main"):
                        setup_function = getattr(module, "main")
                        Register(file[:-3].capitalize(), setup_function, bot)
                else:
                    logger.debug(
                        f"Skipping {file} as it is a private module (_ prefix)"
                    )
            else:
                logger.debug(f"Skipping {file} as it is not a .py file (.py expected)")
        registrationResults()
        if errorFlip():
            logger.critical("Errors occurred during registration. Exiting...")
            raise SystemExit(1)

        await ctx.send("All custom cogs reloaded successfully.")
        logger.info("All custom cogs reloaded.")

    @bot.command(
        name="_forceCPU",
        help="Starts a stress test for the bot with advanced system monitoring.",
    )
    @roleLocked("developer", 1307619426757120041)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def stress_test(ctx, seconds: int = 5, intensity: int = 1000000):
        """
        Stress test command that increases CPU load while updating system stats in an embed.
        Usage: ?stresstest [seconds] [intensity]
            seconds: Duration of the test (default 5)
            intensity: Range for the CPU load operation (default 1000000)
        """
        # Create the initial embed
        embed = discord.Embed(
            title="⚠️ Stress Test Initiated",
            description=f"Test Duration: {seconds} seconds",
            color=0xFF4500,
        )
        embed.add_field(name="CPU Usage", value="Calculating...", inline=True)
        embed.add_field(name="CPU Frequency", value="Calculating...", inline=True)
        embed.add_field(name="Memory Usage", value="Calculating...", inline=True)
        embed.add_field(name="Disk Usage", value="Calculating...", inline=True)
        embed.add_field(name="Elapsed Time", value="0s", inline=True)
        embed.add_field(name="Progress", value="░░░░░░░░░░", inline=False)
        embed.set_footer(text="Stress test in progress...")

        message = await ctx.send(embed=embed)
        start_time = time.time()
        stop_flag = [False]  # Mutable flag for threads

        def cpu_stress():
            """Performs a CPU-intensive operation to simulate load."""
            while time.time() - start_time < seconds and not stop_flag[0]:
                # This loop performs a heavy calculation
                _ = [x**2 for x in range(intensity)]

        def update_stats():
            """Monitors system stats and updates the embed message."""
            while not stop_flag[0]:
                elapsed = int(time.time() - start_time)
                progress = min(int((elapsed / seconds) * 10), 10)
                progress_bar = "█" * progress + "░" * (10 - progress)

                cpu_usage = psutil.cpu_percent(interval=0.5)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
                cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else "N/A"

                new_embed = discord.Embed(
                    title="⚠️ Stress Test Running",
                    description=f"Test Duration: {seconds} seconds",
                    color=0xFF4500,
                )
                new_embed.add_field(
                    name="CPU Usage", value=f"{cpu_usage}%", inline=True
                )
                new_embed.add_field(
                    name="CPU Frequency", value=f"{cpu_freq} MHz", inline=True
                )
                new_embed.add_field(
                    name="Memory Usage", value=f"{mem.percent}%", inline=True
                )
                new_embed.add_field(
                    name="Disk Usage", value=f"{disk.percent}%", inline=True
                )
                new_embed.add_field(
                    name="Elapsed Time", value=f"{elapsed}s", inline=True
                )
                new_embed.add_field(name="Progress", value=progress_bar, inline=False)
                new_embed.set_footer(text="Stress test in progress...")

                # Edit the embed message thread-safely
                asyncio.run_coroutine_threadsafe(
                    message.edit(embed=new_embed), bot.loop
                )
                time.sleep(1)  # Update every second

        # Start threads for the stress test and monitoring
        stress_thread = threading.Thread(target=cpu_stress, daemon=True)
        monitor_thread = threading.Thread(target=update_stats, daemon=True)
        stress_thread.start()
        monitor_thread.start()

        await asyncio.sleep(seconds)
        stop_flag[0] = True  # Signal threads to stop

        # Final stats update after completion
        final_cpu = psutil.cpu_percent(interval=0.5)
        final_mem = psutil.virtual_memory().percent
        final_disk = psutil.disk_usage("/").percent
        final_elapsed = int(time.time() - start_time)

        final_embed = discord.Embed(
            title="✅ Stress Test Completed",
            description=f"Test ran for {seconds} seconds",
            color=0x00FF00,
        )
        final_embed.add_field(
            name="Final CPU Usage", value=f"{final_cpu}%", inline=True
        )
        final_embed.add_field(
            name="Final Memory Usage", value=f"{final_mem}%", inline=True
        )
        final_embed.add_field(
            name="Final Disk Usage", value=f"{final_disk}%", inline=True
        )
        final_embed.add_field(
            name="Total Elapsed Time", value=f"{final_elapsed}s", inline=True
        )
        final_embed.set_footer(text="Stress test completed successfully.")

        await message.edit(embed=final_embed)
