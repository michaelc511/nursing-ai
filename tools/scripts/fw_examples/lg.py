from langchain_core.messages import AIMessage, HumanMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

RULES = "You are ServiceApps Assist. Cite KB numbers."

def respond(state: MessagesState, config, *, store: BaseStore):
    user = config["configurable"]["user_id"]
    window = trim_messages(state["messages"], strategy="last", token_counter=count_tokens_approximately,
                           max_tokens=60, start_on="human")                 # short-term limit (7.1)
    prefs = [i.value["text"] for i in store.search((user, "memories"))]   # long-term memory (7.3)
    # a real node would call the model with RULES + prefs + window; here we report what it would send
    return {"messages": [AIMessage(f"(would send {len(window)} of {len(state['messages'])} messages; memories: {prefs})")]}

builder = StateGraph(MessagesState)
builder.add_node("respond", respond)
builder.add_edge(START, "respond")
store = InMemoryStore()
graph = builder.compile(checkpointer=InMemorySaver(), store=store)            # persistence + long-term store

store.put(("u42", "memories"), "pref-1", {"text": "prefers short bullet answers"})
cfg = {"configurable": {"thread_id": "u42:INC0012345", "user_id": "u42"}}
for q in ["My VPN shows error 809", "I'm on hotel Wi-Fi", "Still failing on my hotspot"]:
    out = graph.invoke({"messages": [HumanMessage(q)]}, cfg)
    print(f"{q!r:32} -> {out['messages'][-1].content}")

print("saved in thread:", len(graph.get_state(cfg).values["messages"]), "messages")
new = {"configurable": {"thread_id": "u42:general", "user_id": "u42"}}
print("new thread, same user:", graph.invoke({"messages": [HumanMessage("Hi")]}, new)["messages"][-1].content)
graph.checkpointer.delete_thread("u42:INC0012345")
print("after delete_thread:", graph.get_state(cfg).values.get("messages", []))
