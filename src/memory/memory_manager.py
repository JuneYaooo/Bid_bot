import os
import json

class MemoryManager:
    def __init__(self, memory_file="memory.json"):
        self.memory_file = memory_file
        self.memory = {}
        if os.path.exists(memory_file):
            self.load_memory()

    def load_memory(self):
        with open(self.memory_file, "r", encoding='utf-8') as f:
            self.memory = json.load(f)

    def save_memory(self):
        with open(self.memory_file, "w", encoding='utf-8') as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=4)

    def add_entry(self, key, value):
        self.memory[key] = value
        self.save_memory()

    def get_entry(self, key):
        return self.memory.get(key, None)

    def remove_entry(self, key):
        if key in self.memory:
            del self.memory[key]
            self.save_memory()
