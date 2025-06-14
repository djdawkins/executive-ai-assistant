from typing import TypedDict
from eaia.gmail import fetch_group_emails
from langgraph_sdk import get_client
import httpx
import uuid
import hashlib
from langgraph.graph import StateGraph, START, END
from eaia.main.config import get_config
from eaia.schemas import EmailData, TextData, ProspectData
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from supabase import create_client, Client
import os
from datetime import date
# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

sb_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

client = get_client()


class JobKickoff(TypedDict):
    minutes_since: int


async def main(state: JobKickoff, config):
    #TODO: Fix add thread id and follow up date column to the leads table
    today = date.today().isoformat()
    prospects, _ = await sb_client.table('leads') \
                .select('phone_number', '"prop_street"', '"prop_city"', \
                        '"prop_state"', '"prop_zip"', '"first_name"', '"last_name"', \
                            'status', 'opt_in', 'contact_info_confirmed', 'last_message_sent', \
                                'last_message_received', 'thread_id') \
                .eq('follow_up_date', today) \
                .limit(100) \
                .execute()
        
    minutes_since: int = state["minutes_since"]
    email = get_config(config)["email"]

    for prospect in await prospects:

        if prospect["status"] == "ready_for_initial_offer":
            # TODO: Add messages here to triggrer the notify node if needed
            intial_messages = []
            # TODO: Add dummy text data here if needed
            text: TextData = {
                # "id": "test",
                # "thread_id": prospect["thread_id"] or str(uuid.uuid4()),
                # # "thread_id": prospect["thread_id"] or str(uuid.uuid4()),

                # "from_phone_number": "+14802909934",
                # "text_content": "yes",
                # "send_time": "2024-12-26T13:13:41-08:00",
                # "to_phone_number": "+1234567890",
            }

            prospect: ProspectData = {
                "phone_number":prospect["phone_number"],
                "first_name":prospect["first_name"],
                "last_name":prospect["last_name"],
                "opt_in":prospect["opt_in"],
                "contact_info_confirmed":prospect["contact_info_confirmed"],
                "status":prospect["status"],
                "prop_street": prospect["prop_street"],
                "prop_city":prospect["prop_city"],
                "prop_state":prospect["prop_state"],
                "prop_zip":prospect["prop_zip"],
                # is the below needed?
                "message_history":[prospect["last_message_sent"], prospect["last_message_received"]],
            }

            thread_id = str(
                uuid.UUID(hex=hashlib.md5(text["thread_id"].encode("UTF-8")).hexdigest())
            )

            await client.runs.create(
                thread_id,
                "main",
                input={"text": text, "messages": intial_messages, "prospect": prospect},
                multitask_strategy="rollback",
            )        
        else:
            # TODO: Add messages here if needed, depends on how we populate the database
            intial_messages = []
            # TODO: Add text data here if needed, depends on how we populate the database
            text: TextData = {
                # "id": "test",
                # "thread_id": prospect["thread_id"] or str(uuid.uuid4()),
                # # "thread_id": prospect["thread_id"] or str(uuid.uuid4()),

                # "from_phone_number": "+14802909934",
                # "text_content": "yes",
                # "send_time": "2024-12-26T13:13:41-08:00",
                # "to_phone_number": "+1234567890",
            }

            prospect: ProspectData = {
                "phone_number":prospect["phone_number"],
                "first_name":prospect["first_name"],
                "last_name":prospect["last_name"],
                "opt_in":prospect["opt_in"],
                "contact_info_confirmed":prospect["contact_info_confirmed"],
                "status":prospect["status"],
                "prop_street": prospect["prop_street"],
                "prop_city":prospect["prop_city"],
                "prop_state":prospect["prop_state"],
                "prop_zip":prospect["prop_zip"],
                "message_history":[prospect["last_message_sent"], prospect["last_message_received"]],
            }

            thread_id = str(
                uuid.UUID(hex=hashlib.md5(text["thread_id"].encode("UTF-8")).hexdigest())
            )

            await client.runs.create(
                thread_id,
                "main",
                input={"text": text, "messages": intial_messages, "prospect": prospect},
                multitask_strategy="rollback",
            )


graph = StateGraph(JobKickoff)
graph.add_node(main)
graph.add_edge(START, "main")
graph.add_edge("main", END)
graph = graph.compile()
