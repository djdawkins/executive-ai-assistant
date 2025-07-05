"""Fetches few shot examples for triage step."""

from langgraph.store.base import BaseStore
from eaia.schemas import TextData


template = """
Text From: {from_phone_number}
Text To: {to_phone_number}
Text Content: 
```
{content}
```
> Triage Result: {result}"""


def format_similar_examples_store(examples):
    strs = ["Here are some previous examples:"]
    for eg in examples:
        strs.append(
            template.format(
                to_phone_number=eg.value["input"]["to_phone_number"],
                from_phone_number=eg.value["input"]["from_phone_number"],
                content=eg.value["input"]["text_content"][:400],
                result=eg.value["triage"],
            )
        )
    return "\n\n------------\n\n".join(strs)


async def get_few_shot_examples(text: TextData, store: BaseStore, config):
    namespace = (
        config["configurable"].get("assistant_id", "default"),
        "triage_examples",
    )
    result = await store.asearch(namespace, query=str({"input": text}), limit=5)
    if result is None:
        return ""
    return format_similar_examples_store(result)
