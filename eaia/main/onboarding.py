"""Core agent responsible for onbaording prospects."""

from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.store.base import BaseStore

from eaia.schemas import (
    State
    , text_template
    , land_survey_text
)
from eaia.main.config import get_config
from datetime import datetime

TEXT_WRITING_INSTRUCTIONS = """You are {full_name}'s executive assistant. You are a top-notch executive assistant who cares about {name} performing as well as possible.

{background}

{name} gets lots of texts. This has been determined to be a text from a prospect that is in the on boarding phase.

Your job is to help {name} decide how to respond. 
You can do this by responding with one of the following keywords:

# ContactConfirmResponse 

First, the contact confirm information is a boolean that indicates whether the contact is confirmed. 
The contact confirm information value is {contact_confirm}.
Follow this exactly,
If the contact confirm information is "False", you should always respond with the `ContactConfirmResponse`.


"""
draft_prompt = """{instructions}

Remember to call a tool correctly! Use the specified names exactly - not add `functions::` to the start. Pass all required arguments.

"""

async def onboarding(state: State, config: RunnableConfig, store: BaseStore):
    """Write a text to a customer."""
    # print("config:", config)
    model = config["configurable"].get("model", "gpt-4o")
    llm = ChatOpenAI(
        model=model,
        temperature=0
    )

    messages = state.get("messages") or []
    prospect = state.get("prospect") or []

    prompt_config = get_config(config)
    namespace = (config["configurable"].get("assistant_id", "default"),)

    _prompt = TEXT_WRITING_INSTRUCTIONS.format(
        contact_confirm=state["prospect"]["contact_info_confirmed"],
        name=prompt_config["name"],
        full_name=prompt_config["full_name"],
        background=prompt_config["background"],
    )
    input_message = draft_prompt.format(
        instructions=_prompt,
    )

    # model = llm.bind_tools(tools)
    messages = [{"role": "user", "content": input_message}] + messages
    response = await llm.ainvoke(messages)
    print("response:", response.content)
    
    if response.content not in ["ContactConfirmResponse", "LandSurvey", "Question", "Ignore"]:
        messages += [{"role": "user", "content": "Please choose a key value."}]

    elif response.content == "ContactConfirmResponse":

        text = text_template.format(
            prop_street=state["prospect"]["prop_street"] ,
            prop_city=state["prospect"]["prop_city"],
            prop_state=state["prospect"]["prop_state"],
            first_name=state["prospect"]["first_name"],
            last_name=state["prospect"]["last_name"],
        )
        messages += [{"role": "user", "content": text}]
        prospect["contact_info_confirmed"] = True
        prospect["status"] = "onboarding"
        prospect["follow_up_date"] = datetime.now().date()

    elif response.content == "LandSurvey":
        text = land_survey_text
        messages += [{"role": "user", "content": text}]
        prospect["contact_info_confirmed"] = True
        prospect["status"] = "ready_for_initial_offer"
        prospect["follow_up_date"] = datetime.now().date()

    return {"prospect": prospect, "messages": messages}
