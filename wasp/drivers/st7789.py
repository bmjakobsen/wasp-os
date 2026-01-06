# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Sitronix ST7789 display driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

    Although the ST7789 supports a variety of communication protocols currently
    this driver only has support for SPI interfaces. However it is structured
    such that other serial protocols can easily be added.
"""

import micropython

from micropython import const
from time import sleep_ms
import builtins

# register definitions
_SWRESET            = const(0x01)
_SLPIN              = const(0x10)
_SLPOUT             = const(0x11)
_NORON              = const(0x13)
_INVOFF             = const(0x20)
_INVON              = const(0x21)
_DISPOFF            = const(0x28)
_DISPON             = const(0x29)
_CASET              = const(0x2a)
_RASET              = const(0x2b)
_RAMWR              = const(0x2c)
_COLMOD             = const(0x3a)
_MADCTL             = const(0x36)

_VSCRDEF            = const(0x33)
_VSCSAD             = const(0x37)

_MAX_BUFFER_Y = const(320)

class ST7789(object):
    """Sitronix ST7789 display driver

    .. automethod:: __init__
    """
    def __init__(self, width, height):
        """Configure the size of the display.

        :param int width: Display width, in pixels
        :param int height: Display height in pixels
        """
        self.spec = None
        self.width = width
        self.height = height
        self.linebuffer = memoryview(bytearray(2 * width))
        command_buffer = memoryview(bytearray(4+6+2))
        self.window = command_buffer[0:4]
        self.vscsad = command_buffer[4:6]
        self.vscrdef = command_buffer[6:12]
        
        self.vscrdef[0] = 0
        self.vscrdef[1] = 0
        self.vscrdef[2] = (_MAX_BUFFER_Y>>8)&0xFF
        self.vscrdef[3] = _MAX_BUFFER_Y&0xFF
        self.vscrdef[4] = 0
        self.vscrdef[5] = 0

        self.vsc_line:int = 0
        self.init_display()

    def init_display(self):
        """Reset and initialize the display."""
        self.reset()

        self.write_cmd(_SLPOUT)
        sleep_ms(10)

        self.vscsad[0] = 0
        self.vscsad[1] = 0

        # Testing split rendering
        #self.vscsad[1] = 240
        #self.vsc_line = 240


        for cmd in (
            (_COLMOD,   b'\x05'), # MCU will send 16-bit RGB565
            (_MADCTL,   b'\x00'), # Left to right, top to bottom
            #(_INVOFF,   None), # Results in odd palette
            (_INVON,   None),
            (_NORON,   None),
        #    (_VSCRDEF,   self.vscrdef),
        #    (_VSCSAD,    self.vscsad)
        ):
            self.write_cmd(cmd[0])
            if not cmd[1] is None:
                self.write_data(cmd[1])
        self.wgl_fill(0, 0, 0, self.width, self.height)
        self.write_cmd(_DISPON)

        # From the point we sent the SLPOUT there must be a
        # 120ms gap before any subsequent SLPIN. In most cases
        # (i.e. when the SPI baud rate is slower than 8M then
        # that time already elapsed as we zeroed the RAM).
        #sleep_ms(125)

    def poweroff(self):
        """Put the display into sleep mode."""
        self.write_cmd(_SLPIN)
        sleep_ms(125)

    def poweron(self):
        """Wake the display and leave sleep mode."""
        self.write_cmd(_SLPOUT)
        sleep_ms(125)

    def invert(self, invert):
        """Invert the display.

        :param bool invert: True to invert the display, False for normal mode.
        """
        if invert:
            self.write_cmd(_INVON)
        else:
            self.write_cmd(_INVOFF)

    def mute(self, mute):
        """Mute the display.

        When muted the display will be entirely black.

        :param bool mute: True to mute the display, False for normal mode.
        """
        if mute:
            self.write_cmd(_DISPOFF)
        else:
            self.write_cmd(_DISPON)

    @micropython.viper
    def set_window(self, x:int, y:int, width:int, height:int):
        """Set the clipping rectangle.

        All writes to the display will be wrapped at the edges of the rectangle.

        :param x:  X coordinate of the left-most pixels of the rectangle
        :param y:  Y coordinate of the top-most pixels of the rectangle
        :param w:  Width of the rectangle, defaults to None (which means select
                   the right-most pixel of the display)
        :param h:  Height of the rectangle, defaults to None (which means select
                   the bottom-most pixel of the display)
        """
        write_cmd = self.write_cmd
        window:ptr8 = ptr8(self.window)
        write_data = self.write_data

        xp = x + width - 1
        yp = y + height - 1

        write_cmd(_CASET)
        window[0] = x >> 8
        window[1] = x & 0xff
        window[2] = xp >> 8
        window[3] = xp & 0xff
        write_data(window)

        write_cmd(_RASET)
        window[0] = y >> 8
        window[1] = y & 0xff
        window[2] = yp >> 8
        window[3] = yp & 0xff
        write_data(window)

        write_cmd(_RAMWR)


    def wgl_vscroll(self, pixels:int):
        vsc_line:int = self.vsc_line
        #ovsc_line = vsc_line
        vsc_line += pixels
        while vsc_line < 0:
            vsc_line += _MAX_BUFFER_Y
        while vsc_line >= _MAX_BUFFER_Y:
            vsc_line -= _MAX_BUFFER_Y
        self.vsc_line = vsc_line

        #print("VSCROLL: "+str(ovsc_line)+" => "+str(vsc_line))

        vscsad = self.vscsad
        vscsad[0] = (vsc_line>>8)&0xFF
        vscsad[1] = vsc_line&0xFF
        self.write_cmd(_VSCSAD)
        self.write_data(vscsad)

    #Temporarily Non-Native
    #@micropython.viper
    def wgl_fill(self, color:int, x:int, y:int, width:int, height:int):
        lbuffer = self.linebuffer
        #buf:ptr8 = ptr8(lbuffer)
        buf:memoryview = lbuffer
        scwidth:int = int(self.width)

        # Correct y variable
        y += int(self.vsc_line)
        while y < 0:
            y += _MAX_BUFFER_Y
        while y >= _MAX_BUFFER_Y:
            y -= _MAX_BUFFER_Y

        color &= 0xFFFF
        for xi in range(0, 2*scwidth, 2):
            buf[xi] = color >> 8
            buf[xi+1] = color & 0xff

        yp:int = y+height
        split_mode = False
        exl:int = 0
        if yp > _MAX_BUFFER_Y:
            exl = yp-_MAX_BUFFER_Y
            split_mode = True
        height -= exl


        quick_start = self.quick_start
        quick_end = self.quick_end
        write_data = self.quick_write
        set_window = self.set_window
        PyInt = builtins.int
        PyInt0 = PyInt(0)

        for sec in range(2):
            if sec == 1:
                if not split_mode:
                    break
                y = 0
                height = exl

            pixels:int = width*height
            full_rows:int = pixels//scwidth
            last_row:int = pixels%scwidth

            set_window(x, y, width, height)

            #print("FILL "+hex(color)+": ", x, y, width, height)

            quick_start()

            # Do the fill
            n:int = 0
            while n < full_rows:
                n += 1
                write_data(lbuffer)
            if last_row > 0:
                last_row <<= 1      # Last row x 2 to get number of bytes instead of number of pixels
                write_data(lbuffer[PyInt0:PyInt(last_row)])
            quick_end()

    #Temporarily Non-Native
    #@micropython.viper
    def wgl_blit(self, image, x:int, y:int):
        # Populate the line buffer
        lbuffer = self.linebuffer
        scwidth:int = int(self.width)

        # Correct y variable
        y += int(self.vsc_line)
        while y < 0:
            y += _MAX_BUFFER_Y
        while y >= _MAX_BUFFER_Y:
            y -= _MAX_BUFFER_Y

        width:int = int(image.width)
        height:int = int(image.height)
        yp:int = y+height
        split_mode = False
        exl:int = 0
        if yp > _MAX_BUFFER_Y:
            exl = yp-_MAX_BUFFER_Y
            split_mode = True
        height -= exl


        quick_start = self.quick_start
        quick_end = self.quick_end
        write_data = self.quick_write
        set_window = self.set_window
        read_pixels = image.read_pixels
        PyInt = builtins.int
        PyInt0 = PyInt(0)

        for sec in range(2):
            if sec == 1:
                if not split_mode:
                    break
                y = 0
                height = exl

            #print("BLIT:  X:"+str(x)+", Y:"+str(y)+", W:"+str(width)+", H:"+str(height)+"                    "+image.info())
            set_window(x, y, width, height)


            pixels:int = width*height

            n:int = 0
            quick_start()
            while True:
                r_read:int = scwidth
                if pixels < scwidth:
                    r_read = pixels
                # Read up to scwidth pixels into the buffer, method returns the number of pixels written
                n = int(read_pixels(True, lbuffer, r_read, 0))

                #print("Pixels Read:", n, "  ", lbuffer[PyInt0:PyInt(2*n)].hex(sep=' '))
                pixels -= n
                # Number lower than the requested number means end of stream
                if n < scwidth:
                    if n > 0:
                        n <<= 1         # Number of gotten pixels x2 to get number of gotten bytes
                        write_data(lbuffer[PyInt0:PyInt(n)])
                else:
                    write_data(lbuffer)
                if n < r_read or pixels <= 0:
                    break
            quick_end()




class ST7789_SPI(ST7789):
    """
    .. method:: quick_write(buf)

        Send data to the display as part of an optimized write sequence.

        :param bytes-like buf: Data, must be in a form that can be directly
                               consumed by the SPI bus.
    """
    def __init__(self, width, height, spi, cs, dc, res=None, rate=8000000):
        """Configure the display.

        :param int width: Width of the display
        :param int height: Height of the display
        :param machine.SPI spi: SPI controller
        :param machine.Pin cs: Pin (or signal) to use as the chip select
        :param machine.Pin dc: Pin (or signal) to use to switch between data
                               and command mode.
        :param machine.Pin res: Pin (or signal) to, optionally, use to reset
                                the display.
        :param int rate: SPI bus frequency
        """
        self.quick_write = spi.write
        self.cs = cs.value
        self.dc = dc.value
        self.res = res
        self.rate = rate
        self.cmd = memoryview(bytearray(1))

        #spi.init(baudrate=self.rate, polarity=1, phase=1)
        cs.init(cs.OUT, value=1)
        dc.init(dc.OUT, value=0)
        if res:
            res.init(res.OUT, value=0)

        super().__init__(width, height)

    def reset(self):
        """Reset the display.

        Uses the hardware reset pin if there is one, otherwise it will issue
        a software reset command.
        """
        if self.res:
            self.res(0)
            sleep_ms(10)
            self.res(1)
        else:
            self.write_cmd(_SWRESET)
        sleep_ms(125)

    #Temporarily Non-Native
    @micropython.viper
    def write_cmd(self, cmd:int):
        """Send a command opcode to the display.

        :param sequence cmd: Command, will be automatically converted so it can
                             be issued to the SPI bus.
        """
        dc = self.dc
        cs = self.cs
        c:ptr8 = ptr8(self.cmd)
        #c:memoryview = self.cmd

        dc(0)
        cs(0)
        c[0] = cmd
        self.quick_write(c)
        cs(1)
        dc(1)

    def write_data(self, buf):
        """Send data to the display.

        :param bytearray buf: Data, must be in a form that can be directly
                              consumed by the SPI bus.
        """
        cs = self.cs
        cs(0)
        self.quick_write(buf)
        cs(1)

    def quick_start(self):
        """Prepare for an optimized write sequence.

        Optimized write sequences allow applications to produce data in chunks
        without having any overhead managing the chip select.
        """
        self.cs(0)

    def quick_end(self):
        """Complete an optimized write sequence."""
        self.cs(1)
