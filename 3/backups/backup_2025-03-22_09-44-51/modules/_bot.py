from discord.ext import commands
from collections import defaultdict
import sys
from modules._LoggerModule import setup_logging

logger = setup_logging(__name__)
logger.debug(f"imported, id: {id(sys.modules[__name__])}")


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._custom_event_handlers = defaultdict(list)

    def _event(self, event_name: str = None):
        """
        Decorator to register a custom event handler.
        If event_name is omitted, the function's own name is used (with the "on_" prefix stripped, if present).

        Usage examples:
            @bot._event("message")
            async def my_message_handler(message):
                ...

            # Or, if the function name is already 'on_reaction_add'
            @bot._event()
            async def on_reaction_add(reaction, user):
                ...
        """

        def decorator(func):
            # Strip the leading "on_" if event_name is not explicitly provided.
            key = event_name or (
                func.__name__[3:] if func.__name__.startswith("on_") else func.__name__
            )
            self._custom_event_handlers[key].append(func)
            logger.debug(f"Registered custom event handler for event: {key}")
            return func

        return decorator

    def dispatch(self, event, *args, **kwargs):
        ###logger.debug(f"Dispatching event: {event} with args: {args} and kwargs: {kwargs}")
        # Call all registered custom handlers for this event.
        if event in self._custom_event_handlers:
            for handler in self._custom_event_handlers[event]:
                try:
                    # Schedule each handler concurrently.
                    self.loop.create_task(handler(*args, **kwargs))
                    ###logger.debug(f"Handler {handler.__name__} scheduled for event: {event}")
                except Exception:
                    logger.exception(
                        f"Error while handling event: {event} with handler: {handler.__name__}"
                    )
        # Continue with the built-in dispatching (which will also call @bot.event handlers)
        super().dispatch(event, *args, **kwargs)
