# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

""" Simulated ST7789 display and CST816S touchscreen. """

import warnings
warnings.simplefilter("ignore", lineno=58)

import sys
import sdl2
import sdl2.ext
import numpy as np
from PIL import Image
import wasp
import os

DISPOFF = 0x28
DISPON = 0x29
CASET = 0x2a
RASET = 0x2b
RAMWR = 0x2c

VSCRDEF = 0x33
VSCSAD = 0x37

WIDTH = 240
HEIGHT = 240
XHEIGHT = 320

SKIN = {
    'fname' : 'res/simulator_skin.png',
    'size' : (337+63+240, 427),
    'button_profile' : 9,
    'offset' : (53, 93),
    'roffset': (400, 50)
}





class ST7789Sim(object):
    def __init__(self):
        self.x = 0
        self.y = 0
        self.colclip = [0, WIDTH-1]
        self.rowclip = [0, HEIGHT-1]
        self.cmd = 0
        self.mute = False

        self.vsc_line = None
        self.display_lines = sorted(list(range(0, HEIGHT)))
        self.BUFFER_HEIGHT = HEIGHT

    def write(self, data):
        # Converting data to a memoryview ensures we act more like spi.write()
        # when running in a real device (e.g. data must be  bytes-like object
        # that implements the buffer protocol)
        data = memoryview(data)

        if len(data) == 1:
            # Assume if we get a byte at a time then it is command.
            # This is a simplification do we don't have to track
            # the D/C pin from within the simulator.
            cmd = data[0]
            if cmd == DISPOFF:
                self.mute = True
            elif cmd == DISPON:
                self.mute = False
                window.refresh()
            else:
                self.cmd = data[0]

        elif self.cmd == VSCRDEF:
            assert(data[0] == 0 and data[1] == 0 and data[4] == 0 and data[5] == 0)
            assert( (data[2]<<8)+(data[3]&0xFF) == XHEIGHT )
            self.vsc_line = 0
            self.BUFFER_HEIGHT = XHEIGHT
            self.display_lines = sorted(list(range(0, HEIGHT)))

        elif self.cmd == VSCSAD:
            # Ensure that a VSCRDEF has been ran before
            assert(self.vsc_line is not None)
            vsc_line = (data[0]<<8)+data[1]&0xFF
            # Assert than the new vsc_line is valid
            assert(vsc_line >= 0 and vsc_line < XHEIGHT)
            self.vsc_line = vsc_line
            if vsc_line + HEIGHT > XHEIGHT:
                xl = (vsc_line + HEIGHT) - XHEIGHT
                xm = vsc_line+xl
                if xm > XHEIGHT:
                    xm = XHEIGHT
                self.display_lines = sorted(list(range(vsc_line, xm)))+sorted(list(range(0, xl)))
            else:
                self.display_lines = sorted(list(range(vsc_line, vsc_line+HEIGHT)))

        elif self.cmd == CASET:
            self.colclip[0] = (data[0] << 8) + data[1]
            assert(self.colclip[0] >= 0 and self.colclip[0] < 240)
            self.colclip[1] = (data[2] << 8) + data[3]
            assert(self.colclip[1] >= 0 and self.colclip[1] < 240)
            self.x = self.colclip[0]

        elif self.cmd == RASET:
            self.rowclip[0] = (data[0] << 8) + data[1]
            assert(self.rowclip[0] >= 0 and self.rowclip[0] < self.BUFFER_HEIGHT)
            self.rowclip[1] = (data[2] << 8) + data[3]
            assert(self.rowclip[1] >= 0 and self.rowclip[1] < self.BUFFER_HEIGHT)
            self.y = self.rowclip[0]

        elif self.cmd == RAMWR:
            #pixelview = sdl2.ext.PixelView(windowsurface)
            pixelview = sdl2.ext.pixels2d(windowsurface)

            half = False
            for d in data:
                if not half:
                    rgb = d << 8
                    half = True
                    continue
                rgb |= d
                half = False

                #pixel = ((rgb & 0xf800) >> 8,
                #         (rgb & 0x07e0) >> 3,
                #         (rgb & 0x001f) << 3)
                pixel = (((rgb & 0xf800) << 8) +
                         ((rgb & 0x07e0) << 5) +
                         ((rgb & 0x001f) << 3))
            

                pv_x2 = self.x + SKIN['radjust'][0]
                pv_y2 = self.y + SKIN['radjust'][1]
                pixelview[pv_x2][pv_y2] = pixel
                try:
                    pv_x1 = self.x + SKIN['adjust'][0]
                    # Display lines is set up in a way where it is a mapping where the index of the line in the wider buffer, is the line where it belongs in the real buffer
                    pv_y1 = self.display_lines.index(self.y) + SKIN['adjust'][1]
                    pixelview[pv_x1][pv_y1] = pixel
                except ValueError:
                    pass

                self.x += 1
                if self.x > self.colclip[1]:
                    self.x = self.colclip[0]
                    self.y += 1
                if self.y > self.rowclip[1]:
                    self.y = self.rowclip[0]
            
            # Forcibly release the surface to ensure it is unlocked
            del pixelview
            if not self.mute:
                window.refresh()

class CST816SSim():
    def __init__(self):
        self.regs = bytearray(64)

    def readfrom_mem_into(self, addr, reg, dbuf, pins):
        tick(pins)

        if not self.regs[1]:
            raise OSError

        dbuf[:] = self.regs[reg:len(dbuf)+reg]
        if self.regs[3]:
            self.regs[3] = 0
        else:
            self.regs[1] = 0

    def writeto_mem(self, addr, reg, buf, pins):
        tick(pins)

        if reg == 0xa5:
            # This will be a sleep command... which we can ignore
            return

        raise OSError

    def handle_key(self, key, pins):
        """Use key presses to provoke different touchscreen events.

        Note: The Down key provokes an upward swipe and vice versa.
              Same for left and right. That is because the swipe up
              gesture means show me the screen the is below me (hence
              the controls are inverted compared to joystick-like
              direction control).
        """
        if key.keysym.sym == sdl2.SDLK_DOWN:
            self.regs[1] = 2
        elif key.keysym.sym == sdl2.SDLK_UP:
            self.regs[1] = 1
        elif key.keysym.sym == sdl2.SDLK_LEFT:
            self.regs[1] = 4
        elif key.keysym.sym == sdl2.SDLK_RIGHT:
            self.regs[1] = 3
        elif key.keysym.sym == sdl2.SDLK_n:
            # Allow NEXT to be tested on the simulator
            self.regs[1] = 253
        self.regs[3] = 0x80
        self.raise_interrupt(pins)

    def handle_mousebuttondown(self, button, pins):
        self.down_x = button.x
        self.down_y = button.y

        if self.down_x < 50:
            pins['BUTTON'].value(0)


    def handle_mousebuttonup(self, button, pins):
        if self.down_x < 50:
            pins['BUTTON'].value(1)
            return

        down_x = max(0, min(239, self.down_x-SKIN['adjust'][0]))
        down_y = max(0, min(239, self.down_y-SKIN['adjust'][1]))
        up_x = max(0, min(239, button.x-SKIN['adjust'][0]))
        up_y = max(0, min(239, button.y-SKIN['adjust'][1]))
        mv_x = up_x - down_x
        mv_y = up_y - down_y

        # Swipe detection
        if abs(mv_x) + abs(mv_y) < 24:
            self.regs[1] = 5
        elif abs(mv_x) > abs(mv_y):
            self.regs[1] = 4 if mv_x > 0 else 3
        else:
            self.regs[1] = 1 if mv_y > 0 else 2

        self.regs[4] = up_x;
        self.regs[6] = up_y;
        self.raise_interrupt(pins)

    def press(self, x, y):
        pins = wasp.watch.Pin.pins
        self.regs[1] = 5
        self.regs[4] = x
        self.regs[6] = y
        self.raise_interrupt(pins)

    def swipe(self, direction):
        pins = wasp.watch.Pin.pins
        if direction ==' up':
            self.regs[1] = 1
        elif direction == 'down':
            self.regs[1] = 2
        elif direction == 'left':
            self.regs[1] = 4
        elif direction == 'right':
            self.regs[1] = 3
        elif direction == 'next':
            # Allow NEXT to be tested on the simulator
            self.regs[1] = 253
        self.regs[3] = 0x80
        self.raise_interrupt(pins)

    def raise_interrupt(self, pins):
        pins['TP_INT'].raise_irq()

# Derive some extra values for padding the display
SKIN['left_pad'] = 9
SKIN['right_pad'] = SKIN['left_pad'] + SKIN['button_profile']
SKIN['top_pad'] = 3
SKIN['bottom_pad'] = 3
SKIN['window'] = (SKIN['size'][0] + SKIN['left_pad'] + SKIN['right_pad'],
                  SKIN['size'][1] + SKIN['top_pad'] + SKIN['bottom_pad'])
SKIN['adjust'] = (SKIN['offset'][0] + SKIN['left_pad'],
                  SKIN['offset'][1] + SKIN['top_pad'])
SKIN['radjust'] = (SKIN['roffset'][0], SKIN['roffset'][1])

sdl2.ext.init()
window = sdl2.ext.Window("ST7789", size=SKIN['window'])



window.show()
windowsurface = window.get_surface()
sdl2.ext.fill(windowsurface, (0xff, 0xff, 0xff))
sdl2.ext.fill(windowsurface, (0,0,0), (SKIN['roffset'][0], SKIN['roffset'][1], WIDTH, XHEIGHT))
skin = sdl2.ext.load_image(SKIN['fname'])
sdl2.SDL_BlitSurface(skin, None, windowsurface, sdl2.SDL_Rect(
        SKIN['left_pad'], SKIN['top_pad'], SKIN['size'][0], SKIN['size'][1]))
sdl2.SDL_FreeSurface(skin)
window.refresh()


spi_st7789_sim = ST7789Sim()
i2c_cst816s_sim = CST816SSim()

def save_image(surface, fname):
    """Save a surface as an image."""
    raw = sdl2.ext.pixels2d(surface)

    # Crop and swap the axes to ensure the final rotation is correct
    cropped = raw[SKIN['top_pad']:-SKIN['bottom_pad']]
    cropped = np.swapaxes(cropped, 0, 1)
    cropped = cropped[SKIN['left_pad']:-SKIN['right_pad']]

    # Split into r, g and b
    r = cropped >> 16
    g = (cropped >> 8) & 0xff
    b = cropped & 0xff

    # Combine into the final pixel data
    rgb = np.uint8(np.dstack((r, g, b)))

    # Save the image
    Image.fromarray(rgb).save(fname)

def tick(pins):
    events = sdl2.ext.get_events()
    for event in events:
        if event.type == sdl2.SDL_QUIT:
            sdl2.ext.quit()
            sys.exit(0)
        elif event.type == sdl2.SDL_MOUSEBUTTONDOWN:
            i2c_cst816s_sim.handle_mousebuttondown(event.button, pins)
        elif event.type == sdl2.SDL_MOUSEBUTTONUP:
            i2c_cst816s_sim.handle_mousebuttonup(event.button, pins)
        elif event.type == sdl2.SDL_KEYDOWN:
            if event.key.keysym.sym == sdl2.SDLK_s:
                fname = f'res/{wasp.system.app.NAME}App.png'.replace(' ', '')
                save_image(windowsurface, fname)
                print(f'Saved: {fname}')
            elif event.key.keysym.sym == sdl2.SDLK_TAB:
                pins['BUTTON'].value(0)
            else:
                i2c_cst816s_sim.handle_key(event.key, pins)
        elif event.type == sdl2.SDL_KEYUP:
            if event.key.keysym.sym == sdl2.SDLK_TAB:
                pins['BUTTON'].value(1)
        else:
            #print(event)
            pass
