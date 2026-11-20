import asyncio, json
from autogen_agentchat.agents import AssistantAgent
from autogen_core.memory import ListMemory, MemoryContent, MemoryMimeType
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_ext.models.replay import ReplayChatCompletionClient

async def main():
    replies = ["Which error code do you see?", "809: the VPN can't reach the server. Avoid guest Wi-Fi.", "Try your phone hotspot."]
    prefs = ListMemory()                                                          # long-term memory (7.3)
    await prefs.add(MemoryContent(content="User prefers short bullet answers", mime_type=MemoryMimeType.TEXT))
    agent = AssistantAgent("assist", model_client=ReplayChatCompletionClient(replies),
                           system_message="You are ServiceApps Assist. Cite KB numbers.",
                           model_context=BufferedChatCompletionContext(buffer_size=4),   # short-term limit (7.1)
                           memory=[prefs])
    for q in ["My VPN keeps dropping", "Error 809", "I'm on hotel Wi-Fi"]:
        r = await agent.run(task=q)
        print(f"{q!r:24} -> {r.messages[-1].content}")
    kept = await agent._model_context.get_messages()                              # what the next call would see
    print("model context keeps:", len(kept), "messages (buffer_size=4)")
    state = await agent.save_state()                                              # serialization (7.3)
    blob = json.dumps(state)
    print("saved state:", len(blob), "chars of JSON, keys:", sorted(state))
    agent2 = AssistantAgent("assist", model_client=ReplayChatCompletionClient(["(resumed)"]),
                            model_context=BufferedChatCompletionContext(buffer_size=4))
    await agent2.load_state(json.loads(blob))
    print("restored context:", len(await agent2._model_context.get_messages()), "messages")
    await prefs.clear()
    print("memory after clear():", (await prefs.query("anything")).results)

asyncio.run(main())
