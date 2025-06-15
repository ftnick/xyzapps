import traceback
import logging
import time
import webbrowser
import uuid
import datetime
import os
import requests
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
import sys


def aCD(seconds: int, message: str):
    """
    Displays a countdown with a spinning icon and a custom message.

    Args:
        seconds (int): The starting number for the countdown.
        message (str): A custom message to display alongside the countdown.
    """
    console = Console()

    # The spinner (using "dots") is displayed until the context exits.
    with console.status(
        f"{message} {seconds} second(s) remaining", spinner="dots"
    ) as status:
        for remaining in range(seconds, 0, -1):
            status.update(f"{message} {remaining} second(s) remaining")
            time.sleep(1)


def trace_calls(frame, event, arg):
    # if event != "call":  # We only care about function calls
    #    return
    code = frame.f_code
    print(f"call trace: {code.co_name} in {code.co_filename}, line {frame.f_lineno}")
    try:
        print(f":{frame.f_locals}:")
        print(f"globals: {frame.f_globals}")
    except Exception:
        pass
    return trace_calls  # This keeps tracing other calls


# Initialize Rich Console for output (no color)
console = Console(color_system="windows")

# Configure logging for crash details
logging.basicConfig(
    filename=os.path.join("logs", "SUER_recovery_log.log"),
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Define the base URL for the help system
HELP_BASE_URL = "https://feature.ftnick.xyz/debug"


def generate_error_id():
    """Generates a unique error ID for each crash."""
    return str(uuid.uuid4())


def generate_help_url(exception_name, file_name):
    """Generates a help URL for debugging."""
    return f"{HELP_BASE_URL}?error={exception_name}&file={file_name}"


def check_help_url_for_error(help_url):
    """Check if the help URL contains a debug page for the specific error."""
    try:
        response = requests.get(help_url)
        if response.status_code == 200:
            return True  # Debug page exists
        else:
            return False  # No debug page found
    except requests.RequestException:
        return False  # Failed to connect or invalid URL


def CrashHandler(exception: Exception, file_name: str):
    sys.settrace(trace_calls)
    error_id = generate_error_id()
    error_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    exception_name = type(exception).__name__
    help_url = generate_help_url(exception_name, os.path.basename(file_name))
    sys.settrace(None)
    time.sleep(1)
    os.system("cls")

    # Display custom header using ASCII art
    console.print(Panel(Text("SUER: Error Occurred", justify="center", style="bold")))

    # Display error ID and time for tracking
    console.print(f"\n[bold]Error ID:[/bold] {error_id}")
    console.print(f"[bold]Timestamp:[/bold] {error_time}")

    # Print error message and detailed traceback
    console.print(f"[bold]Exception Type:[/bold] {exception_name}")
    console.print(f"[bold]Error Message:[/bold] {str(exception)}")

    traceback_str = "".join(
        traceback.format_exception(type(exception), exception, exception.__traceback__)
    )
    console.print(Panel(traceback_str, title="Full Traceback", style="bold"))

    # Log the full error details to a file
    logging.error("Error ID: %s", error_id)
    logging.error("Timestamp: %s", error_time)
    logging.error("Exception occurred: %s", str(exception))
    logging.error("Traceback:\n%s", traceback_str)

    # Check if a debug page is available for the specific error
    if not check_help_url_for_error(help_url):
        console.print("\nA debug page is available for this error!")
        console.print(f"[bold]Click here to access the help page:[/bold] {help_url}")
        if (
            Prompt.ask(
                "Do you want to open the help page in the browser? (yes/no)"
            ).lower()
            == "yes"
        ):
            webbrowser.open(help_url)
    else:
        console.print("\nNo specific debug page found for this error.")
        console.print(
            "You can try searching the internet for more details or contact support."
        )
    return exception
