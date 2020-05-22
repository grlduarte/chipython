'''
gduarte@astro.ufsc.br
Created on 20-mai-2020
'''
from sys import argv
from tkinter import Tk

from scripts.cpu import Processor
from scripts.video import Video

def main(rom):
    rom = rom.upper()
    root = Tk()
    root.title(f'Chip8 - {rom}')
    game = Video(root, scale=20)
    game.start(f'roms/{rom}')
    root.mainloop()

if __name__ == '__main__':
    main(argv[1])

