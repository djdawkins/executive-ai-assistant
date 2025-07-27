FROM langchain/langgraph-api:3.11



# -- Adding local package . --
ADD . /deps/executive-ai-assistant
# -- End of local package . --

# -- Installing all local dependencies --
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -c /api/constraints.txt -e /deps/*
# -- End of local dependencies install --
ENV LANGGRAPH_STORE='{"index": {"embed": "openai:text-embedding-3-small", "dims": 1536}}'
ENV LANGSERVE_GRAPHS='{"main": "/deps/executive-ai-assistant/eaia/main/graph.py:graph", "cron": "/deps/executive-ai-assistant/eaia/cron_graph.py:graph", "general_reflection_graph": "/deps/executive-ai-assistant/eaia/reflection_graphs.py:general_reflection_graph", "multi_reflection_graph": "/deps/executive-ai-assistant/eaia/reflection_graphs.py:multi_reflection_graph"}'



WORKDIR /deps/executive-ai-assistant