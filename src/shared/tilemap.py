# ============================================================
# shared/tilemap.py
# Tile type constants. Duplicated (not imported) into client/config.py
# on purpose: the client and server are separate processes/repos in your
# architecture, so this file is the single source of truth you copy from,
# not a runtime dependency both sides import.
# ============================================================

TILE_WALL = 0       # collidable
TILE_STONE = 1      # collidable
TILE_GROUND = 2      # walkable
TILE_WATER = 3       # walkable, slows player (see player.iswater in old Java)
TILE_TREASURE = 4    # collidable

WALKABLE_TILES = (TILE_GROUND, TILE_WATER)
COLLIDABLE_TILES = (TILE_WALL, TILE_STONE, TILE_TREASURE)
