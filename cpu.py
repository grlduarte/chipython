'''
gduarte@astro.ufsc.br
Created on 20-mai-2020
'''

from random import randint
import tkinter as tk


class UnexpectedOpcode(Exception):
    pass


class Processor:
    def __init__(self, video=None):
        '''
        Parameters
        ----------
        video : object
            Instance containing update_grid and draw_grid methods.
        '''
        self.memory_size = 4096
        self.video = video
        self.reset()

        self.table = {0x0: self.cls_ret,
                      0x1: self.jp_addr,
                      0x2: self.call_addr,
                      0x3: self.se_vx_byte,
                      0x4: self.sne_vx_byte,
                      0x5: self.se_vx_vy,
                      0x6: self.ld_vx_byte,
                      0x7: self.add_vx_byte,
                      0x8: self.register_operations,
                      0x9: self.sne_vx_vy,
                      0xA: self.ld_i_addr,
                      0xB: self.jp_v0_addr,
                      0xC: self.rnd_vx_byte,
                      0xD: self.drw_vx_vy_nibble,
                      0xE: self.key_operations,
                      0xF: self.misc_operations,
                      }

        # Operations to decode if opcode starts with 0x0
        self.cls_ret_table = {0x00E0: self.cls,
                              0x00EE: self.ret,
                              }

        # Operations to decode if opcode starts with 0x8
        self.reg_op_table = {0x0: self.ld_vx_vy,
                             0x1: self.or_vx_vy,
                             0x2: self.and_vx_vy,
                             0x3: self.xor_vx_vy,
                             0x4: self.add_vx_vy,
                             0x5: self.sub_vx_vy,
                             0x6: self.shr_vx,
                             0x7: self.subn_vx_vy,
                             0xE: self.shl_vx,
                             }

        # Operations to decode if opcode starts with 0xE
        self.key_op_table = {0x9E: self.skp_vx,
                             0xA1: self.sknp_vx,
                             }

        # Operations to decode if opcode starts with 0xF
        self.misc_op_table = {0x07: self.ld_vx_dt,
                              0x0A: self.ld_vx_key,
                              0x15: self.ld_dt_vx,
                              0x18: self.ld_st_vx,
                              0x1E: self.add_i_vx,
                              0x29: self.ld_f_vx,
                              0x33: self.ld_b_vx,
                              0x55: self.ld_i_vx,
                              0x65: self.ld_vx_i,
                              }

    def __repr__(self):
        lines = ''
        i = 0
        for px in self.display:
            lines += str(px)
            if i == 63:
                lines += '\n'
                i = 0
            else:
                i += 1
        return lines

    def reset(self):
        self.memory = bytearray(self.memory_size)
        self.register = bytearray(16)
        self.register_i = 0
        self.set_display()
        self.load_fontset()
        # I won't use a stack pointer, since it'll always point at stack[-1]
        self.stack = []
        
        self.dt = 0
        self.st = 0
        self.pointer = 0x200

    def set_display(self):
        self.display = [0] * (32 * 64)

    def load_fontset(self):
        self.load_program('fontset.bin', start_point=0)

    def load_program(self, rom, start_point=0x200):
        with open(f'{rom}', 'rb') as f:
            p = f.read()
        # 0x200-0xFFF - Program ROM and work RAM
        for i, op in enumerate(p):
            self.memory[start_point+i] = op
        print(f"DEBUG: successfully loaded {rom}")

    def cycle(self):
        # Chip8 uses big-endian storage for its 2 bytes opcodes
        # That means that the most important (hence the leftier)
        # is the first byte.
        # The bitwise operator << 8 moves the byte 8 bits to the left
        # and the | operator "sums" them both
        # X << n -> X * 2**n
        # X >> n -> X // 2**n
        byte_1 = self.memory[self.pointer]
        byte_2 = self.memory[self.pointer + 1]
        opcode = byte_1 << 8 | byte_2
        self.pointer += 2
        
        try:
            self.table[opcode >> 12](opcode)
        except KeyError:
            raise UnexpectedOpcode(hex(opcode))

        if self.dt > 0:
            self.dt -= 1
        if self.st > 0:
            self.st -= 1
            self.buzzing = True
        else:
            self.buzzing = False
        
    # Instructions methods names and docstrings are accordingly
    # to devernay.free.fr/hacks/chip8/C8TECH10.HTM#Annn
    ########### Instructions ###########
    def cls_ret(self, opcode):
        self.cls_ret_table[opcode & 0xFF](opcode)

    def cls(self, opcode):
        '''
        Clear the display and increases the pointer by 2.

        opcode == 0x00E0
        '''
        self.set_display()
        self.video.update()

    def ret(self, opcode):
        '''
        Return from a subroutine. The pop method will return the
        last item from the stack list and remove it from there.

        opcode == 0x00EE
        '''
        self.pointer = self.stack.pop() 
        
    def jp_addr(self, opcode):
        '''
        Jump to address NNN.

        opcode == 0x1NNN
        '''
        addr = (opcode & 0x0FFF)
        self.pointer = addr 

    def call_addr(self, opcode):
        '''
        Call routine at address NNN.
        
        opcode == 0x2NNN
        '''
        addr = (opcode & 0x0FFF)
        self.stack.append(self.pointer)
        self.pointer = addr

    def se_vx_byte(self, opcode):
        '''
        Skip next instruction if Vx == NN.

        opcode == 0x3XNN
        '''
        x = (opcode & 0x0F00) >> 8
        kk = (opcode & 0x00FF)
        if self.register[x] == kk:
            self.pointer += 2

    def sne_vx_byte(self, opcode):
        '''
        Skip next instruction if Vx != NN.

        opcode == 0x4XNN
        '''
        x = (opcode & 0x0F00) >> 8
        kk = (opcode & 0x00FF)
        if not (self.register[x] == kk):
            self.pointer += 2

    def se_vx_vy(self, opcode):
        '''
        Skip next instruction if Vx = Vy.

        opcode == 0x5XY0
        '''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        if self.register[x] == self.register[y]:
            self.pointer += 2

    def ld_vx_byte(self, opcode):
        '''
        Set Vx = NN.

        opcode == 0x6XNN
        '''
        x = (opcode & 0x0F00) >> 8
        kk = (opcode & 0x00FF)
        self.register[x] = kk

    def add_vx_byte(self, opcode):
        '''
        Set Vx = Vx + NN.

        opcode == 0x7XNN
        '''
        x = (opcode & 0x0F00) >> 8
        kk = (opcode & 0x00FF)
        value = self.register[x] + kk
        self.register[x] = (value & 0xFF)

    def register_operations(self, opcode):
        self.reg_op_table[opcode & 0x000F](opcode)

    def ld_vx_vy(self, opcode):
        '''
        Set Vx = Vy.

        opcode == 0x8XY0 '''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        self.register[x] = self.register[y]

    def or_vx_vy(self, opcode):
        '''
        Set Vx = Vx OR Vy.
        
        opcode == 0x8XY1
        '''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        self.register[x] |= self.register[y]

    def and_vx_vy(self, opcode):
        '''
        Set Vx = Vx AND Vy.

        opcode == 0x8XY2
        '''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        self.register[x] &= self.register[y]

    def xor_vx_vy(self, opcode):
        '''
        Set Vx = Vx XOR Vy.
        
        opcode == 0x8XY3
        '''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        self.register[x] ^= self.register[y]

    def add_vx_vy(self, opcode):
        '''
        Set Vx = Vx + Vy, set VF = carry.

        opcode == 0x8XY4 '''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        value = self.register[x] + self.register[y]
        try:
            self.register[x] = value
            self.register[0xF] = 0
        except ValueError:
            self.register[x] = (value & 0xFF)
            self.register[0xF] = 1

    def sub_vx_vy(self, opcode):
        '''
        Set Vx = Vx - Vy, set VF = NOT borrow.

        opcode == 0x8XY5
        '''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        value = self.register[x] - self.register[y]
        try:
            self.register[x] = value
            self.register[0xF] = 1
        except ValueError:
            self.register[x] = (value & 0xFF)
            self.register[0xF] = 0

    def shr_vx(self, opcode):
        '''
        Set Vx = Vx SHR 1.

        If the least-significant bit of Vx is 1, then VF is set to 1, otherwise 0.
        Then Vx is divided by 2 (in other words, loses its rightmost bit).
        
        opcode == 0x8XY6
        '''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        self.register[0xF] = (self.register[y] & 0x01)
        self.register[x] = self.register[y] >> 1

    def subn_vx_vy(self, opcode):
        '''
        Set Vx = Vy - Vx, set VF = NOT borrow.

        opcode == 0x8XY7
        '''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        value = self.register[y] - self.register[x]
        try:
            self.register[x] = value
            self.register[0xF] = 1
        except ValueError:
            self.register[x] = (value & 0xFF)
            self.register[0xF] = 0

    def shl_vx(self, opcode):
        '''
        Set Vx = Vx SHL 1.

        If the most-significant bit of Vx is 1, then VF is set to 1,
        otherwise to 0. Then Vx is multiplied by 2 (ie, gains a 
        bit to the right).

        opcode == 0x8XYE
        '''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        self.register[0xF] = (self.register[y] & 0x80) >> 7
        self.register[x] = self.register[y] << 1

    def sne_vx_vy(self, opcode):
        '''
        Skip next instruction if Vx != Vy.

        opcode == 0x9XY0
        '''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        if not (self.register[x] == self.register[y]):
            self.pointer += 2

    def ld_i_addr(self, opcode):
        '''
        Set I = NNN.

        opcode == 0xANNN
        '''
        addr = (opcode & 0x0FFF)
        self.register_i = addr

    def jp_v0_addr(self, opcode):
        '''
        Jump to location nnn + V0.
        
        opcode == 0xBXNN
        '''
        addr = (opcode & 0x0FFF)
        self.pointer = addr + self.register[0x0]

    def rnd_vx_byte(self, opcode):
        '''
        Set Vx = random byte AND NN.

        opcode == 0xCXNN
        '''
        x = (opcode & 0x0F00) >> 8
        kk = (opcode & 0x00FF)
        self.register[x] = (randint(0, 255) & kk)

    def drw_vx_vy_nibble(self, opcode):
        '''
        Display n-byte sprite starting at memory location I at (Vx, Vy),
        set VF = collision.

        opcode == 0xDXYN
        '''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        n_bytes = (opcode & 0x000F)
        x_0 = self.register[x]
        y_0 = self.register[y]

        for j in range(n_bytes):
            byte = f'{self.memory[self.register_i + j]:08b}'
            for i, px in enumerate(byte):
                try:
                    idx = x_0 + i + (y_0 + j) * 64
                    px = int(px)
                    px_old = self.display[idx]
                    px_new = px_old ^ px
                    if (px_old == 1) and (px_new == 0):
                        self.register[0xF] = 1
                    self.display[idx] = px_new
                except IndexError:
                    print("DEBUG: index out of range when drawing sprite")
        self.video.update()

    def key_operations(self, opcode):
        self.key_op_table[opcode & 0x00FF](opcode)

    def skp_vx(self, opcode):
        '''
        Skip next instruction if key with the value of Vx is pressed.

        opcode == 0xEX9E
        '''
        x = (opcode & 0x0F00) >> 8
        key = self.register[x]
        if key in self.video.pressed_keys:
            self.pointer += 2

    def sknp_vx(self, opcode):
        '''
        Skip next instruction if key with the value of Vx is not pressed.

        opcode == 0xEXA1
        '''
        x = (opcode & 0x0F00) >> 8
        key = self.register[x]
        if not (key in self.video.pressed_keys):
            self.pointer += 2

    def misc_operations(self, opcode):
        self.misc_op_table[opcode & 0x00FF](opcode)

    def ld_vx_dt(self, opcode):
        '''
        Set Vx = delay timer value.

        opcode == 0xFX07
        '''
        x = (opcode & 0x0F00) >> 8
        self.register[x] = self.dt
        
    def ld_vx_key(self, opcode):
        '''
        Wait for a key press, store the value of the key in Vx.

        opcode == 0xFX0A
        '''
        x = (opcode & 0x0F00) >> 8
        self.video.waitvar(self.video.last_key)
        self.register[x] = self.video.last_key.get()

    def ld_dt_vx(self, opcode):
        '''
        Set delay timer = Vx.

        opcode == 0xFX15
        '''
        x = (opcode & 0x0F00) >> 8
        self.dt = self.register[x]

    def ld_st_vx(self, opcode):
        '''
        Set sound timer = Vx.

        opcode == 0xFX18
        '''
        x = (opcode & 0x0F00) >> 8
        self.st = self.register[x]

    def add_i_vx(self, opcode):
        '''
        Set I = I + Vx.

        opcode == 0xFX1E
        '''
        x = (opcode & 0x0F00) >> 8
        self.register_i += self.register[x]

    def ld_f_vx(self, opcode):
        '''
        Set I = location of sprite for digit Vx.
        A Chip 8 letter sprite it's 5 bytes long, so the * 5.

        opcode == 0xFX29
        '''
        x = (opcode & 0x0F00) >> 8
        self.register_i = self.register[x] * 5

    def ld_b_vx(self, opcode):
        '''
        Store BCD representation of Vx in memory locations I, I+1,
        and I+2.

        opcode == 0xFX33
        '''
        x = (opcode & 0x0F00) >> 8
        decimal = f"{self.register[x]:03d}"
        for i, digit in enumerate(decimal):
            self.memory[self.register_i + i] = int(digit)

    def ld_i_vx(self, opcode):
        '''
        Store registers V0 through Vx in memory starting at location I.

        opcode == 0xFX55
        '''
        x = (opcode & 0x0F00) >> 8
        for i in range(x + 1):
            self.memory[self.register_i + i] = self.register[i]

    def ld_vx_i(self, opcode):
        '''
        Read registers V0 through Vx from memory starting at location I.

        opcode == 0xFX65
        '''
        x = (opcode & 0x0F00) >> 8
        for i in range(x + 1):
            self.register[i] = self.memory[self.register_i + i]
