import os
from typing import Final

import requests
import time

from eaia.main.lead_manager import LeadManager


class SMSHandler:
    def __init__(self, lead_manager: LeadManager):
        self.lead_manager = lead_manager
    
    def handle_incoming_message(self, phone_number: str, message: str = ""):
        """Process incoming SMS messages"""
        # TODO: confirm that this is returning none when phone_number doesn't exist in the db
        lead_info = self.lead_manager.get_lead_info(phone_number)

        # self.lead_manager.add_or_update_lead(phone_number)
        # client_info_dict = self.lead_manager.get_lead_info(phone_number)
        # return client_info_dict

        # If it is the first time the lead has reached out - add them to LEADS table
        if not lead_info:
            self.lead_manager.add_or_update_lead(phone_number)
            lead_info = self.lead_manager.get_lead_info(phone_number)
            return lead_info
        
        lead_status = lead_info['status']

        if lead_status == 'unknown_lead':
            print('send to catch all discord')
            self.lead_manager.handle_unknown_lead(phone_number, lead_info, message)
            #TODO: uncomment could below after adding a catch all to the DISCORD : P
            # dictToSend = {'content': message}

            # print(f"sending message to this thread id {thread_id}")

            # res = requests.post(f'https://discord.com/api/webhooks/{WEBHOOK_ID}/{WEBHOOK_TOKEN}?thread_id={thread_id}', json=dictToSend)  
            # self.lead_manager.record_message(phone_number, 'outbound', message)
            return

        else:
            return lead_info     
        
        # Check if this is an opt-in
        if (message.strip().lower() in ('yes', 'y', 'opt in', 'start')) & (lead_status == 'new'):
            self.lead_manager.update_lead_status(phone_number, "proposal_sent")
            self.lead_manager.handle_opt_in(phone_number, lead_info)
            return

        if (message.strip().lower() in ('no', 'n', 'opt out', 'stop')) & (lead_status == 'new'):
            self.lead_manager.update_lead_status(phone_number, "proposal_sent")
            self.lead_manager.handle_opt_out(phone_number, lead_info)
            return
         
        # Check if this is contact info confirmation
        if (lead_info and lead_info['opt_in'] and not lead_info['contact_info_confirmed']):
            message = message.strip().lower()
            if message in ('yes', 'y', 'confirm'):
                self.lead_manager.confirm_contact_info(phone_number, lead_info, message)
                return
            
            else:
                self.lead_manager.decline_contact_info(phone_number, lead_info, message)
                return 

        # Check if this is contact info confirmation
        if (lead_info and lead_info['opt_in'] and lead_info['contact_info_confirmed'] and lead_info['discord_thread_id']):
            thread_id = lead_info['discord_thread_id']

            #TODO: delete after testing
            message = 'test forward to discord'
            dictToSend = {'content': message}

            print(f"sending message to this thread id {thread_id}")

            res = requests.post(f'https://discord.com/api/webhooks/{WEBHOOK_ID}/{WEBHOOK_TOKEN}?thread_id={thread_id}', json=dictToSend)  
            self.lead_manager.record_message(phone_number, 'inbound', message)
            return       

        print('send to catch all discord')
        #TODO: uncomment could below after adding a catch all to the DISCORD : P
        # dictToSend = {'content': message}
        self.lead_manager.handle_unknown_response(phone_number, lead_info, message)

        # print(f"sending message to this thread id {thread_id}")

        # res = requests.post(f'https://discord.com/api/webhooks/{WEBHOOK_ID}/{WEBHOOK_TOKEN}?thread_id={thread_id}', json=dictToSend)  
        # self.lead_manager.record_message(phone_number, 'outbound', message)
