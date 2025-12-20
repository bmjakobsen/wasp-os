# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

"""Application launcher
~~~~~~~~~~~~~~~~~~~~~~~

.. figure:: res/screenshots/LauncherApp.png
    :width: 179
"""

import fonts.sans24
import wasp
import icons
from watchgl import create_wasp_image_stream, Screen, WglAppInfo, DIRECTION_UP, DIRECTION_DOWN, ALIGNMENT_CENTER, ALIGNMENT_LEFT, AutoFormatImageStream

_PAGE_COORD_MAP = (("a0", 0,0), ("a1", 120, 0), ("a2", 0, 120), ("a3", 120, 120))
_icon_stream = AutoFormatImageStream()
def _draw_function(screen:'Screen', wgl, draw_info):
    updated_groups, stripe_start, stripe_width = draw_info
    stripe_end = stripe_start + stripe_width
    scroll = screen.get_var('scroller')
    updated_already = False
    for i in range(4):
        if updated_groups&(1<<i) == 0:
            continue
        si,x,y = _PAGE_COORD_MAP[i]
        if stripe_end < y or stripe_start >= y+120:
            continue
        app = screen.get_var(si)
        if not app:
            continue
        if hasattr(app, 'ICON'):
            icon = _icon_stream
            icon.set_auto_content(app.ICON)
        else:
            icon = self.get_var('ficon')
        icon.reset()
        wgl.blit(icon, x+13, y+12)
        if i == 1:
            scroll.update(_redraw=True)
            updated_already = True
        wgl.draw_string_a(wasp.system.theme('mid'), 0, app.NAME, x, y+120-30, width=120, align=ALIGNMENT_CENTER)
    if not updated_already:
        scroll.update()


class LauncherApp():
    """An application launcher application."""
    NAME = 'Launcher'
    ICON = icons.app



    def __init__(self):
        self.appinfo = wasp.watch.wgl.create_appinfo()

    def background(self):
        self.appinfo.free()

    def foreground(self):
        """Activate the application."""
        self._page = 0
        
        r = []
        for _ in range(2):
            s = self.appinfo.create_screen(0, _draw_function, { 'a0': 0, 'a1': 1, 'a2': 2, 'a3': 3, 'scroller': 4, 'ficon': 5 }, font=fonts.sans24)
            s.set_var('scroller', wasp.widgets.ScrollIndicator(y=6))
            s.set_var('ficon', create_wasp_image_stream(icons.app))
            r.append(s)
        self.appinfo.init(r)
        self._update_page()
        wasp.system.request_event(wasp.EventMask.TOUCH |
                                  wasp.EventMask.SWIPE_UPDOWN)

    def swipe(self, event):
        i = self._page
        n = self._num_pages
        d = -1
        if event[0] == wasp.EventType.UP:
            i += 1
            if i >= n:
                i -= 1
                wasp.watch.vibrator.pulse()
                return
            d = DIRECTION_UP
        else:
            i -= 1
            if i < 0:
                wasp.system.switch(wasp.system.quick_ring[0])
                return
            d = DIRECTION_DOWN

        self._page = i
        self._update_page()
        ap = self.appinfo
        ap.switch_screen(ap.screens[i%2], direction=d)

    def touch(self, event):
        page = self._get_page(self._page)
        x = event[1]
        y = event[2]
        app = page[2 * (y // 120) + (x // 120)]
        if app:
            wasp.system.switch(app)
        else:
            wasp.watch.vibrator.pulse()

    @property
    def _num_pages(self):
        """Work out what the highest possible pages it."""
        num_apps = len(wasp.system.launcher_ring)
        return (num_apps + 3) // 4

    def _get_page(self, i):
        apps = wasp.system.launcher_ring
        page = apps[4*i: 4*(i+1)]
        while len(page) < 4:
            page.append(None)
        return page

    def _update_page(self):
        page_num = self._page
        page = self._get_page(page_num)


        sc = self.appinfo.screens[page_num%2]
        for i,si in [(0, 'a0'), (1, 'a1'), (2, 'a2'), (3, 'a3')]:
            sc.set_var(si, page[i], changed=True)

        scroll = sc.get_var('scroller')
        scroll.up = page_num > 0
        scroll.down = page_num < (self._num_pages-1)
