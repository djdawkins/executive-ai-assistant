import os
from datetime import datetime
from typing import Optional, Dict, Tuple, Final
import requests
from supabase import create_client, Client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

class LeadManager:
    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self._initialize_db()
        
    def _initialize_db(self):
        """Initialize the database with required tables"""
        # Note: With Supabase, table creation is typically done through the UI
        # or migrations. This method is kept for compatibility but doesn't need
        # to create tables as they should be pre-defined in Supabase.
        pass
    
    def get_contact_view_data(self, phone_number: str):
        # Get data from supabase
        data, _ = self.supabase.table('contact_view') \
                    .select('phone_number', '"Property Street"', '"Property City"', \
                            '"Property State"', '"Property ZIP Code"', '"First Name"', '"Last Name"')\
                    .eq('phone_number', phone_number).execute()
        
        print("data: ", data)

        if data[1]:
            contact_dict = data[1][0]
        else:
            client_info_dict = {}
            return client_info_dict

        first_name = contact_dict['First Name']
        last_name = contact_dict['Last Name']

        phone_number = contact_dict['phone_number']
        prop_street = contact_dict['Property Street']
        prop_city = contact_dict['Property City']
        prop_state = contact_dict['Property State']
        prop_zip = contact_dict['Property ZIP Code']

        client_info_dict = {
                'first_name': first_name, 
                'last_name': last_name, 
                'phone_number': phone_number, 
                'prop_street': prop_street, 
                'prop_city': prop_city, 
                'prop_state': prop_state, 
                'prop_zip': prop_zip
        }
        print("client_info_dict: ", client_info_dict)

        return client_info_dict

    def get_send_proposal_view_data(self):
        # Get data from supabase
        data, _ = self.supabase.table('send_proposal_view') \
                    .select('phone_number', '"Property Street"', '"Property City"', \
                            '"Property State"', '"Property ZIP Code"', '"First Name"', '"Last Name"').limit(10).execute()
        
        # print("data: ", data)

        if data[1]:
            contact_list = data[1]
            recipients_list = []
        else:
            contact_list = []
            return client_info_dict

        for contact in contact_list:
            first_name = contact['First Name']
            last_name = contact['Last Name']

            phone_number = contact['phone_number']
            prop_street = contact['Property Street']
            prop_city = contact['Property City']
            prop_state = contact['Property State']
            prop_zip = contact['Property ZIP Code']

            client_info_dict = {
                    'first_name': first_name, 
                    'last_name': last_name, 
                    'phone_number': phone_number, 
                    'prop_street': prop_street, 
                    'prop_city': prop_city, 
                    'prop_state': prop_state, 
                    'prop_zip': prop_zip
            }

            recipients_list.append(client_info_dict)
        # print("client_info_dict: ", client_info_dict)

        return recipients_list
    
    def add_or_update_lead(self, phone_number: str):
        client_info_dict = self.get_contact_view_data(phone_number)
        """Add a new lead or update existing one"""
        if client_info_dict:
            lead_data = {
                'phone_number': phone_number,
                'first_name': client_info_dict['first_name'],
                'last_name': client_info_dict['last_name'],
                'prop_street': client_info_dict['prop_street'],
                'prop_city': client_info_dict['prop_city'],
                'prop_state': client_info_dict['prop_state'],
                'prop_zip': client_info_dict['prop_zip'],
                'updated_at': datetime.utcnow().isoformat()
            }
        else:
            lead_data = {
                'phone_number': phone_number,
                'status': 'unknown_lead',
                'updated_at': datetime.utcnow().isoformat()
            }
        
        # Upsert operation (insert if not exists, update if exists)
        self.supabase.table('leads').upsert(lead_data, on_conflict='phone_number').execute()

    def record_message(self, phone_number: str, direction: str, content: str):
        """Record a message sent to or received from a lead"""
        # Record the message
        message_data = {
            'lead_phone': phone_number,
            'direction': direction,
            'content': content
        }
        self.supabase.table('messages').insert(message_data).execute()
        
        # Update lead stats
        current_time = datetime.utcnow().isoformat()
        
        if direction == 'outbound':
            # Get current messages_sent count
            response = self.supabase.table('leads').select('messages_sent').eq('phone_number', phone_number).execute()
            current_count = 0
            if response.data and len(response.data) > 0:
                current_count = response.data[0].get('messages_sent', 0) or 0
            
            # Update with incremented count
            self.supabase.table('leads').update({
                'messages_sent': current_count + 1,
                'last_message_sent': current_time,
                'updated_at': current_time
            }).eq('phone_number', phone_number).execute()
        else:
            self.supabase.table('leads').update({
                'last_message_received': current_time,
                'updated_at': current_time
            }).eq('phone_number', phone_number).execute()

    def handle_opt_in(self, phone_number: str, lead_info: dict):
        """Handle when a lead opts in"""
        self.supabase.table('leads').update({
            'opt_in': True,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('phone_number', phone_number).execute()
        
        # Send confirmation request
        self.send_opt_in_confirmation_request(phone_number, lead_info)

    def handle_opt_out(self, phone_number: str, lead_info: dict):
        """Handle when a lead opts in"""
        #TODO: add attribute to set follow up time 30 / 60 / 90
        self.supabase.table('leads').update({
            'opt_in': False,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('phone_number', phone_number).execute()
        
        # Send confirmation request
        self.send_opt_out_confirmation_request(phone_number, lead_info)

    def send_opt_in_confirmation_request(self, phone_number: str, lead_info: dict):
        first_name = lead_info['first_name']
        last_name = lead_info['last_name']
        prop_street = lead_info['prop_street']
        prop_city = lead_info['prop_city']
        prop_state = lead_info['prop_state']
        prop_zip = lead_info['prop_zip']

        """Send contact info confirmation request"""
        # This would integrate with your SMS service
        message = f"Thanks for opting in! Please confirm the property address {prop_street} {prop_city}, {prop_state} {prop_zip} \
            . Reply with 'Yes' if this is correct."
        self.send_message(phone_number, message)
        # self.record_message(phone_number, 'outbound', message)

    def send_opt_out_confirmation_request(self, phone_number: str, lead_info: dict):
        first_name = lead_info['first_name']
        last_name = lead_info['last_name']
        prop_street = lead_info['prop_street']
        prop_city = lead_info['prop_city']
        prop_state = lead_info['prop_state']
        prop_zip = lead_info['prop_zip']

        """Send contact info confirmation request"""
        # This would integrate with your SMS service
        message = f"You have been removed from our list, thank you."
        self.send_message(phone_number, message)

    def send_contact_decline_request(self, phone_number: str, lead_info: dict):
        # TODO: Get response from twilio campaign
        """Send contact info confirmation request"""
        # This would integrate with your SMS service
        message = "send_contact_decline_request."
        self.send_message(phone_number, message)
        # self.record_message(phone_number, 'outbound', message)

    def confirm_contact_info(self, phone_number: str, lead_info: dict, message: str):
        """Mark contact info as confirmed and create Discord thread"""
        self.supabase.table('leads').update({
            'contact_info_confirmed': True,
            'status': 'contact_confirmed',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('phone_number', phone_number).execute()
        
        # Create Discord thread
        thread_id = self.create_discord_thread(phone_number, lead_info, message)
        # Send confirmation request
        self.record_message(phone_number, 'inbound', message)
        
    def decline_contact_info(self, phone_number: str, lead_info: dict, message: str):
        """Mark contact info as confirmed and create Discord thread"""
        self.supabase.table('leads').update({
            'contact_info_confirmed': False,
            'status': 'contact_confirmed',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('phone_number', phone_number).execute()
        
        # Create Discord thread
        thread_id = self.create_discord_thread(phone_number, lead_info, message)
        self.record_message(phone_number, 'inbound', message)

    def handle_unknown_response(self, phone_number: str, lead_info: dict, message: str):
        """Mark contact info as confirmed and create Discord thread"""
        self.supabase.table('leads').update({
            # 'contact_info_confirmed': True,
            'status': 'unknown_response',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('phone_number', phone_number).execute()
        
        # Create Discord thread
        thread_id = self.create_discord_thread(phone_number, lead_info, message)
        self.record_message(phone_number, 'inbound', message)

    def handle_unknown_lead(self, phone_number: str, lead_info: dict, message: str):
        """Mark contact info as confirmed and create Discord thread"""
        self.supabase.table('leads').update({
            # 'contact_info_confirmed': True,
            'status': 'unknown_lead',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('phone_number', phone_number).execute()
        
        # Create Discord thread
        thread_id = self.create_discord_thread(phone_number, lead_info, message)
        self.record_message(phone_number, 'inbound', message)

    def add_discord_thread_to_db(self, phone_number, thread_id):
        if thread_id:
            self.supabase.table('leads').update({
                'discord_thread_id': thread_id,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('phone_number', phone_number).execute()

    def create_discord_thread(self, phone_number: str, lead_info: dict, message: str) -> Optional[str]:
        first_name = lead_info['first_name']
        last_name = lead_info['last_name']
        prop_street = lead_info['prop_street']
        prop_city = lead_info['prop_city']
        prop_state = lead_info['prop_state']
        prop_zip = lead_info['prop_zip']
        status = lead_info['status']

        """Create a Discord thread for the lead"""
        try:
            thread_id = '1214334238359420928'
            thread_name = str(phone_number)

            dictToSend = {'thread_name':thread_name, 'content':f'Contact: {first_name} {last_name} {prop_street} {prop_city}, {prop_state} {prop_zip}.\
                           \n Status: {status} \n Response: {message}'}

            print("thread_name:", thread_name)

            # res = requests.post(f'https://discord.com/api/webhooks/{WEBHOOK_ID}/{WEBHOOK_TOKEN}?thread_id={thread_id}', json=dictToSend)            
            res = requests.post(f'https://discord.com/api/webhooks/{WEBHOOK_ID}/{WEBHOOK_TOKEN}', json=dictToSend) 
            
            # For now, return a mock ID
            return f"discord_thread_{thread_name}"
        except Exception as e:
            print(f"Error creating Discord thread: {e}")
            return None

    def get_lead_info(self, phone_number: str) -> Optional[Dict]:
        """Get all information about a lead"""
        # Get lead data
        lead_response = self.supabase.table('leads').select('*').eq('phone_number', phone_number).execute()
        
        if lead_response.data and len(lead_response.data) > 0:
            lead = lead_response.data[0]
            
            # Get message history
            messages_response = self.supabase.table('messages')\
                .select('direction,content,timestamp')\
                .eq('lead_phone', phone_number)\
                .order('timestamp', desc=True)\
                .execute()
            
            return {
                **lead,
                # 'message_history': messages_response.data or []
            }
        return None

    def update_lead_status(self, phone_number: str, status: str):
        """Update the sales funnel status of a lead"""
        valid_statuses = ['new', 'contact_confirmed', 'needs_followup', 'proposal_sent', 'negotiating', 'closed_won', 'closed_lost', 'unknown_lead', 'unknown_response']
        
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
            
        self.supabase.table('leads').update({
            'status': status,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('phone_number', phone_number).execute()

    def send_message(self, phone_number: str, content: str):
        """Send a message to a lead"""
        # This would integrate with your SMS service
        print(f"Sending to {phone_number}: {content}")
        # Record the message
        self.record_message(phone_number, 'outbound', content)