import pygame as pg
import sys
from config import *


class DungeonQuestGame:
    
    def __init__(self):
        pg.init()
        pg.display.set_caption("Dungeon Quest")
        
        self.screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pg.time.Clock()
        
        # Player as rectangle
        self.player_x = PLAYER_START_X
        self.player_y = PLAYER_START_Y
        self.player_size = TILE_SIZE   # Make player same size as tiles
        self.player_speed = PLAYER_DEFAULT_SPEED
        
        self.running = True

    def handle_input(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                self.running = False

        keys = pg.key.get_pressed()
        
        if keys[pg.K_w] or keys[pg.K_UP]:
            self.player_y -= self.player_speed
        if keys[pg.K_s] or keys[pg.K_DOWN]:
            self.player_y += self.player_speed
        if keys[pg.K_a] or keys[pg.K_LEFT]:
            self.player_x -= self.player_speed
        if keys[pg.K_d] or keys[pg.K_RIGHT]:
            self.player_x += self.player_speed

    def draw(self):
        self.screen.fill(color=(255, 255, 255)) 
        
        player_rect = pg.Rect(self.player_x, self.player_y, self.player_size, self.player_size)
        pg.draw.rect(self.screen, (0, 0, 255), player_rect)
        
        pg.display.flip()

    def run(self):
        while self.running:
            self.handle_input()
            self.draw()
            self.clock.tick(FPS)

        pg.quit()
        sys.exit()


def main():
    game = DungeonQuestGame()
    game.run()


if __name__ == "__main__":
    main()