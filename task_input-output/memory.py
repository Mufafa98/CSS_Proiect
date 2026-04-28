class MemoryManager:
    def __init__(self, limit):
        self.limit = limit
        self.used = 0
        self.ram = []
        self.lru = []

    def access(self, p):
        if p in self.lru:
            self.lru.remove(p)
        self.lru.append(p)

    def can_fit(self, p):
        return self.used + p.mem <= self.limit

    def load(self, p):
        if p.in_memory:
            self.access(p)
            return True

        if not self.can_fit(p):
            return False

        self.used += p.mem
        p.in_memory = True
        self.access(p)
        return True

    def evict_lru(self):
        if not self.lru:
            return None

        victim = self.lru.pop(0)
        victim.in_memory = False
        self.used -= victim.mem
        return victim
    