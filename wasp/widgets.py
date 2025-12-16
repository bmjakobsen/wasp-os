# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Widget library
~~~~~~~~~~~~~~~~~

The widget library allows common fragments of logic and drawing code to be
shared between applications.
"""

import fonts
import icons
import wasp
import watch
import watchgl

from micropython import const



_wgl = wasp.watch.drawable._wgl_bak

class BatteryMeter():
    """Battery meter widget.

    A simple battery meter with a charging indicator, will draw at the
    top-right of the display.
    """
    def __init__(self):
        self.level = -2
        self._icon1 = watchgl.create_wasp_image_stream(icons.battery)
        self._icon2 = watchgl.create_wasp_image_stream(icons.battery)
        self._icon2._set_color(3, 0xf800)

    def draw(self):
        """Draw from meter (from scratch)."""
        self.level = -2
        self.update()

    def update(self):
        """Update the meter.

        The update is lazy and won't redraw unless the level has changed.
        """
        if _wgl.redraw_widgets:
            self.level = -2

        nlevel = -2
        if watch.battery.charging():
            nlevel = -1
        else:
            nlevel = watch.battery.level()
        if self.level == nlevel:
            return
        self.level = nlevel
        self._draw_function(_wgl)
    def _draw_function(self, wgl):
        self._icon1._set_color(3, wasp.system.theme('battery'))
        level = self.level
        if level == -1:
            wgl.blit(self._icon1, 239-self._icon1.width, 0)
        else:
            green = level // 3
            if green > 31:
                green = 31
            red = 31-green
            rgb = (red << 11) + (green << 6)

            if level > 5:
                wgl.blit(self._icon1, 239-self._icon1.width, 0)
            else:
                rgb = 0xf800
                wgl.blit(self._icon2, 239-self._icon2.width, 0)
            w = self._icon1.width - 10
            x = 239 - 5 - w
            h = 2*level // 11
            if 18 - h != 0:
                wgl.fill(0, x, 9, w, 18-h)
            if h != 0:
                wgl.fill(rgb, x, 27-h, w, h)




class Clock():
    """Small clock widget."""
    def __init__(self, enabled=True):
        self.on_screen = None
        self.enabled = enabled



    def draw(self):
        """Redraw the clock from scratch.

        The container is required to clear the canvas prior to the redraw
        and the clock is only drawn if it is enabled.
        """
        self.on_screen = None
        self.update()

    def update(self):
        """Update the clock widget if needed.

        This is a lazy update that only redraws if the time has changes
        since the last call *and* the clock is enabled.

        :returns: An time tuple if the time has changed since the last call,
                  None otherwise.
        """
        if _wgl.redraw_widgets:
            self.on_screen = None

        now = wasp.watch.rtc.get_localtime()
        on_screen = self.on_screen
        if on_screen and on_screen == now:
            return None

        if self.enabled and (not on_screen
                or now[4] != on_screen[4] or now[3] != on_screen[3]):
            self._draw_function(_wgl, now)
        self.on_screen = now
        return now

    def _draw_function(wgl, now):
        r = wgl.get_font()
        try:
            wgl.set_font(fonts.sans28)
            t1 = '{:02}:{:02}'.format(now[3], now[4])
            wgl.draw_string(wasp.system.theme('status-clock'), 0, t1, 52, 4, width=138, align=ALIGNMENT_CENTER)
        finally:
            wgl.set_font(r)

class NotificationBar():
    """Show BT status and if there are pending notifications."""
    def __init__(self, x:int=0, y:int=0):
        self.x = x
        self.y = y
        self.state = (None, None)
        self._icon_ble = watchgl.create_wasp_image_stream(icons.blestatus)
        self._icon_notif = watchgl.create_wasp_image_stream(icons.notification)

    def draw(self):
        """Redraw the notification widget.

        For this simple widget :py:meth:`~.draw` is simply a synonym for
        :py:meth:`~.update` because we unconditionally update from scratch.
        """
        self.state = (None, None)
        self.update()

    def update(self):
        """Update the widget.

        This widget does not implement lazy redraw internally since this
        can often be implemented (with less state) by the container.
        """
        if _wgl.redraw_widgets:
            self.state = (None, None)


        draw = watch.drawable

        self._draw_function(_wgl)

        new_state = (bool(wasp.watch.connected()), bool(wasp.system.notifications))

        if new_state == self.state:
            return
        self.state = new_state
        self._draw_function(_wgl)


    def _draw_function(self, wgl):
        self._icon_ble._set_color(3, wasp.system.theme('ble'))
        self._icon_notif._set_color(3, wasp.system.theme('notify-icon'))

        x = self.x
        y = self.y

        connected, notifications = self.state
        if connected:
            wgl.blit(self._icon_ble, x, y)
            if notifications:
                wgl.blit(self._icon_notif, x+22, y),
            else:
                wgl.fill(0, x+22, y, 30, 32)
        elif notifications:
            wgl.blit(self._icon_notif, x, y)
            wgl.fill(0, x+30, y, 22, 32)
        else:
            wgl.fill(0, x, y, 52, 32)

class StatusBar():
    """Combo widget to handle notification, time and battery level."""
    def __init__(self):
        self._notif = NotificationBar(flags=flags, no_draw=True, xoff=0)
        self._clock = Clock(flags=flags, no_draw=True, xoff=52)
        self._meter = BatteryMeter(flags=flags, no_draw=True, xoff=208)

    @property
    def clock(self):
        """True if the clock should be included in the status bar, False
        otherwise.
        """
        return self._clock.enabled

    @clock.setter
    def clock(self, enabled):
        self._clock.enabled = enabled

    def draw(self):
        """Redraw the status bar from scratch."""
        self._clock.draw()
        self._meter.draw()
        self._notif.draw()

    def update(self):
        if _wgl.redraw_widgets:
            self.draw()

        """Lazily update the status bar.

        :returns: An time tuple if the time has changed since the last call,
                  None otherwise.
        """
        now = self._clock.update()
        if now:
            self._meter.update()
            self._notif.update()
        return now


class ScrollIndicator():
    """Scrolling indicator.

    A pair of arrows that prompted the user to swipe up/down to access
    additional pages of information.
    """
    def __init__(self, x=240-18, y=240-24):
        self.x = x
        self.y = y
        self.up = True
        self.down = True
        self.state = (None, None)
        self._icon_up = watchgl.create_wasp_image_stream(icons.up_arrow)
        self._icon_down = watchgl.create_wasp_image_stream(icons.down_arrow)

    def draw(self):
        """Draw from scrolling indicator.

        For this simple widget :py:meth:`~.draw` is simply a synonym for
        :py:meth:`~.update`.
        """
        self.state = (None, None)
        self.update()

    def update(self):
        if _wgl.redraw_widgets:
            self.state = (None, None)

        """Update from scrolling indicator."""
        new_state = (self.up, self.down)
        if new_state == self.state:
            return
        self.state = new_state
        self._draw_function(_wgl)

    def _draw_function(self, wgl):
        draw = watch.drawable
        color = wasp.system.theme('scroll-indicator')
        self._icon_up._set_color(3, color)
        self._icon_down._set_color(3, color)
        if self.up:
            wgl.blit(self._icon_up, x, y)
        if self.down:
            wgl.blit(self._icon_down, x, y+13)

class Button():
    """A button with a text label."""
    def __init__(self, x, y, w, h, label)(None, None):
        super().__init__(x, y, w, h, self._draw_function, font=fonts.sans24, state={'toggle': state}, flags=flags)
        self._im = (x, y, w, h, label)
        self._label = label

    def draw(self):
        """Draw the button."""
        self.dirty = True
        self.update()

    def update(self, toggle=None):
        draw = wasp.watch.drawable
        im = self._im

        if toggle is not None:
            self.set_var('toggle', toggle)

        if not self.bound and self.dirty:
            self.direct_draw(_wgl)
            self.dirty = False

    def _draw_function(self, com, state, wgl):
        label = self._label

        _, _, w, h, _ = self._im
        if state['toggle']:
            bg = wasp.watch.drawable.darken(wasp.system.theme('ui'))
        else:
            bg = wasp.watch.drawable.darken(wasp.system.theme('mid'))
        frame = wasp.system.theme('mid')
        txt = wasp.system.theme('bright')

        wgl.fill(bg, 0, 0, w, h)
        wgl.draw_string_a(txt, bg, label, 2, h//2-12, width=w-4, align=watchgl.ALIGNMENT_CENTER)
        wgl.fill(frame, 0, 0, w, 2)
        wgl.fill(frame, 0, h-2, w, 2)
        wgl.fill(frame, 0, 2, 2, h-4)
        wgl.fill(frame, w-2, 2, 2, h-4)

    def touch(self, event):
        """Handle touch events."""
        x = event[1]
        y = event[2]

        # Adopt a slightly oversized hit box
        im = self._im
        x1 = im[0] - 10
        x2 = x1 + im[2] + 20
        y1 = im[1] - 10
        y2 = y1 + im[3] + 20

        if x >= x1 and x < x2 and y >= y1 and y < y2:
            return True

        return False

class ToggleButton(Button):
    """A button with a text label that can be toggled on and off."""
    def __init__(self, x, y, w, h, label, flags:int=watchgl.COMFLAG_DEFAULT):
        super().__init__(x, y, w, h, label, state=False, flags=flags)

    @property
    def state(self):
        self.get_var('toggle')
    @state.setter
    def state(self, v):
        self.set_var('toggle', v)

    def touch(self, event):
        """Handle touch events."""
        if super().touch(event):
            self.set_var('toggle', (not self._state['toggle']))
            self.draw()
            return True
        else:
            return False

class Checkbox(watchgl.Component):
    """A simple (labelled) checkbox."""
    def __init__(self, x, y, label=None, width:int=None, flags=watchgl.COMFLAG_DEFAULT):
        if width is not None and width < 32:
            raise Exception("Width must be 32 or greater")
        if width is not None and label is None:
            x = (x+width)-32-4
            width = 32
        elif width is None and label is None:
            width = 32
        elif width is None:
            width = 240-x
        else:
            pass

        super().__init__(x, y, width, 32, self._draw_function, font=fonts.sans24, state={'toggle': False}, flags=flags)

        self._label = label
        box_x = 0
        if label is not None:
            box_x = width-32-4
        self._box_x = box_x
        self._im = (x, y, label)
        self._icon_on = watchgl.create_wasp_image_stream(icons.checkbox)
        self._icon_off = watchgl.create_wasp_image_stream(icons.checkbox)

    @property
    def label(self):
        return self._label
    @property
    def state(self):
        return self.get_var('toggle')
    @state.setter
    def state(self, v):
        self.set_var('toggle', v)

    def draw(self):
        """Draw the checkbox and label."""
        self.dirty = True
        self.update()

    def update(self):
        """Draw the checkbox."""
        if not self.bound and self.dirty:
            self.direct_draw(_wgl)
            self.dirty = False


    def _draw_function(self, com, state, wgl):
        color1 = wasp.system.theme('ui')
        color2 = wasp.watch.drawable.lighten(color1, wasp.system.theme('contrast'))
        self._icon_on._set_color(1, color1)
        self._icon_on._set_color(2, color2)
        self._icon_on._set_color(3, color2)
        self._icon_off._set_color(1, 0)
        self._icon_off._set_color(2, 0)
        self._icon_off._set_color(3, wasp.system.theme('mid'))
        label = self._label
        box_x = self._box_x
        if label is not None:
            wgl.draw_string_a(wasp.system.theme('bright'), 0, label, 0, 4, width=0, align=watchgl.ALIGNMENT_LEFT)
        if state['toggle']:
            wgl.blit(self._icon_on, box_x, 0)
        else:
            wgl.blit(self._icon_off, box_x, 0)

    def touch(self, event):
        """Handle touch events."""
        x = event[1]
        y = event[2]
        im = self._im
        if (self.label or im[0] <= x < im[0]+40) and im[1] <= y < im[1]+40:
            self.set_var('toggle', not (self._state['toggle']))
            self.update()
            return True
        return False

class GfxButton(watchgl.Component):
    """A button with a graphical icon."""
    def __init__(self, x, y, gfx, flags=watchgl.COMFLAG_DEFAULT):
        _gfx = watchgl.create_wasp_image_stream(gfx)
        width, height = (_gfx.width, _gfx.height)
        if width % watchgl.TILE_SIZE != 0:
            width += watchgl.TILE_SIZE - (width % watchgl.TILE_SIZE)
        if height % watchgl.TILE_SIZE != 0:
            height += watchgl.TILE_SIZE - (height % watchgl.TILE_SIZE)


        super().__init__(x, y, width, height, self._draw_function, flags=flags)
        self._im = (x, y)
        self.gfx = gfx
        self._gfx = _gfx

    def draw(self):
        """Draw the button."""
        im = self._im

        if not self.bound:
            self.direct_draw(_wgl)
            self.dirty = False

    def _draw_function(self, com, state, wgl):
        wgl.blit(self._gfx, 0, 0)

    def touch(self, event):
        x = event[1]
        y = event[2]

        # Adopt a slightly oversized hit box
        im = self._im
        gfx = self._gfx
        x1 = im[0] - 10
        x2 = x1 + gfx.width + 20
        y1 = im[1] - 10
        y2 = y1 + gfx.height + 20

        if x >= x1 and x < x2 and y >= y1 and y < y2:
            return True

        return False

_SLIDER_KNOB_DIAMETER = const(40)
_SLIDER_KNOB_RADIUS = const(_SLIDER_KNOB_DIAMETER // 2)
_SLIDER_KNOB_OFFSET = const(6)
_SLIDER_WIDTH = const(220)
_SLIDER_TRACK = const(_SLIDER_WIDTH - _SLIDER_KNOB_DIAMETER)
_SLIDER_TRACK_HEIGHT = const(8)
_SLIDER_TRACK_Y1 = const(_SLIDER_KNOB_RADIUS - (_SLIDER_TRACK_HEIGHT // 2))
_SLIDER_TRACK_Y2 = const(_SLIDER_TRACK_Y1 + _SLIDER_TRACK_HEIGHT)

class Slider(watchgl.Component):
    """A slider to select values."""
    def __init__(self, steps, x=10, y=90, color=None, width=220, height=40, flags=watchgl.COMFLAG_DEFAULT):
        super().__init__(x, y, width, height, self._draw_function, state={'value': 0 }, flags=flags)
        self._steps = steps
        self._stepsize = _SLIDER_TRACK / (steps-1)
        self._color = color
        self._lowlight = None
        self._icon_knob = watchgl.create_wasp_image_stream(icons.knob)

    @property
    def value(self):
        return self.get_var('value')
    @value.setter
    def value(self, v):
        self.set_var('value', v)

    def _draw_function(self, com, state, wgl):
        if self._color is None:
            self._color = wasp.system.theme('ui')
        self._icon_knob._set_color(3, self._color)
        if self._lowlight is None:
            self._lowlight = watch.drawable.lighten(self._color, wasp.system.theme('contrast'))

        knob_x = (_SLIDER_TRACK * self.value) // (self._steps-1)
        wgl.fill(0, 0, 0, self.width, self.height)
        wgl.fill(self._color, _SLIDER_KNOB_OFFSET, _SLIDER_TRACK_Y1, self.width-(_SLIDER_KNOB_OFFSET*2), _SLIDER_TRACK_HEIGHT)
        wgl.blit(self._icon_knob, knob_x, 0)

    def draw(self):
        if not self.bound:
            self.direct_draw(_wgl)
            dirty = False

    def update(self):
        if not self.bound and self.dirty:
            self.draw()

    def touch(self, event):
        tx = event[1]
        threshold = self.x + 20 - (self._stepsize / 2)
        v = int((tx - threshold) / self._stepsize)
        if v < 0:
            v = 0
        elif v >= self._steps:
            v = self._steps - 1
        changed = self.value != v
        self.value = v
        return changed

class Spinner(watchgl.Component):
    """A simple Spinner widget.

    In order to have large enough hit boxes the spinner is a fairly large
    widget and requires 60x120 px.
    """
    # mn is Miniumum, mx is Maximum
    def __init__(self, x, y, mn, mx, field=1, incr=1, flags=watchgl.COMFLAG_DEFAULT):
        super().__init__(x, y, 64, 128, self._draw_function, font=fonts.sans28, state={'value': mn }, flags=flags)
        self._im = bytes((x, y, mn, mx, field, incr))
        self._icon_up = watchgl.create_wasp_image_stream(icons.up_arrow)
        self._icon_down = watchgl.create_wasp_image_stream(icons.down_arrow)

    @property
    def value(self):
        return self.get_var('value')
    @value.setter
    def value(self, v):
        self.set_var('value', v)


    def _draw_function(self, com, state, wgl):
        im = self._im
        fg = wasp.watch.drawable.lighten(wasp.system.theme('ui'), wasp.system.theme('contrast'))
        self._icon_up._set_color(3, fg)
        self._icon_down._set_color(3, fg)
        wgl.blit(self._icon_up, 32-8, 24)
        wgl.blit(self._icon_down, 32-8, 24+100-20-9)

        s = str(state['value'])
        if len(s) < im[4]:
            s = '0' * (im[4] - len(s)) + s
        wgl.draw_string_a(wasp.system.theme('bright'), 2, s, 0, 24+40-14, width=60, align=watchgl.ALIGNMENT_CENTER)


    def draw(self):
        """Draw the spinner"""
        self.dirty = True
        self.update()


    def update(self):
        """Update the spinner value."""
        if not self.bound and self.dirty:
            self.direct_draw(_wgl)
            self.dirty = False

    def touch(self, event):
        x = event[1]
        y = event[2]
        im = self._im
        if x >= im[0] and x < im[0]+60 and y >= im[1] and y < im[1]+120:
            if y < im[1] + 60:
                self.value += im[5]
                if self.value > im[3]:
                    self.value = im[2]
            else:
                self.value -= im[5]
                if self.value < im[2]:
                    self.value = im[3]
            while self.value % im[5] != 0:
                self.value -= 1

            self.update()
            return True

        return False

class Stopwatch:
    """A stopwatch widget"""
    def __init__(self, y):
        self._y = y
        self.reset()

    def start(self):
        uptime = wasp.watch.rtc.get_uptime_ms() // 10
        self._started_at = uptime - self.count

    def stop(self):
        self._started_at = 0

    @property
    def started(self):
        return bool(self._started_at)

    def reset(self):
        self.count = 0
        self._started_at = 0
        self._last_count = -1

    def draw(self):
        self._last_count = -1
        self.update()

    def update(self):
        # Before we do anything else let's make sure count is
        # up to date
        if self._started_at:
            uptime = wasp.watch.rtc.get_uptime_ms() // 10
            self.count = uptime - self._started_at
            if self.count > 999*60*100:
                self.reset()

        if self._last_count != self.count:
            centisecs = self.count
            secs = centisecs // 100
            centisecs %= 100
            minutes = secs // 60
            secs %= 60

            t1 = '{}:{:02}'.format(minutes, secs)
            t2 = '{:02}'.format(centisecs)

            y = self._y
            draw = wasp.watch.drawable
            draw.set_font(fonts.sans36)
            draw.set_color(draw.lighten(wasp.system.theme('ui'), wasp.system.theme('contrast')))
            w = fonts.width(fonts.sans36, t1)
            draw.string(t1, 180-w, y)
            draw.fill(0, 0, y, 180-w, 36)
            draw.set_font(fonts.sans24)
            draw.string(t2, 180, y+18, width=46)

            self._last_count = self.count

class ConfirmationView:
    """Confirmation widget allowing user confirmation of a setting."""

    def __init__(self):
        self.active = False
        self.value = False
        self._yes = Button(20, 140, 90, 45, 'Yes')
        self._no = Button(130, 140, 90, 45, 'No')

    def draw(self, message):
        draw = wasp.watch.drawable
        mute = wasp.watch.display.mute

        mute(True)
        draw.set_color(wasp.system.theme('bright'))
        draw.set_font(fonts.sans24)
        draw.fill()
        draw.string(message, 0, 60)
        self._yes.draw()
        self._no.draw()
        mute(False)

        self.active = True

    def touch(self, event):
        if not self.active:
            return False

        if self._yes.touch(event):
            self.active = False
            self.value = True
            return True
        elif self._no.touch(event):
            self.active = False
            self.value = False
            return True

        return False
