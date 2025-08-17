import os

import click
import requests

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


OPENAI_NASTY_CATEGORIES = {
    "sexual",
    "hate",
    "harassment",
    "self-harm",
    "sexual/minors",
    "hate/threatening",
    "violence/graphic",
    "self-harm/intent",
    "self-harm/instructions",
    "harassment/threatening",
    "violence",
}

# Get API key from environment variable
openai_api_key = os.environ.get("OPENAI_API_KEY", "")
start_sequence = "\nA:"
restart_sequence = "\n\nQ: "


class OpenAI:
    def __init__(self):
        self.class_name = self.__class__.__name__

    def log_error(self, error, exception=None, warning=False):
        if warning:
            logger.error(error)
        else:
            logger.error(error)

    def is_text_risky(self, text: str) -> object:
        """Ask the openai moderation endpoint if the text is risky.

        See https://platform.openai.com/docs/guides/moderation/quickstart for details.
        """
        allowed_categories = {"violence"}  # Can be triggered by some AI safety terms

        response = None
        try:
            http_response = requests.post(
                "https://api.openai.com/v1/moderations",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_api_key}",
                },
                json={"input": text},
            )
        except Exception as e:
            self.log_error("Error in Requests module trying to moderate content", e)
            return True

        if http_response.status_code == 401:
            self.log_error("OpenAI Authentication Failed")
            return True
        elif http_response.status_code == 429:
            self.log_error("OpenAI Rate Limit Exceeded", warning=True)
            return True
        elif http_response.status_code != 200:
            self.log_error(
                f"Possible issue with the OpenAI API. Status: {http_response.status_code}, Content: {http_response.text}"
            )
            return True
        response = http_response.json()
        logger.info(response)

        return response


@click.group(name="openai")
def openai():
    """OpenAI CLI command group."""
    pass


@openai.command(name="is_text_risky")
@click.argument("text")
def is_text_risky(text: str):
    """Check if the provided text is risky using OpenAI moderation."""
    openai_instance = OpenAI()
    result = openai_instance.is_text_risky(text)
    click.echo(f"Is the text risky? {result}")


if __name__ == "__main__":
    oai = OpenAI()
    # Example usage
    text_to_check = "This is a test message."
    is_risky = oai.is_text_risky(text_to_check)
    print(f"Is the text risky? {is_risky}")
