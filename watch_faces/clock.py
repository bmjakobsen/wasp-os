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
from watchgl import create_wasp_image_stream, Screen, WglAppInfo, DIRECTION_UP, DIRECTION_DOWN, ALIGNMENT_CENTER

DIGITS_COLON = create_wasp_image_stream(digits.clock_colon)
DIGITS = (
        create_wasp_image_stream(digits.clock_0), create_wasp_image_stream(digits.clock_1), create_wasp_image_stream(digits.clock_2), create_wasp_image_stream(digits.clock_3),
        create_wasp_image_stream(digits.clock_4), create_wasp_image_stream(digits.clock_5), create_wasp_image_stream(digits.clock_6), create_wasp_image_stream(digits.clock_7),
        create_wasp_image_stream(digits.clock_8), create_wasp_image_stream(digits.clock_9)
)

MONTH = 'JanFebMarAprMayJunJulAugSepOctNovDec'



def _draw_function(screen:'Screen', wgl, draw_info):
    global DIGITS, DIGITS_COLON
    update_groups = draw_info['groups']
    stripe_start = draw_info['vstripe_start']
    stripe_end = draw_info['vstripe_end']
    hilo =  (wasp.system.theme('mid'), wasp.system.theme('bright'))
    mid = wasp.watch.drawable.lighten(hilo[0], 1)
    already_updated = False
    if update_groups&(1<<5):
        if stripe_start < (80+64) and stripe_end >= 80:
            DIGITS_COLON._set_color(3, wasp.watch.drawable.lighten(wasp.system.theme('mid'), 1))
            wgl.blit(DIGITS_COLON, 2*48, 80)
    if update_groups&(1<<6):
        bar = screen.get_var('bar')
        if stripe_start < (0+32) and stripe_end >= 0:
            bar.update()
    for si, i, x in (('h0', 0, 0), ('h1', 1, 48), ('m0', 2, 144), ('m1', 3, 192)):
        if not update_groups&(1<<i):
            continue
        if stripe_start >= (80+64) or stripe_end < 80:
            continue
        digit = DIGITS[screen.get_var(si)]
        digit._set_color(3, hilo[i%2])
        wgl.blit(digit, x, 80)
    if update_groups&(1<<4) and stripe_start < (176+48) and stripe_end >= 176:
        wgl.draw_string_a(wasp.system.theme('bright'), 0, screen.get_var('date'), 0, 176+4, width=240, align=ALIGNMENT_CENTER)


class ClockApp():
    """Simple digital clock application."""
    NAME = 'Clock'

    def __init__(self):
        self.appinfo = wasp.watch.wgl.create_appinfo()

    def foreground(self, _preview:bool=False):
        """Activate the application.

        Configure the status bar, redraw the display and request a periodic
        tick callback every second.
        """
        now = wasp.watch.rtc.get_localtime()

        s = self.appinfo.create_screen(0, _draw_function, {'h0': 0, 'h1': 1, 'm0': 2, 'm1': 3, 'date': 4, 'bar': 5, 'bar_update': 6})
        self._bar = wasp.widgets.StatusBar()
        self._bar.clock = False
        s.set_var('bar', self._bar, changed=True)
        self.appinfo.init([s])
        self._update()
        if not _preview:
            wasp.system.request_tick(1000)
    def background(self):
        self.appinfo.free()

    def _update(self):
        bar = self._bar
        bar.clock = False
        now = bar.check_time()
        if now is None:
            return
        s = self.appinfo.screens[0]
        s.set_var('h0', now[3] // 10)
        s.set_var('h1', now[3] % 10)
        s.set_var('m0', now[4] // 10)
        s.set_var('m1', now[4] % 10)
        s.set_var('date', self._day_string(now))
        s.set_var('bar_update', None, changed=True)

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
        self.foreground(_preview=True)
        self._update()
        self.background()

    def _day_string(self, now):
        """Produce a string representing the current day"""
        # Format the month as text
        month = now[1] - 1
        month = MONTH[month*3:(month+1)*3]

        return '{} {} {}'.format(now[2], month, now[0])

