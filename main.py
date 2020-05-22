'''
gduarte@astro.ufsc.br
Created on 20-mai-2020
'''
from sys import argv
import tkinter as tk

from cpu import *
from video import *

def main(rom):
    rom = rom.upper()
    root = Tk()
    root.title(f'Chip8 - {rom}')
    game = Video(root, scale=20)
    game.start(f'roms/{rom}')
    root.mainloop()

if __name__ == '__main__':
    main(argv[1])

