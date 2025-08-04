import os
from dotenv import load_dotenv


from twilio.rest import Client as TwloClient
import logging


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

twloClient: TwloClient = TwloClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_text(txt_message, phone_number):

    logger.info("Ready to setup texting !!!")
                          
    try:

        message = twloClient.messages \
            .create(
                body=txt_message,
                from_=TWILIO_PHONE_NUMBER,
                to=phone_number
     )
        
    except Exception as e:
        logger.info("Error sending message")
        logger.info(e)
