from pushover import Client

# local imports
from src.config import load as load_config

config = load_config()

if config["PUSHOVER_ENABLED"]:
    client = Client(config["PUSHOVER_USER_KEY"], api_token=config["PUSHOVER_API_TOKEN"])


def send_notification(title, message):
    if config["PUSHOVER_ENABLED"]:
        client.send_message(message, title=title)

