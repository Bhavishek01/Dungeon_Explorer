from .monster_base import MonsterBase


class Monster3(MonsterBase):
    def __init__(self, data, tile_size: int):
        super().__init__(data, tile_size)
        self.kind = "monster3"
