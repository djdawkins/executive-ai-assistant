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


triage_prompt = """You are {full_name}'s executive assistant. You are a top-notch executive assistant who cares about {name} performing as well as possible.

{background}. 

{name} gets lots of texts. Your job is to categorize the below text to see whether is it worth responding to.

Texts that are worth responding to:
{triage_text}

There are also other things that {name} should know about, but don't require a text response. For these, you should notify {name} (using the `notify` response). Examples of this include:
{triage_notify}

For texts not worth responding to, respond `no`. For something where {name} should respond via text, respond `text`. If it's important to notify {name}, but no text is required, respond `text`. \

If unsure, opt to `notify` {name} - you will learn from this in the future.

{fewshotexamples}

Please determine how to handle the below text thread:

From: {author}
To: {to}

{text_thread}"""


async def triage_input(state: State, config: RunnableConfig, store: BaseStore):
    model = config["configurable"].get("model", "gpt-4o")
    llm = ChatOpenAI(model=model, temperature=0)
    examples = await get_few_shot_examples(state["text"], store, config)
    prompt_config = get_config(config)
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
    )
    model = llm.with_structured_output(RespondTo).bind(
        tool_choice={"type": "function", "function": {"name": "RespondTo"}}
    )
    response = await model.ainvoke(input_message)
    if len(state["messages"]) > 0:
        delete_messages = [RemoveMessage(id=m.id) for m in state["messages"]]
        return {"triage": response, "messages": delete_messages}
    else:
        return {"triage": response}
