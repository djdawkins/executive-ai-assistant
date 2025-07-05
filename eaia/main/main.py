from datetime import datetime
from typing import Final
import os
from dotenv import load_dotenv

from flask import Flask, request, Response
from supabase import create_client

from urllib.parse import urlunsplit, urlparse

from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client as TwloClient

import json
import logging

from multiprocessing import Process
from flask import Flask

from eaia.schemas import (
    TextData,
    ProspectData,
)
from langgraph_sdk import get_client
import uuid
import hashlib

from eaia.main.get_prospect_info import get_contact_view_data

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

twloClient: TwloClient = TwloClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
app = Flask(__name__)

async def send_text(txt_message, phone_number):

    print("Ready to setup texting !!!")
                          
    try:

        message = twloClient.messages \
            .create(
                body=txt_message,
                from_=TWILIO_PHONE_NUMBER,
                to=phone_number
     )
        
    except Exception as e:
        print("Error sending message")
        print(e)

@app.route("/sms", methods=['GET', 'POST'])
async def webhooks():

    """Send a dynamic reply to an incoming text message"""
    # Get the message the user sent our Twilio number
    body = request.values.get('Body', None)
    to_num = request.values.get('To', None)
    from_num = request.values.get('From', None)
    sms_id = request.values.get('SmsSid', None)
    message_id = request.values.get('MessageSid', None)
    print("body: \n", request.values)
    # print("from_num: ", from_num)

    # lead_manager = LeadManager()
    # sms_handler = SMSHandler(lead_manager)

    # sms_handler.handle_incoming_message(from_num, body)
    client = get_client(url="http://127.0.0.1:2024")
    # initial state
    intial_messages = []
    text: TextData = {
        "id": sms_id,
        "thread_id": message_id,
        "from_phone_number": "+14802909934",
        "text_content": body,
        "send_time": datetime.now().isoformat(),
        "to_phone_number": "+1234567890",
    }

    prospect: ProspectData = get_contact_view_data('+16025991760')

    thread_id = str(
        uuid.UUID(hex=hashlib.md5(text["thread_id"].encode("UTF-8")).hexdigest())
    )
    try:
        await client.threads.delete(thread_id)
    except:
        pass
    await client.threads.create(thread_id=thread_id)
    await client.runs.create(
        thread_id,
        "main",
        input={"text": text, "messages": intial_messages, "prospect": prospect},
        multitask_strategy="rollback",
    )

    return '', 200

# def run_flask():
#     port = int(os.environ.get('PORT', 5000))
#     app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Always run both processes in production mode
    app.run()



