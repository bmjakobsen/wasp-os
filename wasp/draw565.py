# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""RGB565 drawing library
~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import array
import fonts.sans24
import math
import micropython

from watchgl import MonoRleImageStream, Rle2ImageStream

from micropython import const

R = const(0b11111_000000_00000)
G = const(0b00000_111111_00000)
B = const(0b00000_000000_11111)


class Draw565(object):
    """Drawing library for RGB565 displays.

    A full framebufer is not required although the library will
    'borrow' a line buffer from the underlying display driver.

    .. automethod:: __init__
    """

    def __init__(self, wg):
        """Initialise the library.

        Defaults to white-on-black for monochrome drawing operations
        and 24pt Sans Serif text.
        """



        self.wg = wg

        self._rle_stream = MonoRleImageStream(wg.display.spec.color_format, memoryview(b'\x08'), 8, 1)
        self._rle2_stream = Rle2ImageStream(wg.display.spec.color_format, memoryview(b'\x08'), 8, 1)

        self._rle_stream._set_color(0, 0)
        self._rle_stream._set_color(1, 0xFFFF)

        self._rle2_stream._set_color(0, 0)
        self._rle2_stream._set_color(1, 0x4a69)
        self._rle2_stream._set_color(2, 0x7bef)
        self._rle2_stream._set_color(3, 0xFFFF)

        self.reset()

    def reset(self):
        """Restore the default colours and font.

        Default colours are white-on-block (white foreground, black
        background) and the default font is 24pt Sans Serif."""
        self.set_color(0xffff)
        self.wg.set_font(fonts.sans24)

    def fill(self, bg=None, x=0, y=0, w=None, h=None):
        """Draw a solid colour rectangle.

        If no arguments a provided the whole display will be filled with
        the background colour (typically black).

        :param bg: Background colour (in RGB565 format)
        :param x:  X coordinate of the left-most pixels of the rectangle
        :param y:  Y coordinate of the top-most pixels of the rectangle
        :param w:  Width of the rectangle, defaults to None (which means select
                   the right-most pixel of the display)
        :param h:  Height of the rectangle, defaults to None (which means select
                   the bottom-most pixel of the display)
        """
        if bg is None:
            bg = self._bg
        if w is None:
            w = self.wg.display.spec.width - x
        if h is None:
            h = self.wg.display.spec.height - y

        remaining = w * h
        if remaining == 0:
          return

        self.wg.fill(bg, x, y, w, h)



    def rleblit(self, image, pos=(0, 0), fg=0xffff, bg=0):
        x, y = pos
        (sx, sy, image_data) = image
        stream = self._rle_stream
        stream._setup(image_data, sx, sy)
        stream._set_color(0, bg)
        stream._set_color(1, fg)
        self.wg.blit(stream, x, y)

    def blit(self, image, x, y, fg=0xffff, c1=0x4a69, c2=0x7bef):
        """Decode and draw an encoded image.

        :param image: Image data in either 1-bit RLE or 2-bit RLE formats. The
                      format will be autodetected
        :param x: X coordinate for the left-most pixels in the image
        :param y: Y coordinate for the top-most pixels in the image
        """
        if len(image) == 3:
            self.rleblit(image, pos=(x, y), fg=fg)
        else: #elif image[0] == 2:
            sx = image[1]
            sy = image[2]
            image_data = image[3:]
            stream = self._rle2_stream
            stream._setup(image_data, sx, sy)
            stream._set_color(1, c1)
            stream._set_color(2, c2)
            stream._set_color(3, fg)
            self.wg.blit(stream, x, y)

    def set_color(self, color, bg=0):
        """Set the foreground and background colours.

        The supplied colour will be used for all monochrome drawing operations.
        If no background colour is provided then the background will be set
        to black.

        :param color: Foreground colour
        :param bg:    Background colour, defaults to black
        """
        self._bg = bg
        self.wg._set_bgcolor(bg)
        self._fg = color

    def set_font(self, font):
        """Set the font used for rendering text.

        :param font:  A font module generated using ``font_to_py.py``.
        """
        self.wg.set_font(font)
        self._font = font

    def string(self, s, x, y, width=None, right=False):
        """Draw a string at the supplied position.

        :param s:     String to render
        :param x:     X coordinate for the left-most pixels in the image
        :param y:     Y coordinate for the top-most pixels in the image
        :param width: If no width is provided then the text will be left
                      justified, otherwise the text will be centred within the
                      provided width and, importantly, the remaining width will
                      be filled with the background colour (to ensure that if
                      we update one string with a narrower one there is no
                      need to "undraw" it)
        :param right: If True (and width is set) then right justify rather than
                      centre the text
        """
        fg = self._fg
        bg = self._bg


        rx = 0
        if width:
            (w, h) = self.wg.string_bounding_box(s)
            if right:
                leftpad = width - w
                rightpad = 0
            else:
                leftpad = (width - w) // 2
                rightpad = width - w - leftpad
            self.fill(bg, x, y, leftpad, h)
            x += leftpad
            rx = x+w

        self.wg.draw_string(fg, s, x, y)

        if width:
            self.fill(bg, rx, y, rightpad, h)

    def bounding_box(self, s):
        """Return the bounding box of a string.

        :param s: A string
        :returns: Tuple of (width, height)
        """
        if s is None:
            s = "   "
        return self.wg.string_bounding_box(s)

    def wrap(self, s, width):
        """Chunk a string so it can rendered within a specified width.

        Example:

        .. code-block:: python

            draw = wasp.watch.drawable
            chunks = draw.wrap(long_string, 240)

            # line(1) will provide the first line
            # line(len(chunks)-1) will provide the last line
            def line(n):
                return long_string[chunks[n-1]:chunks[n]]

        :param s:     String to be chunked
        :param width: Width to wrap the text into
        :returns:     List of chunk boundaries
        """
        font = self.wg._font
        max = len(s)
        chunks = [ 0, ]
        end = 0

        while end < max:
            start = end
            l = 0

            for i in range(start, max+1):
                if i >= max:
                    end = i
                    break
                ch = s[i]
                font._set_ch(ch)
                h = font.height
                w = font.width
                l += w + 1
                if l > width:
                    if end <= start:
                        end = i
                    break

                # Break the line immediately if requested
                if ch == '\n':
                    end = i+1
                    break

                # Remember the right-most place we can cleanly break the line
                if ch == ' ':
                    end = i+1
            chunks.append(end)

        return chunks

    def line(self, x0, y0, x1, y1, width=1, color=None):
        """Draw a line between points (x0, y0) and (x1, y1).

        Example:

        .. code-block:: python

            draw = wasp.watch.drawable
            draw.line(0, 120, 240, 240, 0xf800)

        :param x0: X coordinate of the start of the line
        :param y0: Y coordinate of the start of the line
        :param x1: X coordinate of the end of the line
        :param y1: Y coordinate of the end of the line
        :param width: Width of the line in pixels
        :param color: Colour to draw line, defaults to the foreground colour
        """
        if color is None:
            color = self._fg
        self.wg.draw_line(color, width, x0, y0, x1, y1)


    def polar(self, x, y, theta, r0, r1, width=1, color=None):
        """Draw a line using polar coordinates.

        The coordinate system is tuned for clock applications so it
        adopts navigational conventions rather than mathematical ones.
        Specifically the reference direction is drawn vertically
        upwards and the angle is measures clockwise in degrees.

        Example:

        .. code-block:: python

            draw = wasp.watch.drawable
            draw.line(360 / 12, 16, 64)

        :param x: X coordinate of the origin
        :param y: Y coordinate of the origin
        :param theta: Angle, in degrees
        :param r0: Radius of the start of the line
        :param y0: Radius of the end of the line
        :param width: Width of the line in pixels
        :param color: Colour to draw line in, defaults to the foreground colour
        """

        if color is None:
            color = self._fg
        self.wg.draw_line_polar(color, width, x, y, theta, r0, r1)

    def lighten(self, color, step=1):
        """Get a lighter shade from the same palette.

        The approach is somewhat unsophisticated. It is essentially just a
        saturating add for each of the RGB fields.

        :param color: Shade to lighten
        :returns:     New colour
        """
        r = (color & R) + (step << 11)
        if r > R:
            r = R

        g = (color & G) + (step <<  6)
        if g > G:
            g = G

        b = (color & B) + step
        if b > B:
            b = B

        return (r | g | b)

    def darken(self, color, step=1):
        """Get a darker shade from the same palette.

        The approach is somewhat unsophisticated. It is essentially just a
        desaturating subtract for each of the RGB fields.

        :param color: Shade to darken
        :returns:     New colour
        """
        rm = color & R
        rs = step << 11
        r = rm - rs if rm > rs else 0

        gm = color & G
        gs = step << 6
        g = gm - gs if gm > gs else 0

        bm = color & B
        b = bm - step if bm > step else 0

        return (r | g | b)
