import datetime
from modules._LoggerModule import setup_logging

logger = setup_logging(__name__)

Registrations = {}
Errored = False
Error = None


def Register(name: str, function, *args):
    global Registrations
    global Errored
    global Error

    logger.debug(f"Starting registration for '{name}'...")
    start_time = datetime.datetime.now()
    try:
        # Execute the registration function
        function(*args)
    except Exception as e:
        Error = e
        Registrations[name] = {
            "status": "Failed",
            "error": str(e),
            "execution_time": None,
        }
        Errored = True
        logger.exception(f"Failed to register '{name}': {e}")
    else:
        end_time = datetime.datetime.now()
        execution_time = (end_time - start_time).total_seconds() * 1000
        Registrations[name] = {
            "status": "Finished",
            "execution_time": f"{execution_time:.2f}ms",
        }
        logger.debug(f"Successfully registered '{name}' in {execution_time:.2f}ms")


def registrationResults():
    logger.debug("Registration Results:")
    for name, details in Registrations.items():
        execution_time = str(details.get("execution_time", "N/A"))
        status = str(details.get("status", "N/A"))
        error = str(details.get("error", "N/A"))

        # Truncate to 10 characters if longer, and append '~' if needed
        name = (name[:9] + "~") if len(name) > 10 else name.ljust(10)
        status = (status[:9] + "~") if len(status) > 10 else status.ljust(10)
        execution_time = (
            (execution_time[:9] + "~")
            if len(execution_time) > 10
            else execution_time.ljust(10)
        )
        # error = (error[:9] + '~') if len(error) > 10 else error.ljust(10)

        # Log the formatted output
        logger.debug(
            f"Name: {name} | Status: {status} | Execution Time: {execution_time} | Error: {error}"
        )


def errorFlip():
    global Errored
    global Error
    return Errored,Error
