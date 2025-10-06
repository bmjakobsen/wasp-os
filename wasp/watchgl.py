#!/usr/bin/env python3
from array import array
import math
import fonts.sans24
import builtins
#from time import ticks_ms, ticks_add, ticks_diff



# TODO; Check drawing functions if they use correct yshift, and apply window coordinates correctly
# TODO: Implement Drawing and Switching of screens
# TODO: For smooth scrolling it would be required to get the components of a screen efficiently, that overlap with a stripe on the screen.
# 



import time
try:
    from micropython import const       # type: ignore[import-not-found]
    import micropython                  # type: ignore[import-not-found]
except ImportError:
    print("Using Micropython Faker Library")
    from _micropython_faker import const
    import _micropython_faker as micropython
    ptr8 = memoryview
    ptr16 = memoryview
    ptr32 = memoryview
    def _sleep_ms(ms):
        time.sleep(ms / 1000)
    time.sleep_ms = _sleep_ms                                   # type: ignore[attr-defined]
    time.ticks_ms = lambda : int(time.time() * 1000)            # type: ignore[attr-defined]
    time.ticks_us = lambda : int(time.time() * 1000 * 1000)     # type: ignore[attr-defined]
    time.ticks_add = lambda x, d : (x+d)                        # type: ignore[attr-defined]
    time.ticks_diff = lambda x, y : x-y                         # type: ignore[attr-defined]



try:
    import gc
    def _gc_collect():
        gc.collect()
except (ImportError, AttributeError):
    def _gc_collect():
        gc.collect()


TILE_SIZE = const(16)                       # Size of tiles on the screen, all components must be aligned to tiles

_MAX_TILES_WIDTH = const(16)
_MAX_TILES_HEIGHT = const(20)

# The Max size of the screen is dependent on the tile size, currently it is assumed that all screens have at most 16 Tiles in the width
_MAX_SCREEN_WIDTH = const(TILE_SIZE*_MAX_TILES_WIDTH)
_MAX_SCREEN_HEIGHT = const(TILE_SIZE*_MAX_TILES_HEIGHT)



try:
    from typing import Protocol
except ImportError:
    Protocol = object           # type: ignore[assignment]




_ARRAY_TEST_MIN_MAX_SIZE = {
    (8,  False):  (       -128,          127),
    (8,  True):   (          0,          255),
    (16, False):  (     -32768,        32767),
    (16, True):   (          0,        65535),
    (32, False):  (-2147483648,   2147483647),
    (32, True):   (          0,   4294967295)
}
_ARRAY_TEST_INTEGERS = {
    False:      [ 'b', 'h', 'i', 'l', 'q' ],
    True:       [ 'B', 'H', 'I', 'L', 'Q' ]
}

def _array_get_int_type(n:int, unsigned:bool=False) -> str:
    global _ARRAY_TEST_MIN_MAX_SIZE, _ARRAY_TEST_INTEGERS
    if n not in [8, 16, 32]:
        raise Exception("Invalid Choice")
    (min, max) = _ARRAY_TEST_MIN_MAX_SIZE[(n, unsigned)]
    minm = min-1
    maxm = max+1
    for ctype in _ARRAY_TEST_INTEGERS[unsigned]:
        a = array(ctype, [0])
        try:
            a[0] = min
            if a[0] != min:
                continue
            a[0] = max
            if a[0] != max:
                continue
        except OverflowError:
            continue

        try:
            a[0] = minm
            if a[0] == minm:
                continue
        except OverflowError:
            pass

        try:
            a[0] = maxm
            if a[0] == maxm:
                continue
        except OverflowError:
            pass
        return ctype
    raise Exception("Unable to get fitting ctype")






COLORFORMAT_RGB565 = const(128)
COLORFORMAT_RGB565_R = const(129)


DIRECTION_UP = const(0)
DIRECTION_DOWN = const(1)
DIRECTION_LEFT = const(2)
DIRECTION_RIGHT = const(3)

ALIGNMENT_CENTER = const(0)
ALIGNMENT_LEFT = const(1)
ALIGNMENT_RIGHT = const(2)



class ImageStream(Protocol):
    width: int
    height: int
    # Reset Stream, or restart it
    def reset(self):
        pass

    # Read n Pixels, into the buffer at the given offset, returns number of pixels read. Offset is in pixels
    # The streams signals that it is emptry by returning a number smaller than the number of requested pixels
    # The stream is never allowed to return less pixels than requested, while the stream has not reached its end

    # A Reader can expect that a stream does not have too many pixels, or that the number of remaining pixels changes unless by the amount specified in skip_pixels or when reading_pixels

    def read_pixels(self, read:bool, buf:memoryview, n:int, offset:int) -> int:
        return -1
    # Get Remaining number of pixels, should only be used in a few cases, like ensuring the stream has enough pixels before starting to read it, as it can be slow.
    def get_remaining(self) -> int:
        return -1
    def info(self) -> str:
        return ""

_DUMMY_BUFFER:memoryview = memoryview(bytearray(16))
def _skip_pixels(s, n:int):
    global _DUMMY_BUFFER
    s.read_pixels(False, _DUMMY_BUFFER, n, 0)



_VSCROLL_STRIPE_SIZE_REDUCTION = const(1)
class DisplaySpec():
    def __init__(self, width:int, height:int, color_format:int, scroll_directions:frozenset[int]=frozenset([]), vscroll_stripe_size:int=0):
        self.width:int = width
        self.height:int = height
        self.color_format:int = color_format
        self.max_dimension:int = width
        self.min_dimension:int = height

        if height > width:
            self.max_dimension = height
            self.min_dimension = width


        if width > _MAX_SCREEN_WIDTH:
            raise Exception("The screen is too wide to handle, currently not more than "+str(_MAX_SCREEN_WIDTH)+" is allowed")
        if height > _MAX_SCREEN_WIDTH:
            raise Exception("The screen is too wide to handle, currently not more than "+str(_MAX_SCREEN_HEIGHT)+" is allowed")


        self.tiled_width:int = width//TILE_SIZE
        self.tiled_height:int = height//TILE_SIZE

        self.x_offset:int = (width-(self.tiled_width*TILE_SIZE))//2
        self.y_chin:int = height-(self.tiled_height*TILE_SIZE)

        if self.x_offset < 0 or self.y_chin < 0:
            raise Exception("Shouldnt Happen")

        if vscroll_stripe_size >= _VSCROLL_STRIPE_SIZE_REDUCTION:
            vscroll_stripe_size -= _VSCROLL_STRIPE_SIZE_REDUCTION
        if vscroll_stripe_size < 0:
            raise Exception("vscroll_stripe_size must not be negative")
        if vscroll_stripe_size < (2*TILE_SIZE+self.y_chin):
            if DIRECTION_UP in scroll_directions or DIRECTION_DOWN in scroll_directions:
                raise Exception("Vertical Scrolling area is too small to implement scrolling, must specify allowed scrolling directions to not include UP or DOWN")

        scroll_directions = frozenset(scroll_directions)
        for scd in scroll_directions:
            if scd == DIRECTION_UP:
                continue
            if scd == DIRECTION_DOWN:
                continue
            raise Exception("Unsupported Scroll Direction used")

        self.vscroll_stripe_size = vscroll_stripe_size
        self.scroll_directions:frozenset[int] = scroll_directions




class DisplayProtocol(Protocol):
    spec: DisplaySpec

    def wgl_vscroll(self, pixels:int):
        pass

    def wgl_fill(self, color:int, x:int, y:int, width:int, height:int):
        pass
    # The Function
    def wgl_blit(self, image:ImageStream, x:int, y:int):
        pass






ARROFF = const(0x10000)

_SX_WIDTH = const(0)
_SX_HEIGHT = const(1)
_SX_REMAINING = const(2)

# Image Stream used to wrap another image stream and crop it vertically, by specifiying the new reduced height, and the number of lines skipped at the start
class VerticalCropStream():
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)
    def __init__(self, instream:ImageStream, skip:int, height:int):
        self._extra_state:memoryview = memoryview(array(self._32BIT_SIGNED_INT, bytearray(3*4)))
        self._setup(instream, skip, height)
    def _setup(self, instream:ImageStream, skip:int, height:int):
        self.width:int = instream.width
        if skip < 0:
            raise Exception("Number of skipped lines must not be negative")
        if skip+height > instream.height:
            raise Exception("Cropped height greater than source height")
        self.height:int = height
        self._instream:ImageStream = instream

        self._skip_lines:int = skip

        self._pixels_n:int = self.height*self.width
        self._skip:int = skip*self.width

        _skip_pixels(self._instream, self._skip)
        self._extra_state[_SX_REMAINING] = self._pixels_n
        assert(self._instream.get_remaining() >= self._pixels_n)
    def reset(self):
        self._instream.reset()
        _skip_pixels(self._instream, self._skip)
        self._extra_state[_SX_REMAINING] = self._pixels_n
        assert(self._instream.get_remaining() >= self._pixels_n)
    def get_remaining(self) -> int:
        return self._extra_state[_SX_REMAINING]
    def read_pixels(self, read:bool, buf, n:int, offset:int) -> int:
        #state:ptr32 = ptr32(self._extra_state)
        state:memoryview = self._extra_state
        remaining:int = state[_SX_REMAINING]
        if n > remaining:
            n = remaining
        if n <= 0:
            return 0
        read_pixels = self._instream.read_pixels
        r:int = int(read_pixels(read, buf, n, offset))
        remaining -= r
        state[_SX_REMAINING] = remaining
        return r
    def info(self) -> str:
        return "VERTICAL_CROP_STREAM("+str(self._skip_lines)+", "+str(self.height)+", "+self._instream.info()+")"


_HCS_SKIP = const(3)
_HCS_REM_IN_L = const(4)


# Image Stream used to wrap another image stream and crop it horizontally, by specifiying the new reduced width, and the number of columns skipped at the start
class HorizontalCropStream():
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)
    def __init__(self, instream:ImageStream, skip:int, width:int):
        self._extra_state:memoryview = memoryview(array(self._32BIT_SIGNED_INT, bytearray(5*4)))
        self._setup(instream, skip, width)
    def _setup(self, instream:ImageStream, skip:int, width:int):
        self.height:int = instream.height
        if skip < 0:
            raise Exception("Number of skipped columns must not be negative")
        if skip+width > instream.width:
            raise Exception("Cropped width greater than source width")
        self.width:int = width
        self._instream:ImageStream = instream
        self._pixels_n:int = self.height*self.width


        # Amount that is skipped at the start of a line
        self._skip_at_start:int = skip

        # Amoung that is skipped between two lines
        self._skip:int = instream.width-width

        # Amount of pixels that are required in the inner stream
        self._instream_required:int = self._pixels_n+self.height*self._skip

        # State for easy access by viper code
        self._extra_state[_SX_WIDTH] = self.width
        self._extra_state[_SX_HEIGHT] = self.height
        self._extra_state[_HCS_SKIP] = self._skip


        self._extra_state[_SX_REMAINING] = self._pixels_n
        self._extra_state[_HCS_REM_IN_L] = self.width
        assert(self._instream.get_remaining() >= self._instream_required)
        _skip_pixels(self._instream, self._skip_at_start)
    def get_remaining(self) -> int:
        return self._extra_state[_SX_REMAINING]

    def reset(self):
        self._instream.reset()
        self._extra_state[_SX_REMAINING] = self._pixels_n
        self._extra_state[_HCS_REM_IN_L] = self.width
        assert(self._instream.get_remaining() >= self._instream_required)
        _skip_pixels(self._instream, self._skip_at_start)

    @micropython.viper
    def read_pixels(self, read:bool, buf, n:int, offset:int) -> int:
        state:ptr32 = ptr32(self._extra_state)

        remaining:int = state[_SX_REMAINING]
        if n > remaining:
            n = remaining
        if n <= 0:
            return 0

        instream = self._instream
        skip_pixels = _skip_pixels
        read_pixels = self._instream.read_pixels

        WIDTH:int = state[_SX_WIDTH]
        SKIP:int = state[_HCS_SKIP]
        rem_in_l:int = state[_HCS_REM_IN_L]

        read_bytes:int = 0
        while n > 0:
            if n >= rem_in_l:
                r = int(read_pixels(read, buf, rem_in_l, offset+read_bytes))
                read_bytes += r
                n -= rem_in_l
                skip_pixels(instream, SKIP)
                remaining -= rem_in_l
                rem_in_l = WIDTH
            else:
                r = int(read_pixels(read, buf, n, offset+read_bytes))
                read_bytes += r
                rem_in_l -= n
                remaining -= n
                n = 0
        state[_SX_REMAINING] = remaining
        state[_HCS_REM_IN_L] = rem_in_l
        return read_bytes
    def info(self) -> str:
        return "HORIZONTAL_CROP_STREAM("+str(self._skip_at_start)+", "+str(self.width)+", "+self._instream.info()+")"


_DEFAULT_TEXT_FGCOLOR:int = const(0xFFFF)
_PALETTE2_INITALIZER = [0, 0xFFFF]
_PALETTE4_INITALIZER = [0, 0x4a69, 0x7bef, 0xFFFF]



#Temporarily Non-Native
#@micropython.viper
def _convert_color_to_format(format:int, color:int) -> int:
    color &= 0xFFFF
    if format == COLORFORMAT_RGB565:
        return color
    elif format == COLORFORMAT_RGB565_R:
        color2:int = (color>>8)&0xFF
        color = (color<<8)&0xFF00
        return color | color2
    else:
        raise Exception("Unknown Color format specified")


_MIS_CBYTE = const(3)
_MIS_INDEX = const(4)
_MIS_REM_IN_L = const(5)
_MIS_BITSEL = const(6)
_MIS_WEXTEND = const(1)
# Streamer for reading a memoryview (1 byte per element) as an uncompressed image, with one bit per pixel
class WaspFontStream():
    _16BIT_UNSIGNED_INT = _array_get_int_type(16, unsigned=True)
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)
    def __init__(self, screen_color_format:int, font):
        self._color_format:int = screen_color_format
        self._palette:memoryview = memoryview(array(self._16BIT_UNSIGNED_INT, _PALETTE2_INITALIZER+_PALETTE2_INITALIZER))
        self._extra_state:memoryview = memoryview(array(self._32BIT_SIGNED_INT, bytearray(7*4)))
        for i in range(4):
            self._palette[i] = _convert_color_to_format(screen_color_format, self._palette[i])
        self._current_char = 'T'
        self._set_font(font)
    def _set_font(self, font):
        self._font_height:int = font.height()
        self._font_max_width:int = font.max_width()
        self._font = font
        self._set_ch(self._current_char)
    def _set_ch(self, ch:str):
        raw_data, height, width = self._font.get_ch(ch)
        self._current_char = ch
        if width <= 0 or height <= 0:
            raise Exception("Image must have a positive size greater than 0")

        width += _MIS_WEXTEND
        self._raw_data:memoryview = raw_data
        self.width:int = width
        self.height:int = height
        self._n_pixels:int = width*height


        # Width
        self._extra_state[_SX_WIDTH] = self.width
        # Height
        self._extra_state[_SX_HEIGHT] = self.height

        self.reset()

    def get_remaining(self) -> int:
        return self._extra_state[_SX_REMAINING]

    @micropython.viper
    def _set_color(self, color:int, bgcolor:int):
        cf:int = int(self._color_format)
        fconv = _convert_color_to_format
        self._palette[0] = fconv(cf, bgcolor)
        self._palette[1] = fconv(cf, color)

    def reset(self):
        # Set State required for reading the image

        #Remaining
        self._extra_state[_SX_REMAINING] = self._n_pixels
        #cbyte
        self._extra_state[_MIS_CBYTE] = self._raw_data[0]
        #index
        self._extra_state[_MIS_INDEX] = 0
        # Remaining in line
        self._extra_state[_MIS_REM_IN_L] = self.width
        # Remaining in byte
        self._extra_state[_MIS_BITSEL] = 0x80

    @micropython.viper
    def read_pixels(self, read:bool, buf, n:int, offset:int) -> int:
        state:ptr32 = ptr32(self._extra_state)

        buf2:ptr8 = ptr8(buf)
        remaining:int = state[_SX_REMAINING]
        if n >= remaining:
            n = remaining
        if n <= 0:
            return 0
        # Offset is in pixels, but offset is required in bytes, so multiply by two
        offset = (offset<<1)


        palette:ptr16 = ptr16(self._palette)
        raw_data:ptr8 = ptr8(self._raw_data)

        WIDTH:int = state[_SX_WIDTH]
        cbyte:int = state[_MIS_CBYTE]
        index:int = state[_MIS_INDEX]
        bitselect:int = state[_MIS_BITSEL]
        rem_in_l:int = state[_MIS_REM_IN_L]

        n2:int = n
        while n2 > 0:
            n2 -= 1

            color:int = palette[1] if cbyte&bitselect else palette[0]
            if read:
                buf2[offset] = (color>>8)&0xFF
                buf2[offset+1] = color&0xFF
            offset += 2


            bitselect >>= 1
            rem_in_l -= 1
            remaining -= 1
            if remaining <= 0:
                break
            if rem_in_l <= _MIS_WEXTEND and rem_in_l > 0:
                bitselect = 0
                continue
            if rem_in_l <= 0:
                rem_in_l = WIDTH
                bitselect = 0
            if bitselect == 0:
                bitselect = 0x80
                index += 1
                cbyte = raw_data[index]
        state[_SX_REMAINING] = remaining
        state[_MIS_CBYTE] = cbyte
        state[_MIS_INDEX] = index
        state[_MIS_BITSEL] = bitselect
        state[_MIS_REM_IN_L] = rem_in_l
        return n
    def info(self) -> str:
        return "WaspFontStream("+str(self._current_char)+", "+str(self.width)+", "+str(self.height)+")"



_MRIS_COLOR = const(3)
_MRIS_RLEN = const(4)
_MRIS_INDEX = const(5)
class WaspRle1ImageStream():
    _16BIT_UNSIGNED_INT = _array_get_int_type(16, unsigned=True)
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)
    def __init__(self, screen_color_format:int, raw_data:memoryview, width:int, height:int):
        self._color_format:int = screen_color_format
        self._palette:memoryview = memoryview(array(self._16BIT_UNSIGNED_INT, _PALETTE2_INITALIZER))
        self._extra_state:memoryview = memoryview(array(self._32BIT_SIGNED_INT, bytearray(6*4)))
        for i in range(2):
            self._palette[i] = _convert_color_to_format(screen_color_format, self._palette[i])
        self._setup(raw_data, width, height)
    def _setup(self, raw_data:memoryview, width:int, height:int):
        if width <= 0 or height <= 0:
            raise Exception("Image must have a positive size greater than 0")

        self._raw_data:memoryview = raw_data
        self.width:int = width
        self.height:int = height
        self._n_pixels:int = width*height

        # Width
        self._extra_state[_SX_WIDTH] = self.width
        # Height
        self._extra_state[_SX_HEIGHT] = self.height
        self.reset()

    def get_remaining(self) -> int:
        return self._extra_state[_SX_REMAINING]

    def _set_color(self, n:int, color:int):
        if n < 0 or n > 1:
            raise Exception("Invalid Palette Index")
        self._palette[n] = _convert_color_to_format(self._color_format, color)

    def reset(self):
        # Set State required for reading the image

        raw_data:memoryview = self._raw_data

        #Remaining
        self._extra_state[_SX_REMAINING] = self._n_pixels
        #color
        self._extra_state[_MRIS_COLOR] = 0
        #index
        self._extra_state[_MRIS_RLEN] = raw_data[0]
        #index
        self._extra_state[_MRIS_INDEX] = 0

    @micropython.viper
    def read_pixels(self, read:bool, buf, n:int, offset:int) -> int:
        state:ptr32 = ptr32(self._extra_state)

        buf2:ptr8 = ptr8(buf)
        remaining:int = state[_SX_REMAINING]
        if n >= remaining:
            n = remaining
        if n <= 0:
            return 0
        # Offset is in pixels, but offset is required in bytes, so multiply by two
        offset = (offset<<1)


        palette:ptr16 = ptr16(self._palette)
        raw_data:ptr8 = ptr8(self._raw_data)

        color:int = state[_MRIS_COLOR]
        rlen:int = state[_MRIS_RLEN]
        index:int = state[_MRIS_INDEX]


        while rlen <= 0:
            index += 1
            rlen = raw_data[index]
            color = (color+1)&1
        color_0:int = palette[color]&0xFF
        color_1:int = (palette[color]>>8)&0xFF

        n2:int = n
        while n2 > 0:
            n2 -= 1

            rlen -= 1
            remaining -= 1
            if read:
                buf2[offset] = color_1
                buf2[offset+1] = color_0
            offset += 2


            if remaining == 0:
                break
            while rlen <= 0:
                index += 1
                rlen = raw_data[index]
                color = (color+1)&1
                color_0 = palette[color]&0xFF
                color_1 = (palette[color]>>8)&0xFF

        state[_SX_REMAINING] = remaining
        state[_MRIS_COLOR] = color
        state[_MRIS_RLEN] = rlen
        state[_MRIS_INDEX] = index
        return n
    def info(self) -> str:
        return "WaspRle1ImageStream("+str(self.width)+", "+str(self.height)+")"









@micropython.viper
def _clut8_rgb565(color_format:int, i: int) -> int:
    if i < 216:
        rgb565  = (( i  % 6) * 0x33) >> 3
        rg = i // 6
        rgb565 += ((rg  % 6) * (0x33 << 3)) & 0x07e0
        rgb565 += ((rg // 6) * (0x33 << 8)) & 0xf800
    elif i < 252:
        i -= 216
        rgb565  = (0x7f + (( i  % 3) * 0x33)) >> 3
        rg = i // 3
        rgb565 += ((0x4c << 3) + ((rg  % 4) * (0x33 << 3))) & 0x07e0
        rgb565 += ((0x7f << 8) + ((rg // 4) * (0x33 << 8))) & 0xf800
    else:
        i -= 252
        gr6 = (0x2c + (0x10 * i)) >> 2
        gr5 = gr6 >> 1
        rgb565 = (gr5 << 11) + (gr6 << 5) + gr5

    return int(_convert_color_to_format(color_format, rgb565))


_R2IS_COLOR = const(3)
_R2IS_NXCOLOR = const(4)
_R2IS_RLEN = const(5)
_R2IS_INDEX = const(6)
_R2IS_MAXINDEX = const(7)
class WaspRle2ImageStream():
    _16BIT_UNSIGNED_INT = _array_get_int_type(16, unsigned=True)
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)
    def __init__(self, screen_color_format:int, raw_data:memoryview, width:int, height:int):
        self._color_format:int = screen_color_format
        self._palette:memoryview = memoryview(array(self._16BIT_UNSIGNED_INT, _PALETTE4_INITALIZER+_PALETTE4_INITALIZER))
        self._extra_state:memoryview = memoryview(array(self._32BIT_SIGNED_INT, bytearray(8*4)))
        self._dummy_buf:memoryview = memoryview(bytearray(1))
        for i in range(8):
            self._palette[i] = _convert_color_to_format(screen_color_format, self._palette[i])
        self._setup(raw_data, width, height)
    def _setup(self, raw_data:memoryview, width:int, height:int):
        if width <= 0 or height <= 0:
            raise Exception("Image must have a positive size greater than 0")

        self._raw_data:memoryview = raw_data
        self.width:int = width
        self.height:int = height
        self._n_pixels:int = width*height

        # Width
        self._extra_state[_SX_WIDTH] = self.width
        # Height
        self._extra_state[_SX_HEIGHT] = self.height
        #index
        self._extra_state[_R2IS_MAXINDEX] = len(raw_data)-1
        self.reset()

    def get_remaining(self) -> int:
        return self._extra_state[_SX_REMAINING]

    def _set_color(self, n:int, color:int):
        if n < 0 or n > 3:
            raise Exception("Invalid Palette Index")
        c = _convert_color_to_format(self._color_format, color)
        self._palette[n] = c
        self._palette[n+4] = c

    def reset(self):
        # Set State required for reading the image

        palette:memoryview = self._palette
        palette[0] = palette[0+4]
        palette[1] = palette[1+4]
        palette[2] = palette[2+4]
        palette[3] = palette[3+4]
        raw_data:memoryview = self._raw_data

        #Remaining
        self._extra_state[_SX_REMAINING] = self._n_pixels
        #color
        self._extra_state[_R2IS_COLOR] = 4
        self._extra_state[_R2IS_NXCOLOR] = 1
        #index
        self._extra_state[_R2IS_RLEN] = 0
        #index
        self._extra_state[_R2IS_INDEX] = -1+ARROFF

    @micropython.viper
    def read_pixels(self, read:bool, buf, n:int, offset:int) -> int:
        state:ptr32 = ptr32(self._extra_state)

        buf2:ptr8 = ptr8(buf)
        remaining:int = state[_SX_REMAINING]
        if n >= remaining:
            n = remaining
        if n <= 0:
            return 0
        # Offset is in pixels, but offset is required in bytes, so multiply by two
        offset = (offset<<1)


        palette:ptr16 = ptr16(self._palette)
        raw_data:ptr8 = ptr8(self._raw_data)

        color:int = state[_R2IS_COLOR]
        nxcolor:int = state[_R2IS_NXCOLOR]
        rlen:int = state[_R2IS_RLEN]
        index:int = state[_R2IS_INDEX]-ARROFF
        fbyte:int = 0
        max_index = state[_R2IS_MAXINDEX]

        clut8_rgb565 = _clut8_rgb565


        n2:int = n
        while n2 > 0:
            if color < 4 and rlen > 0:
                color_0 = palette[color]&0xFF
                color_1 = (palette[color]>>8)&0xFF
                while rlen > 0 and n2 > 0:
                    if read:
                        buf2[offset] = color_1
                        buf2[offset+1] = color_0
                    offset += 2
                    rlen -= 1
                    n2 -= 1
                    remaining -= 1
            if n2 == 0:
                break
            if rlen == 0:
                index += 1
                fbyte = raw_data[index]
                color = (fbyte>>6)&3
                rlen = fbyte&0x3F
                if rlen == 0:
                    index += 1
                    fbyte = raw_data[index]
                    palette[nxcolor] = int(clut8_rgb565(self._color_format, fbyte))&0xFFFF
                    nxcolor += 1
                    if nxcolor > 3:
                        nxcolor = 1
                    rlen = 0
                elif rlen == 63:
                    while index < max_index:
                        index += 1
                        fbyte = raw_data[index]
                        rlen += fbyte
                        if fbyte < 255:
                            break
        state[_SX_REMAINING] = remaining
        state[_R2IS_COLOR] = color
        state[_R2IS_NXCOLOR] = nxcolor
        state[_R2IS_RLEN] = rlen
        state[_R2IS_INDEX] = index+ARROFF
        return n
    def info(self) -> str:
        return "WaspRle2ImageStream("+str(self.width)+", "+str(self.height)+")"






# The Draw Function of a component takes the reference to the component, the state dict, and a reference to the WatchGraphics Object
def _draw_function_sample(com:'Component', state:dict[str, object], wgl:'WatchGraphics'):
    return None

class Component():
    def __init__(self, x:int, y:int, width:int, height:int, draw_function, state:dict[str, object]={}, font=None):
        if (x < 0 or x%TILE_SIZE != 0 or
          y < 0 or y%TILE_SIZE != 0 or
          width <= 0 or width%TILE_SIZE != 0 or
          height <= 0 or height%TILE_SIZE != 0):
            raise Exception("Invalid Sizing or Positioning of Component, Components Size and Position must be aligned to "+str(TILE_SIZE)+", Position must not be negative and Size must be greater than 0")

        self.x:int = x
        self.y:int = y
        self.width:int = width
        self.height:int = height
        self.dirty = False
        self._font = font


        self.draw = draw_function
        self._state:dict[str, object] = {}
        # Only assign value of state to _state if it is not the default value, else assign to empty dict
        # This is because, if the default value where assigned, the updates to the dict would also happen
        # In other components
        if len(state) > 0:
            self._state = state
        self._screen:"Screen" = None        # type: ignore[assignment]
        self._cid:int = 0
    # Returns None, if undefined
    def get_var(self, k:str) -> object:
        state = self._state
        if k not in state:
            return None
        return self._state[k]
    def set_var(self, k:str, v:object):
        state = self._state
        # Only Notify Screen of Update, if the component is not dirty, and the component is part of a screen
        # And if the component changes, either key is not in state, or value is different
        # This also sets the dirty flag
        screen = self._screen
        if not self.dirty and screen is not None and (k not in state or state[k] != v):
            screen.notify_component_update(self._cid)
            self.dirty = True
        state[k] = v


_SC_WIDTH = const(0)            # Width of Screen
_SC_HEIGHT = const(1)           # Height of Screen
_SC_THEIGHT = const(2)          # Height of screen in Components
# Horizontal and Vertical Offset to usable screen inside of real screen
_SC_XOFFSET = const(3)
_SC_YCHIN = const(4)
_SC_MAX_AHEAD = const(5)

# This means that the component Grid is centered horizontally, but not vertically.



_SC_YMAP_NULL_ENTRY = const(_MAX_TILES_HEIGHT*2)

class Screen():
    _8BIT_UNSIGNED_INT = _array_get_int_type(8, unsigned=True)
    _16BIT_UNSIGNED_INT = _array_get_int_type(16, unsigned=True)
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)

    _YMAP_INITIALIZER = [0, _SC_YMAP_NULL_ENTRY]*(_MAX_TILES_HEIGHT)+[0]


    _CREATION_OVERLAP_BITMASK:memoryview = memoryview(array(_16BIT_UNSIGNED_INT, bytearray(_MAX_TILES_HEIGHT*2)))
    def __init__(self, bgcolor:int, wgl:'WatchGraphics', components:list['Component'], font=fonts.sans24):
        if len(components) > 127:
            raise Exception("Too many components")
        self.bgcolor:int = bgcolor&0xFF

        if font is None:
            font = fonts.sans24
        self._font = font

        self._wgl = wgl
        display_spec = wgl.display.spec

        self.display_spec:DisplaySpec = display_spec
        self.display_width:int = display_spec.width
        self.display_height:int = display_spec.height

        self._full_draw:bool = True

        tiled_height:int = display_spec.tiled_height
        tiled_width:int = display_spec.tiled_width
        self.tiled_height:int = tiled_height

        x_offset:int = display_spec.x_offset
        y_chin:int = display_spec.y_chin


        self._screen_info:memoryview = memoryview(array(self._32BIT_SIGNED_INT, bytearray(6*4)))
        self._screen_info[_SC_WIDTH] = self.display_width
        self._screen_info[_SC_HEIGHT] = self.display_height
        self._screen_info[_SC_THEIGHT] = tiled_height
        self._screen_info[_SC_XOFFSET] = x_offset
        self._screen_info[_SC_YCHIN] = y_chin
        self._screen_info[_SC_MAX_AHEAD] = display_spec.vscroll_stripe_size


        # The bitfield is used to detect overlaps in components
        # Each array index is a row and each bit says wether that column is occupied by a component
        com_map_y:list[list[int]] = []
        bitfield:memoryview = self._CREATION_OVERLAP_BITMASK
        for i in range(tiled_height):
            bitfield[i] = 0
            com_map_y.append([])


        ncomponents:list['Component'] = []
        cid:int = 1
        for c in components:
            # Get y range occupied by tile
            cy0:int = (c.y)//TILE_SIZE
            cy1:int = cy0+(c.height//TILE_SIZE)

            # Get x range occupied by tile
            cx0:int = (c.x)//TILE_SIZE
            cx1:int = cx0+(c.width//TILE_SIZE)

            if cy1 > tiled_height or cx1 > tiled_width:
                raise Exception("Component goes out of screen bounds")

            # Check and set flags in bitfield wether a given position is already occupied by another component
            for cyp in range(cy0, cy1):
                com_map_y[cyp].append(cid)
                value = bitfield[cyp]
                for i in range(cx0, cx1):
                    if (value>>i)&1:
                        raise Exception("Overlapping components detected")
                    bitfield[cyp] |= 1<<i

            # Register this screen to the component so that it nows its id and has a reference to the screen
            if not c._screen is None:
                raise Exception("Component given to screen is already part of a screen")
            c._screen = self
            c._cid = cid

            if c._font is None:
                c._font = font
            c.dirty = False
            ncomponents.append(c)
            cid = cid+1






        last_used_offset:int = -1
        last_used_list:list[int] = []
        next_offset:int = _SC_YMAP_NULL_ENTRY+1
        com_map_a:array = array(self._8BIT_UNSIGNED_INT, self._YMAP_INITIALIZER)
        ri:int = 0
        for r in com_map_y:
            r.append(0)
            offset:int = -1
            if len(r) <= 1:
                offset = _SC_YMAP_NULL_ENTRY
            elif r == last_used_list:
                offset = last_used_offset
            else:
                offset = next_offset
                next_offset += int(len(r))
                com_map_a.extend(r)
                last_used_list = r
                last_used_offset = offset
            offset &= 0xFFFF
            com_map_a[ri] = offset>>8
            com_map_a[ri+1] = offset&0xFF
            ri += 2

        # This is a viper friendly representation of the map that says which components are at which height
        # First is a section of _MAX_TILES_HEIGHT byte pairs where the first byte are the upper 8 Bits and the second byte are the lower 8 bits of a 16 Bit Integer
        # This 16 Bit integer yields and offset into the array, which is a list of cluster ids, terminated by a null byte.
        self.com_map_y:memoryview = memoryview(com_map_a)


        self.components:list['Component'] = ncomponents
        self.update_array = memoryview(array(self._16BIT_UNSIGNED_INT, bytearray(9*2)))
    @micropython.viper
    def notify_component_update(self, cid:int):
        update_array:ptr16 = ptr16(self.update_array)

        byti:int = 1+(cid>>4)
        biti:int = cid&0xf

        update_array[0] |= 1<<byti
        update_array[byti] |= 1<<biti


    @micropython.viper
    def draw(self):
        if self._full_draw:
            self._draw_full()
            return

        wgl = self._wgl
        update_array:ptr16 = ptr16(self.update_array)
        set_com_context = wgl._set_component_context
        builtin_false = builtins.bool(False)

        sc_info:ptr32 = ptr32(self._screen_info)
        X_OFFSET:int = sc_info[_SC_XOFFSET]


        # Use Pointers to set value
        update_bitfield:int = update_array[0]
        if update_bitfield == 0:
            return
        update_bitfield >>= 1
        id_block_off:int = -16
        byti:int = 0
        while byti < (8+1):
            id_block_off += 16
            id_block_used:int = update_bitfield&1
            byti += 1
            update_bitfield >>= 1

            if not id_block_used:
                if update_bitfield == 0:
                    break
                continue

            value:int = update_array[byti]&0xFFFF
            update_array[byti] = 0

            id_sub:int = 0
            while id_sub < 16:
                id_sub += 1

                id_used = value&1
                value >>= 1
                if not id_used:
                    if value == 0:
                        break
                    continue
                cid = id_block_off+id_sub
                com = self.components[cid]
                set_com_context(com._font, X_OFFSET+int(com.x), int(com.y), com.width, com.height, 0)
                com_draw = com.draw
                com_draw(com, com._state, wgl)
                com.dirty = builtin_false
        update_array[0] = 0


    def _draw_full(self):
        builtin_false = builtins.bool(False)
        self._full_draw = builtin_false
        wgl = self._wgl
        #update_array:ptr16 = ptr16(self.update_array)
        update_array:memoryview = self.update_array
        set_com_context = wgl._set_component_context

        #sc_info:ptr32 = ptr32(self._screen_info)
        sc_info:memoryview = self._screen_info
        X_OFFSET:int = sc_info[_SC_XOFFSET]

        for n in range(0, 9):
            update_array[n] = 0
        for com in self.components:
            set_com_context(com._font, X_OFFSET+int(com.x), int(com.y), com.width, com.height, 0)
            com_draw = com.draw
            com_draw(com, com._state, wgl)
            com.dirty = builtin_false

    def _draw_scroll(self, scroll_direction:int):
        builtin_false = builtins.bool(False)
        wgl = self._wgl
        fill = wgl._fill_uw
        sleep_ms = time.sleep_ms            # type: ignore[attr-defined]
        ticks_ms = time.ticks_ms            # type: ignore[attr-defined]
        ticks_add = time.ticks_add          # type: ignore[attr-defined]
        ticks_diff = time.ticks_diff        # type: ignore[attr-defined]


        if scroll_direction != DIRECTION_UP and scroll_direction != DIRECTION_DOWN:
            raise Exception("Invalid Direction given")


        vscroll = wgl.display.wgl_vscroll
        #sc_info:ptr32 = ptr32(self._screen_info)
        sc_info:memoryview = self._screen_info
        WIDTH:int = sc_info[_SC_WIDTH]
        HEIGHT:int = sc_info[_SC_HEIGHT]
        TILED_HEIGHT:int = sc_info[_SC_THEIGHT]
        X_OFFSET:int = sc_info[_SC_XOFFSET]
        Y_CHIN:int = sc_info[_SC_YCHIN]
        MAX_AHEAD:int = sc_info[_SC_MAX_AHEAD]
        bgcolor:int = self.bgcolor

        #update_array:ptr16 = ptr16(self.update_array)
        update_array:memoryview = self.update_array
        set_com_context = wgl._set_component_context
        
        for n in range(0, 9):
            update_array[n] = 0


        #ymap:ptr8 = ptr8(self.com_map_y)
        ymap:memoryview = self.com_map_y
        ahead:int = 0                   # Number of lines drawing is ahead of scrolling
        TICKS_BETWEEN_SCROLL = 3
        scroll_next_pixel = ticks_add(ticks_ms(), TICKS_BETWEEN_SCROLL)
        scroll_remaining:int = HEIGHT

        if scroll_direction == DIRECTION_UP:
            current_draw_line:int = HEIGHT
            FIRST_ROW:int = 0
            LAST_ROW:int = TILED_HEIGHT-1
            ypos:int = -16
            YPOS_CHANGE:int = TILE_SIZE
            SCROLL_D:int = -1
            CDL_OFFSET:int = 0
            SCROLL_RANGE = range(0, TILED_HEIGHT)
        elif scroll_direction == DIRECTION_DOWN:
            current_draw_line:int = 0
            FIRST_ROW:int = TILED_HEIGHT-1
            LAST_ROW:int = 0
            ypos:int = (TILED_HEIGHT*16)
            YPOS_CHANGE:int = 0-TILE_SIZE
            SCROLL_D:int = 1
            CDL_OFFSET:int = 0-TILE_SIZE
            SCROLL_RANGE = range(TILED_HEIGHT-1, -1, -1)
            if Y_CHIN > 0:
                fill(bgcolor, 0, current_draw_line-Y_CHIN, WIDTH, Y_CHIN)
                current_draw_line -= Y_CHIN
                ahead += Y_CHIN

        for trow in SCROLL_RANGE:
            ypos += YPOS_CHANGE

            # Scroll if there isnt enough buffer space ahead
            while ahead+TILE_SIZE > MAX_AHEAD:
                if int(ticks_diff(scroll_next_pixel, ticks_ms())) > 0:
                    sleep_ms(1)
                    continue
                scroll_next_pixel = ticks_add(scroll_next_pixel, TICKS_BETWEEN_SCROLL)
                current_draw_line += SCROLL_D
                scroll_remaining -= 1
                ahead -= 1
                vscroll(0-SCROLL_D)

            fill(bgcolor, 0, current_draw_line+CDL_OFFSET, WIDTH, TILE_SIZE)

            trow_x_2:int = trow<<1
            row_offset = (ymap[trow_x_2]<<8)+ymap[trow_x_2+1]
            while ymap[row_offset] != 0:
                com_id:int = ymap[row_offset]
                row_offset += 1
                com = self.components[com_id-1]
                com_draw = com.draw
                yshift:int = int(com.y)-ypos
                set_com_context(com._font, X_OFFSET+int(com.x), current_draw_line+CDL_OFFSET, com.width, TILE_SIZE, yshift)
                com_draw(com, com._state, wgl)
                com.dirty = builtin_false
                while ahead > 0 and int(ticks_diff(scroll_next_pixel, ticks_ms())) < 0:
                    scroll_next_pixel = ticks_add(scroll_next_pixel, TICKS_BETWEEN_SCROLL)
                    current_draw_line += SCROLL_D
                    scroll_remaining -= 1
                    ahead -= 1
                    vscroll(0-SCROLL_D)
            current_draw_line += YPOS_CHANGE
            ahead += TILE_SIZE
        if scroll_direction == DIRECTION_UP and Y_CHIN > 0:
            while ahead+Y_CHIN+1 > MAX_AHEAD:
                if int(ticks_diff(scroll_next_pixel, ticks_ms())) > 0:
                    sleep_ms(1)
                    continue
                scroll_next_pixel = ticks_add(scroll_next_pixel, TICKS_BETWEEN_SCROLL)
                current_draw_line += SCROLL_D
                scroll_remaining -= 1
                ahead -= 1
                vscroll(0-SCROLL_D)
            fill(bgcolor, 0, current_draw_line, WIDTH, Y_CHIN)
            ahead += Y_CHIN
        while scroll_remaining > 0:
            if int(ticks_diff(scroll_next_pixel, ticks_ms())) < 0:
                scroll_next_pixel = ticks_add(scroll_next_pixel, TICKS_BETWEEN_SCROLL)
                scroll_remaining -= 1
                vscroll(0-SCROLL_D)
            else:
                sleep_ms(1)

    @micropython.viper
    def _clear_screen(self, bgcolor:int):
        cbgcolor:int = int(self.bgcolor)
        wgl = self._wgl
        fill = wgl._fill_uw
        # Special Case, new background color differs, so redraw entire screen
        if bgcolor != cbgcolor:
            fill(bgcolor, 0, 0, self.display_width, self.display_height)
            return
        # Just overdraw individual components
        for com in self.components:
            fill(bgcolor, com.x, com.x, com.width, com.height)

    def switch_screen(self, ns:'Screen', direction:int):
        self._wgl._set_screen(self, ns)



def FillComponent(x:int, y:int, width:int, height:int, color:int):
    def _draw_function(com, state, wgl):
        wgl.fill(color, 0, 0, width, height)
        wgl.draw_line(color^0xAAAA, 3, 0, 0, width-1, height-1)
    return Component(x, y, width, height, _draw_function)

def TextComponent(x:int, y:int, width:int, height:int, s:str, color:int, bgcolor:int):
    def _draw_function(com, state, wgl):
        wgl.draw_string(color, bgcolor, s, 0, 0)
    return Component(x, y, width, height, _draw_function)




_WGWI_WIDTH = const(0)
_WGWI_HEIGHT = const(1)
_WGWI_XPOS = const(2)
_WGWI_YPOS = const(3)
_WGWI_YSHIFT = const(4)

_DEFAULT_BGCOLOR = const(0)

_C_TO_RADIANS:float = (math.pi / 180)
class WatchGraphics():
    _BIT_UNSIGNED_INT = _array_get_int_type(8, unsigned=True)
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)

    def __init__(self, display:DisplayProtocol, gc_collect:bool=True):
        self.display:DisplayProtocol = display

        self._font:WaspFontStream = WaspFontStream(display.spec.color_format, fonts.sans24)

        self.bgcolor:int = _DEFAULT_BGCOLOR

        self._screen = None

        #self.scroll_direction:int = DIRECTION_UP

        self._display_width:int = self.display.spec.width
        self._display_height:int = self.display.spec.height

        self.width:int = self._display_width
        self.height:int = self._display_height

        self._window_info:memoryview = memoryview(array(self._32BIT_SIGNED_INT, bytearray(5*4)))

        # Setup window info
        self._window_info[_WGWI_WIDTH] = self.width
        self._window_info[_WGWI_HEIGHT] = self.height
        self._window_info[_WGWI_XPOS] = 0
        self._window_info[_WGWI_YPOS] = 0+ARROFF
        self._window_info[_WGWI_YSHIFT] = 0+ARROFF


        # Init Crop Streamers used for Blitting images that dont fit in their components
        self._crop_v_stream:VerticalCropStream = VerticalCropStream(DummyImageStream(1, 1), 0, 1)
        self._crop_h_stream:HorizontalCropStream = HorizontalCropStream(DummyImageStream(1, 1), 0, 1)


        # Call garbage collection to clean up potential temporary allocated objects
        if gc_collect:
            _gc_collect()



    def _create_test_screen(self, v=0):
        colors = [0xf800, 0xfba0, 0xffc0, 0xff20,   0xbfe0, 0x67e0, 0x07e2, 0x07f2,   0x07fd, 0x055f, 0x033f, 0x0ff,   0x281f, 0x781f, 0xe01f, 0xf814]
        components = []
        if v == 0:
            SLICES = 11
            TOFF = 0
        elif v == 1:
            SLICES = 10
            TOFF = -16
        for i in range(SLICES):
            components.append(FillComponent(i*16, i*16, 16, 80, colors[i]))
        for i in range(7):
            components.append(TextComponent(176+TOFF, i*32, 64, 32, "TEST", colors[i], colors[i+8]))
        return Screen(0, self, components)


    def _set_font(self, font):
        self._font._set_font(font)

    def _set_window(self, x:int, y:int, width:int, height:int, shift_y:int):
        self.width = width
        self.height = height
        self._window_info[_WGWI_WIDTH] = self.width
        self._window_info[_WGWI_HEIGHT] = self.height
        self._window_info[_WGWI_XPOS] = x
        self._window_info[_WGWI_YPOS] = y+ARROFF
        self._window_info[_WGWI_YSHIFT] = shift_y+ARROFF

    def _set_bgcolor(self, bgcolor:int):
        self.bgcolor = bgcolor

    def _set_screen_context(self, bgcolor:int):
        self._set_bgcolor(bgcolor)
        self._set_window(0, 0, self._display_width, self._display_height, 0)

    def _set_component_context(self, font, x:int, y:int, width:int, height:int, shift_y:int):
        self._font._set_font(font)
        self._set_window(x, y, width, height, shift_y)



    def _set_screen(self, old:Screen, s:Screen):
        cs = self._screen
        if old is not None and cs is not old:
            raise Exception("Cant switch screen if current screen is not active")
        if cs == s:
            return
        if s is None:
            self.screen = None
            self._set_screen_context(0)
        else:
            self._screen = s
            self._set_screen_context(s.bgcolor)







    def create_screen(self, bgcolor:int, components:list['Component'], font=fonts.sans24):
        return Screen(bgcolor, self, components, font=font)

    # Bit image to the screen at position, will automatically be cropped if it goes out of bounds
    @micropython.viper
    def blit(self, image, x:int, y:int):
        window_info:ptr32 = ptr32(self._window_info)

        y += window_info[_WGWI_YSHIFT]-ARROFF
        window_width:int = window_info[_WGWI_WIDTH]
        window_height:int = window_info[_WGWI_HEIGHT]

        width:int = int(image.width)
        height:int = int(image.height)
        skip_lines:int = 0
        if y < 0:
            skip_lines -= y
            height += y
            y = 0
        reduce_by_lines:int = skip_lines
        stripped_lines:int = (y+height)-window_height
        if stripped_lines > 0:
            reduce_by_lines += stripped_lines
            height -= stripped_lines
        if height <= 0:
            return
        skip_cols:int = 0
        if x < 0:
            skip_cols -= x
            width += x
            x = 0
        reduce_by_cols:int = skip_cols
        stripped_cols:int = (x+width)-window_width
        if stripped_cols > 0:
            reduce_by_cols += stripped_cols
            width -= stripped_cols
        if width <= 0:
            return

        if reduce_by_lines <= 0 and reduce_by_cols <= 0:
            self.display.wgl_blit(image, window_info[_WGWI_XPOS]+x, window_info[_WGWI_YPOS]-ARROFF+y)
            return

        if reduce_by_lines > 0:
            croppedy:VerticalCropStream = self._crop_v_stream
            croppedy._setup(image, skip_lines, height)
            image = croppedy

        if reduce_by_cols > 0:
            croppedx:HorizontalCropStream = self._crop_h_stream
            croppedx._setup(image, skip_cols, width)
            image = croppedx

        self.display.wgl_blit(image, window_info[_WGWI_XPOS]+x, window_info[_WGWI_YPOS]-ARROFF+y)
        image.reset()


    # Fill on screen but ignore current window
    def _fill_uw(self, color:int, x:int, y:int, width:int, height:int):
        self.display.wgl_fill(color, x, y, width, height)

    # Fill an area on the screen, will automatically be cropped to not leave the specified component
    @micropython.viper
    def fill(self, color:int, x:int, y:int, width:int, height:int):
        window_info:ptr32 = ptr32(self._window_info)

        y += window_info[_WGWI_YSHIFT]-ARROFF
        window_height:int = window_info[_WGWI_HEIGHT]
        window_width:int = window_info[_WGWI_WIDTH]
        if y < 0:
            height += y
            y = 0
        if x < 0:
            width += x
            x = 0
        max_y:int = y+height-1
        max_x:int = x+width-1
        if max_x >= window_width:
            width += (window_width-1)-max_x
        if max_y >= window_height:
            height += (window_height-1)-max_y
        if width <= 0 or height <= 0:
            return
        self.display.wgl_fill(color, window_info[_WGWI_XPOS]+x, window_info[_WGWI_YPOS]-ARROFF+y, width, height)


    # Draw a line, with a given thickness and color, between the start and endpoints,
    # Special cases like perfetly orthogonal lines are handled seperately
    # Other Lines are drawn using bresenhams line algorithm
    # with the difference that multiple oeprations to draw a single pixel are coalesced
    # into bigger operations to draw orthogonal lines.
    @micropython.viper
    def draw_line(self, color:int, width:int, x0:int, y0:int, x1:int, y1:int):
        # Line Thickness offset
        ltoff:int = (width-1)//2

        # Correct using line thickness offset
        x0 -= ltoff
        y0 -= ltoff
        x1 -= ltoff
        y1 -= ltoff

        dx:int = int(abs(x1 - x0))
        dy:int = int(-abs(y1 - y0))
        mdy:int = 0-dy

        # Check if line ends where it starts
        if dx == 0 and dy == 0:
            self.fill(color, x0, y0, width, width)
            return
        # Line doesnt span vertically, meaning its horizontal so it can be drawn using a single fill operation
        elif dy == 0:
            if x0 > x1:
                x2 = x0
                x0 = x1
                x1 = x2
            self.fill(color, x0, y0, dx+width, width)
            return
        # Line doesnt span horizontally, meaning its vertical, so it can be drawn with a single fill operation
        elif dx == 0:
            if y0 > y1:
                y2 = y0
                y0 = y1
                y1 = y2
            self.fill(color, x0, y0, width, mdy+width)
            return


        window_info:ptr32 = ptr32(self._window_info)

        # Shift content by y, do not shift before, else it would be shifted twice, when using simple fill operations
        yshift:int = window_info[_WGWI_YSHIFT]-ARROFF
        y0 += yshift
        y1 += yshift



        # Direction to move, x0-x1 cant be zero, same for y0-y1
        sx:int = 1 if (x0 < x1) else -1
        sy:int = 1 if (y0 < y1) else -1


        dx_x2:int = dx<<1
        dy_x2:int = dy<<1


        fill_x:int = -1
        fill_y:int = -1
        fill_w:int = -1
        fill_h:int = -1

        error:int = dx_x2+dy_x2
        window_width:int = window_info[_WGWI_WIDTH]
        window_height:int = window_info[_WGWI_HEIGHT]

        wgl_fill = self.display.wgl_fill


        wxpos:int = window_info[_WGWI_XPOS]
        wypos:int = window_info[_WGWI_YPOS]-ARROFF

        while True:
            # Cropping the current point so it doesnt overdraw
            rx0:int = x0
            ry0:int = y0

            rwidth:int = width
            rheight:int = width

            if rx0 < 0:
                rwidth += rx0
                rx0 = 0
            if ry0 < 0:
                rheight += ry0
                ry0 = 0

            max_width:int = window_width-rx0
            max_height:int = window_height-ry0

            if rwidth > max_width:
                rwidth += max_width-rwidth
            if rheight > max_height:
                rheight += max_height-rheight

            # Check how much the x and y coordinates differ from the current fill operation
            # Note: Since y/rx0 are guaranteed to be zero or greater, x_offset and y_offset cant be 0 if fill_x is -1
            x_offset:int = rx0-fill_x
            y_offset:int = ry0-fill_y

            if rwidth <= 0 or rheight <= 0:
                if fill_x != -1:
                    wgl_fill(color, wxpos+fill_x, wypos+fill_y, fill_w, fill_h)
                    fill_x = -1
                    fill_y = -1
            elif y_offset == 0 and x_offset == 0:
                if rheight > fill_h:
                    fill_h = rheight
                if rwidth > fill_w:
                    fill_w = rwidth
            elif y_offset == 0 and rheight == fill_h:
                if rx0 < fill_x:
                    fill_w += fill_x-rx0
                    fill_x = rx0
                elif (rx0+rwidth) > (fill_x+fill_w):
                    fill_w += (rx0+rwidth)-(fill_x+fill_w)
            elif x_offset == 0 and rwidth == fill_w:
                if ry0 < fill_y:
                    fill_h += fill_y-ry0
                    fill_y = ry0
                elif (ry0+rheight) > (fill_y+fill_h):
                    fill_h += (ry0+rheight)-(fill_y+fill_h)
            else:
                if fill_x != -1:
                    wgl_fill(color, wxpos+fill_x, wypos+fill_y, fill_w, fill_h)
                fill_x = rx0
                fill_y = ry0
                fill_w = rwidth
                fill_h = rheight

            error_change:int = 0
            if error >= dy:
                if x0 == x1:
                    break
                error_change += dy_x2
                x0 += sx
            if error <= dx:
                if y0 == y1:
                    break
                error_change += dx_x2
                y0 += sy
            error += error_change
        if fill_x != -1:
            wgl_fill(color, wxpos+fill_x, wypos+fill_y, fill_w, fill_h)


    # Draw a line using polar coordinates
    def draw_line_polar(self, color:int, width:int, x:int, y:int, theta:int, r0:int, r1:int):
        theta2:float = theta*_C_TO_RADIANS
        xdelta:float = math.sin(theta2)
        ydelta:float = math.cos(theta2)
        x0:int = x + int(xdelta * r0)
        x1:int = x + int(xdelta * r1)
        y0:int = x - int(ydelta * r0)
        y1:int = x - int(ydelta * r1)
        self.draw_line(color, width, x0, y0, x1, y1)


    # Get bounding box of a string drawn on the screen
    @micropython.native
    def string_bounding_box(self, s:str) -> tuple[int, int]:
        font:WaspFontStream = self._font
        height:int = font._font_height
        width:int = 0
        for c in s:
            font._set_ch(c)
            cw2:int = int(font.width)
            ch2:int = int(font.height)
            width += cw2
            if ch2 > height:
                height = ch2
        return (width, height)



    # Draw string to the screen at position, sadly cant be viper as it doesnt
    #Temporarily Non-Native
    #@micropython.native
    def draw_string(self, color:int, bgcolor:int, s:str, x:int, y:int):
        window_width:int = self.width
        window_height:int = self.height
        font:WaspFontStream = self._font
        if bgcolor < 0:
            bgcolor = self.bgcolor
        font._set_color(color, bgcolor)

        font_height = font._font_height

        if y >= window_height:
            return
        if x >= window_width:
            return
        if y+font_height <= 0:
            return

        for c in s:
            font._set_ch(c)
            cw:int = int(font.width)
            ch:int = int(font.height)
            if x+cw <= 0:
                x += cw
                continue
            if x >= window_width:
                break
            self.blit(font, x, y)
            x += cw

    def draw_string_a(self, color:int, bgcolor:int, s:str, x:int, y:int, align:int):
        (rw, rh) = self.string_bounding_box(s)
        rwidth:int = int(rw)
        if align == ALIGNMENT_CENTER:
            offset:int = rwidth//2
            self.draw_string(color, bgcolor, s, x-offset, y)
        elif align == ALIGNMENT_LEFT:
            self.draw_string(color, bgcolor, s, x, y)
        elif align == ALIGNMENT_RIGHT:
            self.draw_string(color, bgcolor, s, x-rwidth, y)
        else:
            raise Exception("Shouldnt Happen")





class DummyDisplay(DisplayProtocol):
    def __init__(self, width:int, height:int, color_format:int=COLORFORMAT_RGB565):
        self.spec = DisplaySpec(width, height, color_format, scroll_directions=frozenset([]))
    def wgl_vscroll(self, pixels:int):
        pass
    def wgl_fill(self, color:int, x:int, y:int, width:int, height:int):
        print("FILL "+hex(color)+", X:"+str(x)+", Y:"+str(y)+", W:"+str(width)+", H:"+str(height))
    def wgl_blit(self, image:ImageStream, x:int, y:int):
        print("BLIT IMAGE:    X:"+str(x)+", Y:"+str(y)+", W:"+str(image.width)+", H:"+str(image.height))
        print("  "+image.info())
class DummyImageStream():
    def __init__(self, width:int, height:int):
        self.width:int = width
        self.height:int = height
        self._remaining:int = self.width*self.height
    def get_remaining(self) -> int:
        return self._remaining
    def reset(self):
         self._remaining = self.width*self.height
    def read_pixels(self, read:bool, buf:memoryview, n:int, offset:int) -> int:
        if n > self._remaining:
            n = self._remaining
        if n <= 0:
            return 0
        self._remaining -= n
        return n
    def info(self) -> str:
        return "DUMMY_STREAM("+str(self.width)+", "+str(self.height)+")"




if __name__ == '__main__':
    dis = DummyDisplay(240, 240)
    dg = WatchGraphics(dis)
    print("Draw Line 1")
    dg.draw_line(0, 1,  0, 1,  0, 1)
    print("Draw Line 2")
    dg.draw_line(0, 1,  0, 1,  6, 4)
    print("Draw Line 3")
    dg.draw_line(0, 3,  -1, -1,  6, 4)
    print("Done")

    img = DummyImageStream(240, 240)
    img2 = DummyImageStream(10, 10)

    dg.blit(img, 10, 10)
    dg.blit(img2, 10, 10)
    dg.blit(img2, 239, 239)
