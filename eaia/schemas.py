from typing import Annotated, List, Literal
from pydantic import BaseModel, Field
from langgraph.graph.message import AnyMessage
from typing_extensions import TypedDict


from langgraph.graph import add_messages


class EmailData(TypedDict):
    id: str
    thread_id: str
    from_email: str
    subject: str
    page_content: str
    send_time: str
    to_email: str

class TextData(TypedDict):
    id: str
    thread_id: str
    from_phone_number: str
    text_content: str
    send_time: str
    to_phone_number: str

class ProspectData(TypedDict):
    first_name: str
    last_name: str
    phone_number: str
    prop_street: str
    prop_city: str
    prop_state: str
    prop_zip: str
    updated_at: str
    contact_info_confirmed: bool
    status: Literal["new", "on_boarding", "dnd", "negotiating", "contract_sent", "closed_won", "closed_lost"] = "new"
    # status = ['new', 'contact_confirmed', 'needs_followup', 'proposal_sent', 'negotiating', 'closed_won', 'closed_lost', 'unknown_lead', 'unknown_response']
    follow_up_date: str | None


class RespondTo(BaseModel):
    logic: str = Field(
        description="logic on WHY the response choice is the way it is", default=""
    )
    response: Literal["no", "text", "notify", "question", "onboard"] = "no"


class ResponseTextDraft(BaseModel):
    """Draft of an text to send as a response."""

    content: str
    new_recipients: List[str]


class NewTextDraft(BaseModel):
    """Draft of a new text to send."""

    content: str
    recipients: List[str]

class ContactConfirmResponse(BaseModel):
    """Response to confirm contact info."""

    response: str = "Okay great. The property address is 930 Ne 43rd Ter Cape Coral, FL and your name is Ken Stewart correct?"

class ReWriteText(BaseModel):
    """Logic for rewriting an text"""

    tone_logic: str = Field(
        description="Logic for what the tone of the rewritten text should be"
    )
    rewritten_content: str = Field(description="Content rewritten with the new tone")


class Question(BaseModel):
    """Question to ask user."""

    content: str


class Ignore(BaseModel):
    """Call this to ignore the text. Only call this if user has said to do so."""

    ignore: bool


# Needed to mix Pydantic with TypedDict
def convert_obj(o, m):
    if isinstance(m, dict):
        return RespondTo(**m)
    else:
        return m


class State(TypedDict):
    text: TextData
    triage: Annotated[RespondTo, convert_obj]
    messages: Annotated[List[AnyMessage], add_messages]
    prospect: ProspectData


text_template = """
Okay great. 
The property address is {prop_street} {prop_city}, {prop_state} and your name is {first_name} {last_name} correct?
"""
