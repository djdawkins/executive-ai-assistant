"""Core agent responsible for onbaording prospects."""

from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.store.base import BaseStore

from eaia.schemas import (
    State,
    ContactConfirmResponse,
    ResponseTextDraft,
    Question,
    Ignore,
    text_template,
)
from eaia.main.config import get_config

TEXT_WRITING_INSTRUCTIONS = """You are {full_name}'s executive assistant. You are a top-notch executive assistant who cares about {name} performing as well as possible.

{background}

{name} gets lots of texts. This has been determined to be a text from a prospect that is in the on boarding phase.

Your job is to help {name} respond. You can do this in a few ways.

# Using the `ContactConfirm` tool

First, the contact confirm information is a boolean that indicates whether the contact is confirmed. 
The contact confirm information value is {contact_confirm}.
Follow this exactly,
If the contact confirm information is "False", you should always respond with the `ContactConfirmResponse` tool.

ALWAYS draft texts as if they are coming from {name}. Never draft them as "{name}'s assistant" or someone else.

Do NOT make up texts.
"""
draft_prompt = """{instructions}

Remember to call a tool correctly! Use the specified names exactly - not add `functions::` to the start. Pass all required arguments.

"""

async def onboarding(state: State, config: RunnableConfig, store: BaseStore):
    """Write a text to a customer."""
    model = config["configurable"].get("model", "gpt-4o")
    llm = ChatOpenAI(
        model=model,
        temperature=0,
        parallel_tool_calls=False,
        tool_choice="required",
    )
    tools = [
        ContactConfirmResponse,
        ResponseTextDraft,
        Question,
    ]
    messages = state.get("messages") or []
    if len(messages) > 0:
        tools.append(Ignore)
    prompt_config = get_config(config)
    namespace = (config["configurable"].get("assistant_id", "default"),)
    # key = "text_thread"
    # result = await store.aget(namespace, key)
    # if result and "data" in result.value:
    #     text_thread = result.value["data"]
    # else:
    #     await store.aput(namespace, key, {"data": prompt_config["text_thread"]})
    #     text_thread = prompt_config["text_thread"]
    # key = "random_preferences"
    # result = await store.aget(namespace, key)
    # if result and "data" in result.value:
    #     random_preferences = result.value["data"]
    # else:
    #     await store.aput(
    #         namespace, key, {"data": prompt_config["background_preferences"]}
    #     )
    #     random_preferences = prompt_config["background_preferences"]
    # key = "response_preferences"
    # result = await store.aget(namespace, key)
    # if result and "data" in result.value:
    #     response_preferences = result.value["data"]
    # else:
    #     await store.aput(namespace, key, {"data": prompt_config["response_preferences"]})
    #     response_preferences = prompt_config["response_preferences"]
    _prompt = TEXT_WRITING_INSTRUCTIONS.format(
        contact_confirm=state["prospect"]["contact_info_confirmed"],
        name=prompt_config["name"],
        full_name=prompt_config["full_name"],
        background=prompt_config["background"],
    )
    print(state["messages"][-1])
    input_message = draft_prompt.format(
        instructions=_prompt,
        # text=text_template.format(
        #     first_name=state["prospect"]["first_name"],
        #     last_name=state["prospect"]["last_name"],
        #     prop_street=state["prospect"]["prop_street"],
        #     prop_city=state["prospect"]["prop_city"],
        #     prop_state=state["prospect"]["prop_state"],
        # ),
    )

    model = llm.bind_tools(tools)
    messages = [{"role": "user", "content": input_message}] + messages
    i = 0
    while i < 5:
        response = await model.ainvoke(messages)
        if len(response.tool_calls) != 1:
            i += 1
            messages += [{"role": "user", "content": "Please call a valid tool call."}]
        else:
            break
    return {"draft": response, "messages": [response]}
