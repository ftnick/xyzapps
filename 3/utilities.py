import time
import importlib.util
import sys
import tempfile
import requests
from rich.console import Console

def fetch_version():
    try:
        response = requests.get("https://raw.githubusercontent.com/ftnick/feature/refs/heads/main/host/version.txt")
        response.raise_for_status()
        return response.text.strip()
    except Exception:
        return "GetRequestException"

def censor_string(s, visible=4):
    return s[:visible] + "*" * (len(s) - visible) if len(s) > visible else s


def importUrl(url: str, func_name: str = None):
    response = requests.get(url)
    if response.status_code != 200:
        raise ImportError(f"Failed to download module from {url}")

    # Save to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
        temp_file.write(response.content)
        temp_filename = temp_file.name

    # Load module dynamically
    module_name = temp_filename.split("/")[-1].replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, temp_filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    # Return function if requested
    if func_name:
        if not hasattr(module, func_name):
            raise ImportError(f"Module '{module_name}' has no function '{func_name}'")
        return getattr(module, func_name)

    return module


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
