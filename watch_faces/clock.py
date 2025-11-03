# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Digital clock
~~~~~~~~~~~~~~~~

Shows a time (as HH:MM) together with a battery meter and the date.

.. figure:: res/screenshots/ClockApp.png
    :width: 179
"""

import wasp

import fonts.clock as digits
from watchgl import create_wasp_image_stream, WglAppInfo, Component, DIRECTION_UP, DIRECTION_DOWN, ALIGNMENT_CENTER

DIGITS_COLON = create_wasp_image_stream(digits.clock_colon)
DIGITS = (
        create_wasp_image_stream(digits.clock_0), create_wasp_image_stream(digits.clock_1), create_wasp_image_stream(digits.clock_2), create_wasp_image_stream(digits.clock_3),
        create_wasp_image_stream(digits.clock_4), create_wasp_image_stream(digits.clock_5), create_wasp_image_stream(digits.clock_6), create_wasp_image_stream(digits.clock_7),
        create_wasp_image_stream(digits.clock_8), create_wasp_image_stream(digits.clock_9)
)

MONTH = 'JanFebMarAprMayJunJulAugSepOctNovDec'


def _draw_component_colon(com, state, wgl):
    DIGITS_COLON._set_color(3, wasp.watch.drawable.lighten(wasp.system.theme('mid'), 1))
    wgl.blit(DIGITS_COLON, 0, 0)

def _draw_component_digit(com, state, wgl):
    color_hi = state['color']
    if color_hi:
        color =  wasp.system.theme('bright')
    else:
        color =  wasp.system.theme('mid')
    digit = state['digit']
    DIGITS[digit]._set_color(3, color)
    wgl.blit(DIGITS[digit], 0, 0)

def _draw_component_date(com, state, wgl):
    wgl.draw_string_a(wasp.system.theme('bright'), 0, state['date'], 0, 4, width=240, align=ALIGNMENT_CENTER)


class ClockApp():
    """Simple digital clock application."""
    NAME = 'Clock'

    def __init__(self):
        self.appinfo = wasp.watch.wgl.create_appinfo(in_scroll=(True, DIRECTION_UP), out_scroll=(True, DIRECTION_DOWN))

    def foreground(self):
        """Activate the application.

        Configure the status bar, redraw the display and request a periodic
        tick callback every second.
        """
        now = wasp.watch.rtc.get_localtime()

        c_sb = wasp.widgets.StatusBar()
        c_sb.clock = False
        c_hdig1 = Component(  0, 80, 48, 64, _draw_component_digit, state={'color': False, 'digit': now[3] // 10})
        c_hdig2 = Component( 48, 80, 48, 64, _draw_component_digit, state={'color': True, 'digit': now[3] % 10})
        c_mdig1 = Component(144, 80, 48, 64, _draw_component_digit, state={'color': False, 'digit': now[4] // 10})
        c_mdig2 = Component(192, 80, 48, 64, _draw_component_digit, state={'color': True, 'digit': now[4] % 10})
        c_text_date = Component(0, 176, 240, 48, _draw_component_date, state={'date': self._day_string(now)})
        c_sep   = Component( 96, 80, 48, 64, _draw_component_colon)
        self.components = [c_sb, c_hdig1, c_hdig2, c_mdig1, c_mdig2, c_sep, c_text_date]

        s = self.appinfo.create_screen(0, self.components)
        self.appinfo.init([s])
        wasp.system.request_tick(1000)
    def background(self):
        self.appinfo.free()

    def _update(self):
        now = self.components[0].update()
        if now is None:
            return
        
        self.components[1].set_var('digit', now[3] // 10)
        self.components[2].set_var('digit', now[3] % 10)
        self.components[3].set_var('digit', now[4] // 10)
        self.components[4].set_var('digit', now[4] % 10)
        self.components[5].set_var('date', self._day_string(now))

    def sleep(self):
        """Prepare to enter the low power mode.

        :returns: True, which tells the system manager not to automatically
                  switch to the default application before sleeping.
        """
        return True

    def wake(self):
        """Return from low power mode.

        Time will have changes whilst we have been asleep so we must
        udpate the display (but there is no need for a full redraw because
        the display RAM is preserved during a sleep.
        """
        self._update()

    def tick(self, ticks):
        """Periodic callback to update the display."""
        self._update()

    def preview(self):
        """Provide a preview for the watch face selection."""
        wasp.system.bar.clock = False
        self._update()

    def _day_string(self, now):
        """Produce a string representing the current day"""
        # Format the month as text
        month = now[1] - 1
        month = MONTH[month*3:(month+1)*3]

        return '{} {} {}'.format(now[2], month, now[0])

