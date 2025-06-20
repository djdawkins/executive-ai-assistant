"""Core agent responsible for drafting text."""

from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.store.base import BaseStore

from eaia.schemas import (
    State,
    NewTextDraft,
    ResponseTextDraft,
    Question,
    Ignore,
    text_template,
)
from eaia.main.config import get_config

TEXT_WRITING_INSTRUCTIONS = """You are {full_name}'s executive assistant. You are a top-notch executive assistant who cares about {name} performing as well as possible.

{background}

{name} gets lots of texts. This has been determined to be a text that is worth {name} responding to.

Your job is to help {name} respond. You can do this in a few ways.

# Using the `Question` tool

First, get all required information to respond. You can use the Question tool to ask {name} for information if you do not know it.

When drafting texts (either to responsed on thread or , if you do not have all the information needed to respond in the most appropriate way, call the `Question` tool until you have that information. Do not put placeholders for names or texts or information - get that directly from {name}!
You can get this information by calling `Question`. Again - do not, under any circumstances, draft a text with placeholders or you will get fired.

Remember, if you don't have enough information to respond, you can ask {name} for more information. Use the `Question` tool for this.
Never just make things up! So if you do not know something, or don't know what {name} would prefer, don't hesitate to ask him.

# Using the `ResponseTextDraft` tool

Next, if you have enough information to respond, you can draft a text for {name}. Use the `ResponseTextDraft` tool for this.

ALWAYS draft texts as if they are coming from {name}. Never draft them as "{name}'s assistant" or someone else.

Do NOT make up texts.

The lead status for the prospect is "{lead_status}".
If the lead status is ready_for_initial_offer, then respond using the following template:
"Based on new construction, we can offer you a price of $X. This is based on the current market conditions and the value of your property."

The context for the text is the full text thread, which you can see below. You can use this to help you determine a response.
{text_thread}

{response_preferences}

# Background information: information you may find helpful when responding to texts or deciding what to do.

{random_preferences}"""

draft_prompt = """{instructions}

Remember to call a tool correctly! Use the specified names exactly - not add `functions::` to the start. Pass all required arguments.

Here is the text thread. Note that this is the full text thread. Pay special attention to the most recent text.

{text}"""


async def draft_response(state: State, config: RunnableConfig, store: BaseStore):
    """Write a text to a customer."""
    model = config["configurable"].get("model", "gpt-4o")
    llm = ChatOpenAI(
        model=model,
        temperature=0,
        parallel_tool_calls=False,
        tool_choice="required",
    )
    tools = [
        NewTextDraft,
        ResponseTextDraft,
        Question,
    ]
    messages = state.get("messages") or []
    prospect = state.get("prospect") or []

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
    key = "random_preferences"
    result = await store.aget(namespace, key)
    if result and "data" in result.value:
        random_preferences = result.value["data"]
    else:
        await store.aput(
            namespace, key, {"data": prompt_config["background_preferences"]}
        )
        random_preferences = prompt_config["background_preferences"]
    key = "response_preferences"
    result = await store.aget(namespace, key)
    if result and "data" in result.value:
        response_preferences = result.value["data"]
    else:
        await store.aput(namespace, key, {"data": prompt_config["response_preferences"]})
        response_preferences = prompt_config["response_preferences"]
    
    _prompt = TEXT_WRITING_INSTRUCTIONS.format(
        text_thread=prospect.get("last_message_received", ""),
        random_preferences=random_preferences,
        response_preferences=response_preferences,
        name=prompt_config["name"],
        full_name=prompt_config["full_name"],
        background=prompt_config["background"],
        lead_status=prospect.get("status", ""),
    )

    # print(state["messages"][-1])

    input_message = draft_prompt.format(
        instructions=_prompt,
        text = text_template.format(
            prop_street=state["prospect"]["prop_street"] ,
            prop_city=state["prospect"]["prop_city"],
            prop_state=state["prospect"]["prop_state"],
            first_name=state["prospect"]["first_name"],
            last_name=state["prospect"]["last_name"],
        )
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
