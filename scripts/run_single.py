"""Script for testing a single run through an agent."""

import asyncio
from langgraph_sdk import get_client
import uuid
import hashlib

from eaia.schemas import EmailData, TextData, ProspectData
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

async def main():
    client = get_client(url="http://127.0.0.1:2024")
    # initial state
    intial_messages = [AIMessage(content="""Hi, my name is DJ from Rosedale Capital. Would you be interested in a proposal for your vacant lot in Cape Coral?reply "Yes" for more info. reply "End" to quit.""")
                       , AIMessage(content="""Okay great. 
The property address is 2531 E Monroe St Phoenix, AZ and your name is Sheet Metal Workers Assoc Local Union 359 correct?""")
                    #    AIMessage(content="""Hi DJ, thanks for reaching out! I'm interested in hearing more about the proposal for my vacant lot in Cape Coral. Please provide me with the details.""")]
                ]
    text: TextData = {
        "id": "test",
        "thread_id": "test_20",
        "from_phone_number": "+14802909934",
        "text_content": "yes",
        "send_time": "2024-12-26T13:13:41-08:00",
        "to_phone_number": "+1234567890",
    }

    prospect: ProspectData = {
        "created_at":"2025-06-01T21:13:07.140883+00:00",
        "phone_number":"+16025991760",
        "first_name":"Sheet",
        "last_name":"Metal Workers Assoc Local Union 359",
        "opt_in":True,
        "contact_info_confirmed":False,
        "messages_sent":0,
        "status":"ready_for_initial_offer",
        "updated_at":"2025-06-01T21:13:06.63518",
        "id":21,
        "prop_street":"2531 E Monroe St",
        "prop_city":"Phoenix",
        "prop_state":"AZ",
        "prop_zip":"85034",
        "follow_up_date":"2025-06-15",
    }

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


if __name__ == "__main__":
    asyncio.run(main())
