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
        self.update(_redraw=True)

    def update(self, _redraw=False):
        """Update the meter.

        The update is lazy and won't redraw unless the level has changed.
        """
        if _redraw or _wgl.redraw_widgets:
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
        self.update(_redraw=True)

    def update(self, _redraw=False):
        """Update the clock widget if needed.

        This is a lazy update that only redraws if the time has changes
        since the last call *and* the clock is enabled.

        :returns: An time tuple if the time has changed since the last call,
                  None otherwise.
        """
        if _redraw or _wgl.redraw_widgets:
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

    def _draw_function(self, wgl, now):
        t1 = '{:02}:{:02}'.format(now[3], now[4])
        wgl.draw_string_a(wasp.system.theme('status-clock'), 0, t1, 52, 4, width=138, align=watchgl.ALIGNMENT_CENTER, font=fonts.sans28)

class NotificationBar():
    """Show BT status and if there are pending notifications."""
    def __init__(self, x:int=0, y:int=0):
        self.x = x
        self.y = y
        self._state = (None, None)
        self._icon_ble = watchgl.create_wasp_image_stream(icons.blestatus)
        self._icon_notif = watchgl.create_wasp_image_stream(icons.notification)

    def draw(self):
        """Redraw the notification widget.

        For this simple widget :py:meth:`~.draw` is simply a synonym for
        :py:meth:`~.update` because we unconditionally update from scratch.
        """
        self.update(_redraw=True)

    def update(self, _redraw=False):
        """Update the widget.

        This widget does not implement lazy redraw internally since this
        can often be implemented (with less state) by the container.
        """
        if _redraw or _wgl.redraw_widgets:
            self._state = (None, None)


        draw = watch.drawable
        new_state = (bool(wasp.watch.connected()), bool(wasp.system.notifications))

        if new_state == self._state:
            return
        self._state = new_state
        self._draw_function(_wgl)


    def _draw_function(self, wgl):
        self._icon_ble._set_color(3, wasp.system.theme('ble'))
        self._icon_notif._set_color(3, wasp.system.theme('notify-icon'))

        x = self.x
        y = self.y

        connected, notifications = self._state
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
        self._notif = NotificationBar()
        self._clock = Clock()
        self._meter = BatteryMeter()

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
        self._state = (None, None)
        self._icon_up = watchgl.create_wasp_image_stream(icons.up_arrow)
        self._icon_down = watchgl.create_wasp_image_stream(icons.down_arrow)

    def draw(self):
        """Draw from scrolling indicator.

        For this simple widget :py:meth:`~.draw` is simply a synonym for
        :py:meth:`~.update`.
        """
        self.update(_redraw=True)

    def update(self, _redraw=False):
        if _redraw or _wgl.redraw_widgets:
            self._state = (None, None)

        """Update from scrolling indicator."""
        new_state = (self.up, self.down)
        if new_state == self._state:
            return
        self._state = new_state
        self._draw_function(_wgl)

    def _draw_function(self, wgl):
        draw = watch.drawable
        color = wasp.system.theme('scroll-indicator')
        self._icon_up._set_color(3, color)
        self._icon_down._set_color(3, color)
        if self.up:
            wgl.blit(self._icon_up, self.x, self.y)
        if self.down:
            wgl.blit(self._icon_down, self.x, self.y+13)

class Button():
    """A button with a text label."""
    def __init__(self, x, y, w, h, label):
        self._im = (x, y, w, h, label)
        self._colors = (None, None, None)
        self._rcolors = (None, None, None)

    def draw(self):
        """Draw the button."""
        bg = wasp.watch.drawable.darken(wasp.system.theme('ui'))
        frame = wasp.system.theme('mid')
        txt = wasp.system.theme('bright')
        self.set_colors('ui', 'mid', 'bright')
        self.update(_redraw=True)

    def set_colors(self, bg, frame, txt):
        self._colors = (bg, frame, txt)

    def update(self, _redraw=False):
        draw = wasp.watch.drawable
        im = self._im
        if _redraw or _wgl.redraw_widgets:
            self._rcolors = (None, None, None)

        bg, frame, txt = self._colors
        if type(bg) == str:
            bg = wasp.system.theme(bg)
        if type(frame) == str:
            frame = wasp.system.theme(frame)
        if type(txt) == str:
            txt = wasp.system.theme(frame)
        new_colors = (bg, frame, txt)

        if new_colors == self._rcolors:
            return
        self._rcolors = new_colors
        self._state = new_state

        self._draw_function(_wgl, bg, frame, text)

    def _draw_function(self, wgl, bg, frame, txt):
        label = self._label

        x, y, w, h, label = self._im
        wgl.fill(bg, x, y, w, h)

        wgl.fill(bg, 0, 0, w, h)
        wgl.draw_string_a(txt, bg, label, 2, h//2-12, width=w-4, align=watchgl.ALIGNMENT_CENTER, font=fonts.sans24)
        wgl.fill(frame, x, y, w, 2)
        wgl.fill(frame, x, y+h-2, w, 2)
        wgl.fill(frame, x, y+2, 2, h-4)
        wgl.fill(frame, x+w-2, y+2, 2, h-4)

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
    def __init__(self, x, y, w, h, label):
        super().__init__(x, y, w, h, label)
        self.state = False

    def draw(self):
        draw = wasp.watch.drawable
        self._set_colors(('ui' if self.state else 'mid'), 'mid', 'bright')
        self.update()


    def touch(self, event):
        """Handle touch events."""
        if super().touch(event):
            self.state = not self.state
            self.draw()
            return True
        else:
            return False

class Checkbox():
    """A simple (labelled) checkbox."""
    def __init__(self, x, y, label=None):
        tx = x
        if label:
            x = 239 - 32 - 4
        self._im = (x, tx, y, label)
        self.state = False
        self._state = False
        self._icon_cb = watchgl.create_wasp_image_stream(icons.checkbox)
    @property
    def label(self):
        return self._im[2]

    def draw(self):
        """Draw the checkbox and label."""
        self.update(_redraw=True)

    def update(self, _redraw=False):
        """Draw the checkbox."""
        if _redraw or _wgl.redraw_widgets:
            self._state = None
        if self.state == self._state:
            return
        self._state = self.state
        self._draw_function(_wgl, self.state)


    def _draw_function(self, wgl, state):
        if state:
            color1 = wasp.system.theme('ui')
            color2 = wasp.watch.drawable.lighten(color1, wasp.system.theme('contrast'))
            fg = color2
        else:
            color1 = 0
            color2 = 0
            fg = wasp.system.theme('mid')
        ix, tx, iy, label = self._im
        cbox = self._icon_cb
        cbox._set_color(1, color1)
        cbox._set_color(2, color2)
        cbox._set_color(3, fg)

        if label:
            wgl.draw_string(wasp.system.theme('bright'), 0, label, tx, iy+6, font=fonts.sans24)

        wgl.blit(cbox, ix, iy)

    def touch(self, event):
        """Handle touch events."""
        x = event[1]
        y = event[2]
        ix, iy, _ = self._im
        if (self.label or ix <= x < ix+40) and iy <= y < iy+40:
            self.state = not self.state
            self.update()
            return True
        return False

class GfxButton():
    """A button with a graphical icon."""
    def __init__(self, x, y, gfx):
        self._im = (x, y)
        self.gfx = gfx
        self._gfx = watchgl.create_wasp_image_stream(gfx)

    def draw(self):
        """Draw the button."""
        self.update(_redraw=True)
    def update(self, _redraw=False):
        if not _redraw and not _wgl.redraw_widgets:
            return
        x, y = self._im
        wgl.blit(self._gfx, x, y)

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

class Slider():
    """A slider to select values."""
    def __init__(self, steps, x=10, y=90, color=None):
        self.value = 0
        self._value = None

        self._steps = steps
        self._stepsize = _SLIDER_TRACK / (steps-1)
        self._x = x
        self._y = y
        self._color = color
        self._lowlight = None
        self._icon_knob = watchgl.create_wasp_image_stream(icons.knob)

    def draw(self):
        self.update(_redraw=True)

    def update(self, _redraw=False):
        if _redraw or _wgl.redraw_widgets:
            self._value = None
        if self.value == self._value:
            return
        self._value = self.value
        self._draw_function(_wgl, self.value)

    def _draw_function(self, wgl, value):
        x = self._x
        y = self._y
        if self._color is None:
            self._color = wasp.system.theme('ui')
        color = self._color
        if self._lowlight is None:
            self._lowlight = watch.drawable.lighten(self._color, wasp.system.theme('contrast'))
        light = self._lowlight

        knob_x = x + (_SLIDER_TRACK * value) // (self._steps-1)
        w1 = x - knob_x
        wgl.fill(0, x, y, _SLIDER_WIDTH, _SLIDER_TRACK_Y1)
        wgl.fill(self._color, x+_SLIDER_KNOB_RADIUS, y+_SLIDER_TRACK_Y1, w1-SLIDER_KNOB_RADIUS, _SLIDER_TRACK_HEIGHT)
        wgl.fill(self._light, knob_x, y+_SLIDER_TRACK_Y1, (_SLIDER_WIDTH-w1)-SLIDER_KNOB_RADIUS, _SLIDER_TRACK_HEIGHT)
        wgl.fill(0, x, y+_SLIDER_TRACK_Y2, _SLIDER_WIDTH, _SLIDER_TRACK_Y1)

        icon_knob = self._icon_knob
        icon_knob._set_color(3, self._color)
        wgl.blit(icon_knob, knob_x, y)

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

class Spinner():
    """A simple Spinner widget.

    In order to have large enough hit boxes the spinner is a fairly large
    widget and requires 60x120 px.
    """
    # mn is Miniumum, mx is Maximum
    def __init__(self, x, y, mn, mx, field=1, incr=1):
        self._im = bytes((x, y, mn, mx, field, incr))
        self.value = mn
        self._value = None
        self._icon_up = watchgl.create_wasp_image_stream(icons.up_arrow)
        self._icon_down = watchgl.create_wasp_image_stream(icons.down_arrow)


    def draw(self):
        """Draw the spinner"""
        self.update(_redraw=True)


    def update(self, _redraw=False):
        """Update the spinner value."""
        if _redraw or _wgl.redraw_widgets:
            self._value = None
        if self.value == self._value:
            return
        self.value = self._value
        self._draw_function(self, _wgl, self.value)

    def _draw_function(self, wgl, value):
        x, y, mn, mx, field, _ = self._im


        fg = wasp.watch.drawable.lighten(wasp.system.theme('ui'), wasp.system.theme('contrast'))
        self._icon_up._set_color(3, fg)
        self._icon_down._set_color(3, fg)
        wgl.blit(self._icon_up, x+30-8, y+20)
        wgl.blit(self._icon_down, x+30-8, y+120-20-9)

        s = str(value)
        ls = len(s)
        if ls < field:
            s = '0' * (field - ls) + s
        wgl.draw_string_a(wasp.system.theme('bright'), 0, s, x, y+60-14, width=60, align=watchgl.ALIGNMENT_CENTER, font=fonts.sans28)



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
        self.update(_redraw=True)

    def update(self, redraw=False):
        # Before we do anything else let's make sure count is
        # up to date
        if _redraw or _wgl.redraw_widgets:
            self._last_count = -1

        if self._started_at:
            uptime = wasp.watch.rtc.get_uptime_ms() // 10
            self.count = uptime - self._started_at
            if self.count > 999*60*100:
                self.reset()

        if self._last_count != self.count:
            self._draw_function(_wgl, self.count)
            self._last_count = self.count

    def _draw_function(self, wgl, count):
        y = self._y
        centisecs = count
        secs = centisecs // 100
        centisecs %= 100
        minutes = secs // 60
        secs %= 60

        t1 = '{}:{:02}'.format(minutes, secs)
        t2 = '{:02}'.format(centisecs)

        color = wasp.watch.drawable.lighten(wasp.system.theme('ui'), wasp.system.theme('contrast'))
        wgl.draw_string_a(color, 0, t1, 20, y, width=152, align=watchgl.ALIGNMENT_RIGHT, font=fonts.sans36)
        wgl.draw_string_a(color, 0, t2, 180, y+18, width=46, align=watchgl.ALIGNMENT_CENTER, font=fonts.sans24)

class ConfirmationView:
    """Confirmation widget allowing user confirmation of a setting."""

    def __init__(self):
        self.active = False
        self.value = False
        self._yes = Button(20, 140, 90, 45, 'Yes')
        self._no = Button(130, 140, 90, 45, 'No')
        self._message = None

    def draw(self, message):
        draw = wasp.watch.drawable
        mute = wasp.watch.display.mute

        mute(True)
        color = wasp.system.theme('bright')
        wgl.fill(0, 0, 0, 240, 240)
        wgl.draw_string_a(color, 0, message, 0, 60, width=120, align=watchgl.ALIGNMENT_CENTER, font=fonts.sans24)
        self._yes.draw()
        self._no.draw()
        self._message = message
        mute(False)

        self.active = True

    def update(self, _redraw=False):
        if _redraw or _wgl.redraw_widgets:
            self.draw(self._message)


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
