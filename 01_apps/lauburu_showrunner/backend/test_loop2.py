import asyncio
from engine import simulation_loop, retrieve_memories, call_llm, npcs

async def debug_loop():
    print("Starting loop")
    npc = npcs[0]
    other_npc = npcs[1]
    print(f"Retrieving memories for {npc['name']}")
    try:
        ctx = await retrieve_memories(f"{npc['name']} interaction with {other_npc['name']}")
        print(f"Memories: {ctx}")
    except Exception as e:
        print(f"Memory error: {e}")
        return
        
    print("Calling LLM")
    try:
        reply = await call_llm(npc, "You are a test", "Hello")
        print(f"LLM Reply: {reply}")
    except Exception as e:
        print(f"LLM Error: {e}")

asyncio.run(debug_loop())
