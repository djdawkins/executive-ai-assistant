from langgraph_sdk import LangGraphServer
from eaia.main.graph import call_graph

server = LangGraphServer(call_graph, name="land_shark_sdk_server")

if __name__ == "__main__":
    server.start()