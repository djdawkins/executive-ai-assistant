"""Agent responsible for triaging the email, can either ignore it, try to respond, or notify user."""

from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_core.messages import RemoveMessage
from langgraph.store.base import BaseStore

from eaia.schemas import (
    State,
    RespondTo,
)
from eaia.main.fewshot import get_few_shot_examples
from eaia.main.config import get_config
from datetime import datetime, date, timedelta


triage_prompt = """You are {full_name}'s executive assistant. You are a top-notch executive assistant who cares about {name} performing as well as possible.

{background}. 

{name} gets lots of texts. Your job is to categorize the below text to see whether is it worth responding to.

Texts that are worth responding to:
{triage_text}

The lead status for the prospect is "{lead_status}".
Follow this exactly, the lead status for the prospect and their resonse determines how you triage the text. 
If the response is positive and the lead status is "new" or "onboarding", you should always respond `onboard`.

The is_past_follow_up variable is a boolean that indicates whether the follow up date is past or not, and it's value is {is_past_follow_up}.
If the lead status is "ready_for_initial_offer", and the is_past_follow_up is "True", you should always respond `text`.
If the lead status is "ready_for_initial_offer", and the is_past_follow_up is "False", you should always respond `notify`.

If the lead status is "negotiating", you should always respond `text`.

There are also other things that {name} should know about, but don't require a text response. For these, you should notify {name} (using the `notify` response). Examples of this include:
{triage_notify}

For texts not worth responding to, respond `no`. For something where {name} should respond via text, respond `text`. If it's important to notify {name}, but no text is required, respond `text`. \

If unsure, opt to `notify` {name} - you will learn from this in the future.
{fewshotexamples}

Below is the response from the prospect:

{text_thread}"""


async def triage_input(state: State, config: RunnableConfig, store: BaseStore):
    model = config["configurable"].get("model", "gpt-4o")
    llm = ChatOpenAI(model=model, temperature=0)
    examples = await get_few_shot_examples(state["text"], store, config)
    prompt_config = get_config(config)

    prospect_info = state.get("prospect") or {}
    # prospect_info = get_contact_view_data(state["text"]["from_phone_number"])
    # prospect_info = get_contact_view_data('+16025991760')
    follow_up_date = prospect_info.get("follow_up_date", None)

    # Convert follow_up_date to a date object if it's a string
    if isinstance(follow_up_date, str):
        follow_up_date = datetime.strptime(follow_up_date, "%Y-%m-%d").date()
    
    print(f"Follow up date: {follow_up_date}, today: {date.today()}")
    if follow_up_date > date.today():
        is_past_follow_up = False

    else:
        is_past_follow_up = True

    input_message = triage_prompt.format(
        text_thread=state["text"]["text_content"],
        author=state["text"]["from_phone_number"],
        to=state["text"].get("to_phone_number", ""),
        fewshotexamples=examples, #TODO: check for quality
        name=prompt_config["name"],
        full_name=prompt_config["full_name"],
        background=prompt_config["background"],
        triage_no=prompt_config["triage_no"],
        triage_text=prompt_config["triage_text"],
        triage_notify=prompt_config["triage_notify"],
        lead_status=prospect_info["status"],
        is_past_follow_up=is_past_follow_up
        ,
    )
    model = llm.with_structured_output(RespondTo).bind(
        tool_choice={"type": "function", "function": {"name": "RespondTo"}}
    )
    response = await model.ainvoke(input_message)
    if state.get("prospect") is None:
        state["prospect"] = prospect_info
    # TODO: add logic for how to manage message removal
    if len(state["messages"]) > 5:
        delete_messages = [RemoveMessage(id=m.id) for m in state["messages"]]
        return {"triage": response, "messages": delete_messages, "prospect": state["prospect"]}
    else:
        return {"triage": response, "prospect": state["prospect"]}

