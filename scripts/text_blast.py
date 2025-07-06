"""Script for testing a single run through an agent."""

import asyncio
from langgraph_sdk import get_client
import time

from eaia.schemas import EmailData, TextData, ProspectData
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from supabase import create_client, Client
import os
from datetime import date, timedelta

from eaia.main.get_prospect_info import get_contact_view_data
from eaia.main.main import send_text

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
TEST_PHONE_NUMBER = os.getenv('TEST_PHONE_NUMBER')

sb_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def main():

    compliacne_text_template = """Hi {name}, my name is DJ from Rosedale Capital.\
        \n\nWould you be interested in a proposal for your vacant lot in {property}?\
        \n\nreply "Yes" for more info. reply "End" to quit."""


    new_prospects, _ = sb_client.table('new_contacts') \
                            .select('*') \
                            .limit(3) \
                            .execute()

    for prospect in new_prospects[1]:
        phone_number = prospect['phone_number']

        prospect_data = get_contact_view_data(phone_number)

        full_property_address = prospect_data['prop_street'] + " " + prospect_data['prop_city'] + ", " + prospect_data['prop_state'] + " " + str(prospect_data['prop_zip'])
        state_city = prospect_data['prop_city'] + ", " + prospect_data['prop_state']
        personalized_message = compliacne_text_template.format(name=prospect_data['first_name'], property=state_city)

        await send_text(personalized_message, TEST_PHONE_NUMBER)

        time.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
