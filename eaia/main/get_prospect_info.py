import os
from supabase import create_client, Client

from eaia.main.lead_manager import LeadManager
from eaia.main.sms_handler import SMSHandler


SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def get_contact_view_data(phone_number: str):
    lead_manager = LeadManager()
    sms_handler = SMSHandler(lead_manager)

    lead_info = sms_handler.handle_incoming_message(phone_number, "body")

    return lead_info

