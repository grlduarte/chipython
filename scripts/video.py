'''
gduarte@astro.ufsc.br
Created on 20-mai-2020
'''

from tkinter import *
from scripts.cpu import Processor

class Video(Canvas):
    def __init__(self, master, scale=5):
        self.x_size = 64
        self.y_size = 32
        self.scale = scale
        self.width = scale * self.x_size
        self.height = scale * self.y_size
        super().__init__(master, width=self.width,
                         height=self.height, bg='black')
        self.keyboard = {'1': 0x1, '2': 0x2, '3': 0x3, '4': 0xC,
                         'q': 0x4, 'w': 0x5, 'e': 0x6, 'r': 0xD,
                         'a': 0x7, 's': 0x8, 'd': 0x9, 'f': 0xE,
                         'z': 0xA, 'x': 0x0, 'c': 0xB, 'v': 0xF}
        self.pack()

    def start(self, rom):
        self.bind_all("<KeyPress>", self.press_key)
        self.bind_all("<KeyRelease>", self.release_key)
        self.pressed_keys = []
        self.last_key = IntVar(self)
        self.cpu = Processor(video=self)
        self.cpu.load_program(rom)
        self.step()

    def press_key(self, e):
        key = e.keysym
        try:
            self.last_key.set(self.keyboard[key])
            self.pressed_keys.append(self.keyboard[key])
        except KeyError:
            pass
        if key == 'Escape':
            self.last_key.set(0)
            self.master.destroy()

    def release_key(self, e):
        key = e.keysym
        try:
            self.pressed_keys.remove(self.keyboard[key])
        except (ValueError, KeyError):
            pass

    def step(self):
        self.cpu.cycle()
        self.sound_buzzer()
        self.ident = self.after(10, self.step)

    def stop(self):
        self.after_cancel(self.ident)

    def update(self):
        self.delete(ALL)
        display = repr(self.cpu).split('\n')
        for j, line in enumerate(display):
            for i, px in enumerate(line):
                if (px == '1'):
                    coords = (i*self.scale, j*self.scale,
                              (i+1)*self.scale, (j+1)*self.scale)
                    self.create_rectangle(coords, fill='white')

    def sound_buzzer(self):
        if self.cpu.buzzing:
            self['bg'] = 'red'
        else:
            self['bg'] = 'black'
