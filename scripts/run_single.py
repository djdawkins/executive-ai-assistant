"""Script for testing a single run through an agent."""

import asyncio
from langgraph_sdk import get_client
import uuid
import hashlib

from eaia.schemas import EmailData, TextData
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

async def main():
    client = get_client(url="http://127.0.0.1:2024")
    # initial state
    intial_messages = [AIMessage(content="""Hi, my name is DJ from Rosedale Capital. Would you be interested in a proposal for your vacant lot in Cape Coral?reply "Yes" for more info. reply "End" to quit.""")]
                    #    , HumanMessage(content="""Yes""")
                    #    AIMessage(content="""Hi DJ, thanks for reaching out! I'm interested in hearing more about the proposal for my vacant lot in Cape Coral. Please provide me with the details.""")]
    
    text: TextData = {
        "id": "test",
        "thread_id": "test_5",
        "from_phone_number": "+14802909934",
        "text_content": "yes",
        "send_time": "2024-12-26T13:13:41-08:00",
        "to_phone_number": "+1234567890",
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
        input={"text": text, "messages": intial_messages},
        multitask_strategy="rollback",
    )


if __name__ == "__main__":
    asyncio.run(main())
