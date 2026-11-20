from llama_index.core.llms import ChatMessage
from llama_index.core.memory import Memory, StaticMemoryBlock

rules = StaticMemoryBlock(name="rules", static_content="You are ServiceApps Assist. Cite KB numbers.", priority=0)
memory = Memory.from_defaults(session_id="u42:INC0012345", token_limit=60,         # short-term limit (7.1)
                              chat_history_token_ratio=0.5, token_flush_size=20,
                              memory_blocks=[rules])                                # pinned rules (7.1)
turns = [("user", "My VPN keeps dropping on my laptop at the hotel"), ("assistant", "Which error code do you see?"),
         ("user", "Error 809 every time I connect"), ("assistant", "809 means the VPN can't reach the server."),
         ("user", "I'm on the hotel guest Wi-Fi right now"), ("assistant", "Avoid guest Wi-Fi; try your phone hotspot."),
         ("user", "Still failing on the hotspot too")]
for role, text in turns:
    memory.put(ChatMessage(role=role, content=text))
sent = memory.get()                                    # what the next model call receives
print("stored messages :", len(memory.get_all()))
print("sent next call  :", len(sent), "messages")
print("first one sent  :", sent[0].role.value, "->", str(sent[0].content)[:90])
print("oldest chat sent:", [m.content for m in sent if m.role.value == "user"][0])
