#!/usr/bin/env python3
import sys; sys.path.insert(0, 'src')
from skills.small_talk_skill import SmallTalkSkill

skill = SmallTalkSkill(config={'skills': {'small_talk': {'enable_llm': False}}})

print("\n🤖 ZERO Small Talk Skill - Quick Demo\n" + "="*60)

tests = [
    ("smalltalk.greeting", "Hello Zero"),
    ("smalltalk.identity", "Who are you?"),
    ("smalltalk.joke", "Tell me a joke"),
    ("smalltalk.thanks", "Thank you"),
]

for intent, query in tests:
    r = skill.execute(intent=intent, entities={"user_input": query}, context={})
    print(f"\n👤 You: {query}\n🤖 ZERO: {r.message}\n" + "-"*60)
