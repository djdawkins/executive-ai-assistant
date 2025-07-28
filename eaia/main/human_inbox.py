"""Parts of the graph that require human input."""

import uuid

from langsmith import traceable
from eaia.schemas import State, text_template
from langgraph.types import interrupt
from langgraph.store.base import BaseStore
from typing import TypedDict, Literal, Union, Optional
from langgraph_sdk import get_client
from eaia.main.config import get_config
from supabase import create_client, Client
import os
from datetime import datetime, date, timedelta

# Initialize Supabase client
print("Initializing Supabase client...")
print("Supabase URL:", os.getenv('SUPABASE_URL'))
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

sb_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

LGC = get_client()


class HumanInterruptConfig(TypedDict):
    allow_ignore: bool
    allow_respond: bool
    allow_edit: bool
    allow_accept: bool


class ActionRequest(TypedDict):
    action: str
    args: dict


class HumanInterrupt(TypedDict):
    action_request: ActionRequest
    config: HumanInterruptConfig
    description: Optional[str]


class HumanResponse(TypedDict):
    type: Literal["accept", "ignore", "response", "edit"]
    args: Union[None, str, ActionRequest]


TEMPLATE = """#

**To**: {to}
**From**: {_from}

{text_content}
"""


def _generate_email_markdown(state: State):
    contents = state["text"]
    return TEMPLATE.format(
        to=contents["to_phone_number"],
        _from=contents["from_phone_number"],
        text_content=contents["text_content"],
    )


async def save_email(state: State, config, store: BaseStore, status: str):
    namespace = (
        config["configurable"].get("assistant_id", "default"),
        "triage_examples",
    )
    key = state["text"]["id"]
    response = await store.aget(namespace, key)
    if response is None:
        data = {"input": state["text"], "triage": status}
        await store.aput(namespace, str(uuid.uuid4()), data)


@traceable
async def send_message(state: State, config, store):
    prompt_config = get_config(config)
    memory = prompt_config["memory"]
    user = prompt_config['name']
    tool_call = state["messages"][-1].tool_calls[0]
    request: HumanInterrupt = {
        "action_request": {"action": tool_call["name"], "args": tool_call["args"]},
        "config": {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": False,
            "allow_accept": False,
        },
        "description": _generate_email_markdown(state),
    }
    print("Requesting human input for tool call:", request)
    responses = interrupt([request])
    response = responses[0]
    print("Response from human input:", response)
    _text_template = text_template.format(
        prop_street=state["prospect"]["prop_street"] ,
        prop_city=state["prospect"]["prop_city"],
        prop_state=state["prospect"]["prop_state"],
        first_name=state["prospect"]["first_name"],
        last_name=state["prospect"]["last_name"],
    )

    print("Requesting human input for tool call:", response)
    # if response["type"] == "response":
    msg = {
        "type": "tool",
        "name": tool_call["name"],
        "content": response["args"],
        "tool_call_id": tool_call["id"],
    }
    memory = False # override memory for text responses
    if memory:
        await save_email(state, config, store, "text")
        rewrite_state = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Draft a response to this text:\n\n{_text_template}",
                }
            ]
            + state["messages"],
            "feedback": f"{user} responded in this way: {response['args']}",
            "prompt_types": ["background"],
            "assistant_key": config["configurable"].get("assistant_id", "default"),
        }
        await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    # elif response["type"] == "ignore":
    #     msg = {
    #         "role": "assistant",
    #         "content": "",
    #         "id": state["messages"][-1].id,
    #         "tool_calls": [
    #             {
    #                 "id": tool_call["id"],
    #                 "name": "Ignore",
    #                 "args": {"ignore": True},
    #             }
    #         ],
    #     }
    #     if memory:
    #         await save_email(state, config, store, "no")
    # else:
    #     raise ValueError(f"Unexpected response: {response}")

    return {"messages": [msg]}


@traceable
async def send_text_draft(state: State, config, store):
    prompt_config = get_config(config)
    memory = prompt_config["memory"]
    user = prompt_config['name']
    tool_call = state["messages"][-1].tool_calls[0]
    request: HumanInterrupt = {
        "action_request": {"action": tool_call["name"], "args": tool_call["args"]},
        "config": {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": True,
            "allow_accept": True,
        },
        "description": _generate_email_markdown(state),
    }
    response = interrupt([request])[0]
    prospect = state["prospect"]
    _text_template = text_template.format(
        prop_street=prospect["prop_street"] ,
        prop_city=prospect["prop_city"],
        prop_state=prospect["prop_state"],
        first_name=prospect["first_name"],
        last_name=prospect["last_name"],
    )
    print("Requesting human input for tool call:", response["type"])
    if response["type"] == "response":
        msg = {
            "type": "tool",
            "name": tool_call["name"],
            "content": f"Error, {user} interrupted and gave this feedback: {response['args']}",
            "tool_call_id": tool_call["id"],
        }
        # if memory:
        #     await save_email(state, config, store, "email")
        #     rewrite_state = {
        #         "messages": [
        #             {
        #                 "role": "user",
        #                 "content": f"Draft a response to this email:\n\n{_email_template}",
        #             }
        #         ]
        #         + state["messages"],
        #         "feedback": f"Error, {user} interrupted and gave this feedback: {response['args']}",
        #         "prompt_types": ["tone", "email", "background", "calendar"],
        #         "assistant_key": config["configurable"].get("assistant_id", "default"),
        #     }
        #     await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "ignore":
        msg = {
            "role": "assistant",
            "content": "",
            "id": state["messages"][-1].id,
            "tool_calls": [
                {
                    "id": tool_call["id"],
                    "name": "Ignore",
                    "args": {"ignore": True},
                }
            ],
        }
        # if memory:
        #     await save_email(state, config, store, "no")
    elif response["type"] == "edit":
        msg = {
            "role": "assistant",
            "content": state["messages"][-1].content,
            "id": state["messages"][-1].id,
            "tool_calls": [
                {
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "args": response["args"]["args"],
                }
            ],
        }
        # if memory:
        #     corrected = response["args"]["args"]["content"]
        #     await save_email(state, config, store, "email")
        #     rewrite_state = {
        #         "messages": [
        #             {
        #                 "role": "user",
        #                 "content": f"Draft a response to this email:\n\n{_email_template}",
        #             },
        #             {
        #                 "role": "assistant",
        #                 "content": state["messages"][-1].tool_calls[0]["args"]["content"],
        #             },
        #         ],
        #         "feedback": f"A better response would have been: {corrected}",
        #         "prompt_types": ["tone", "email", "background", "calendar"],
        #         "assistant_key": config["configurable"].get("assistant_id", "default"),
        #     }
        #     await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "accept":
        # if memory:
        #     await save_email(state, config, store, "email")
        if prospect["status"] == "ready_for_initial_offer":
            prospect["status"] = "negotiating"

        today = date.today().isoformat()
        prospect["follow_up_date"] = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
        print("Updating prospect status to negotiating:", prospect)
        sb_client.table('leads').upsert(prospect, on_conflict='phone_number').execute()

        return {"prospect": prospect}
    else:
        raise ValueError(f"Unexpected response: {response}")
    return {"messages": [msg]}

@traceable
async def send_email_draft(state: State, config, store):
    prompt_config = get_config(config)
    memory = prompt_config["memory"]
    user = prompt_config['name']
    tool_call = state["messages"][-1].tool_calls[0]
    request: HumanInterrupt = {
        "action_request": {"action": tool_call["name"], "args": tool_call["args"]},
        "config": {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": True,
            "allow_accept": True,
        },
        "description": _generate_email_markdown(state),
    }
    response = interrupt([request])[0]
    _email_template = email_template.format(
        email_thread=state["email"]["page_content"],
        author=state["email"]["from_email"],
        subject=state["email"]["subject"],
        to=state["email"].get("to_email", ""),
    )
    if response["type"] == "response":
        msg = {
            "type": "tool",
            "name": tool_call["name"],
            "content": f"Error, {user} interrupted and gave this feedback: {response['args']}",
            "tool_call_id": tool_call["id"],
        }
        if memory:
            await save_email(state, config, store, "email")
            rewrite_state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a response to this email:\n\n{_email_template}",
                    }
                ]
                + state["messages"],
                "feedback": f"Error, {user} interrupted and gave this feedback: {response['args']}",
                "prompt_types": ["tone", "email", "background", "calendar"],
                "assistant_key": config["configurable"].get("assistant_id", "default"),
            }
            await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "ignore":
        msg = {
            "role": "assistant",
            "content": "",
            "id": state["messages"][-1].id,
            "tool_calls": [
                {
                    "id": tool_call["id"],
                    "name": "Ignore",
                    "args": {"ignore": True},
                }
            ],
        }
        if memory:
            await save_email(state, config, store, "no")
    elif response["type"] == "edit":
        msg = {
            "role": "assistant",
            "content": state["messages"][-1].content,
            "id": state["messages"][-1].id,
            "tool_calls": [
                {
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "args": response["args"]["args"],
                }
            ],
        }
        if memory:
            corrected = response["args"]["args"]["content"]
            await save_email(state, config, store, "email")
            rewrite_state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a response to this email:\n\n{_email_template}",
                    },
                    {
                        "role": "assistant",
                        "content": state["messages"][-1].tool_calls[0]["args"]["content"],
                    },
                ],
                "feedback": f"A better response would have been: {corrected}",
                "prompt_types": ["tone", "email", "background", "calendar"],
                "assistant_key": config["configurable"].get("assistant_id", "default"),
            }
            await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "accept":
        if memory:
            await save_email(state, config, store, "email")
        return None
    else:
        raise ValueError(f"Unexpected response: {response}")
    return {"messages": [msg]}


@traceable
async def notify(state: State, config, store):
    prompt_config = get_config(config)
    memory = prompt_config["memory"]
    user = prompt_config['name']
    request: HumanInterrupt = {
        "action_request": {"action": "Notify", "args": {}},
        "config": {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": False,
            "allow_accept": False,
        },
        "description": _generate_email_markdown(state),
    }
    response = interrupt([request])[0]
    _text_template = text_template.format(
            prop_street=state["prospect"]["prop_street"] ,
            prop_city=state["prospect"]["prop_city"],
            prop_state=state["prospect"]["prop_state"],
            first_name=state["prospect"]["first_name"],
            last_name=state["prospect"]["last_name"],
    )
    if response["type"] == "response":
        msg = {"type": "user", "content": response["args"]}
        if memory:
            await save_email(state, config, store, "text")
            rewrite_state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a response to this text:\n\n{_text_template}",
                    }
                ]
                + state["messages"],
                "feedback": f"{user} gave these instructions: {response['args']}",
                "prompt_types": ["text", "background", "calendar"],
                "assistant_key": config["configurable"].get("assistant_id", "default"),
            }
            await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "ignore":
        msg = {
            "role": "assistant",
            "content": "",
            "id": str(uuid.uuid4()),
            "tool_calls": [
                {
                    "id": "foo",
                    "name": "Ignore",
                    "args": {"ignore": True},
                }
            ],
        }
        if memory:
            await save_email(state, config, store, "no")
    else:
        raise ValueError(f"Unexpected response: {response}")

    return {"messages": [msg]}


@traceable
async def send_cal_invite(state: State, config, store):
    prompt_config = get_config(config)
    memory = prompt_config["memory"]
    user = prompt_config['name']
    tool_call = state["messages"][-1].tool_calls[0]
    request: HumanInterrupt = {
        "action_request": {"action": tool_call["name"], "args": tool_call["args"]},
        "config": {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": True,
            "allow_accept": True,
        },
        "description": _generate_email_markdown(state),
    }
    response = interrupt([request])[0]
    _email_template = email_template.format(
        email_thread=state["email"]["page_content"],
        author=state["email"]["from_email"],
        subject=state["email"]["subject"],
        to=state["email"].get("to_email", ""),
    )
    if response["type"] == "response":
        msg = {
            "type": "tool",
            "name": tool_call["name"],
            "content": f"Error, {user} interrupted and gave this feedback: {response['args']}",
            "tool_call_id": tool_call["id"],
        }
        if memory:
            await save_email(state, config, store, "email")
            rewrite_state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a response to this email:\n\n{_email_template}",
                    }
                ]
                + state["messages"],
                "feedback": f"{user} interrupted gave these instructions: {response['args']}",
                "prompt_types": ["email", "background", "calendar"],
                "assistant_key": config["configurable"].get("assistant_id", "default"),
            }
            await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "ignore":
        msg = {
            "role": "assistant",
            "content": "",
            "id": state["messages"][-1].id,
            "tool_calls": [
                {
                    "id": tool_call["id"],
                    "name": "Ignore",
                    "args": {"ignore": True},
                }
            ],
        }
        if memory:
            await save_email(state, config, store, "no")
    elif response["type"] == "edit":
        msg = {
            "role": "assistant",
            "content": state["messages"][-1].content,
            "id": state["messages"][-1].id,
            "tool_calls": [
                {
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "args": response["args"]["args"],
                }
            ],
        }
        if memory:
            await save_email(state, config, store, "email")
            rewrite_state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a response to this email:\n\n{_email_template}",
                    }
                ]
                + state["messages"],
                "feedback": f"{user} interrupted gave these instructions: {response['args']}",
                "prompt_types": ["email", "background", "calendar"],
                "assistant_key": config["configurable"].get("assistant_id", "default"),
            }
            await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "accept":
        if memory:
            await save_email(state, config, store, "email")
        return None
    else:
        raise ValueError(f"Unexpected response: {response}")

    return {"messages": [msg]}
