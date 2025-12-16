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
from watchgl import create_wasp_image_stream, WglAppInfo, Component, DIRECTION_UP, DIRECTION_DOWN, ALIGNMENT_CENTER, ALIGNMENT_LEFT

def _draw_component_icon(com, state, wgl):
    if state['i1'] is not None:
        wgl.blit(state['i1'], 0, 0)
    if state['i2'] is not None:
        wgl.blit(state['i2'], 208-96, 0)
def _draw_component_name(com, state, wgl):
    color = wasp.system.theme('mid')
    wgl.draw_string_a(color, 0, state['n1'], 0, 2, width=120, align=ALIGNMENT_CENTER)
    wgl.draw_string_a(color, 0, state['n2'], 120, 2, width=120, align=ALIGNMENT_CENTER)

class LauncherApp():
    """An application launcher application."""
    NAME = 'Launcher'
    ICON = icons.app

    def __init__(self):
        self.appinfo = wasp.watch.wgl.create_appinfo(in_scroll=(False, DIRECTION_UP), out_scroll=(True, DIRECTION_DOWN))
        self._fallback_icon = create_wasp_image_stream(icons.app)
        self._cached_icons = []

    def background(self):
        self.appinfo.free()
        self._cached_icons = []

    def foreground(self):
        """Activate the application."""
        self._page = 0
        
        r = []
        for _ in range(2):
            s = self.appinfo.create_screen(0, [
                Component(16, 16, 208, 64, _draw_component_icon, state={'i1': None, 'i2': None, 'n1': "", 'n2': ""}),
                Component(16, 144, 208, 64, _draw_component_icon, state={'i1': None, 'i2': None, 'n1': "", 'n2': ""}),
                Component(0, 16+64, 240, 32, _draw_component_name, state={'i1': None, 'i2': None, 'n1': "", 'n2': ""}),
                Component(0, 144+64, 240, 32, _draw_component_name, state={'i1': None, 'i2': None, 'n1': "", 'n2': ""}),
                wasp.widgets.ScrollIndicator(y=16)
            ], font=fonts.sans24)
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
        if len(self._cached_icons) == 0:
            for _ in range(self._num_pages*4):
                self._cached_icons.append(None)

        page_num = self._page
        page = self._get_page(page_num)
        icon_cache_offset = page_num*4
        for i in range(4):
            if page[i] is None:
                continue
            if self._cached_icons[icon_cache_offset+i] is None:
                if hasattr(page[i], 'ICON'):
                    self._cached_icons[icon_cache_offset+i] = create_wasp_image_stream(page[i].ICON)
                else:
                    self._cached_icons[icon_cache_offset+i] = self._fallback_icon


        ci = self._cached_icons
        sc = self.appinfo.screens[page_num%2]
        c1 = sc.components[0]
        c2 = sc.components[1]
        n1 = sc.components[2]
        n2 = sc.components[3]
        scroll = sc.components[4]

        if page[0]:
            c1.set_var('i1', ci[icon_cache_offset+0])
            n1.set_var('n1', page[0].NAME)
        else:
            c1.set_var('i1', None)
            n1.set_var('n1', "")
        if page[1]:
            c1.set_var('i2', ci[icon_cache_offset+1])
            n1.set_var('n2', page[1].NAME)
        else:
            c1.set_var('i2', None)
            n1.set_var('n2', "")

        if page[2]:
            c2.set_var('i1', ci[icon_cache_offset+2])
            n2.set_var('n1', page[2].NAME)
        else:
            c2.set_var('i1', None)
            n2.set_var('n1', "")
        if page[3]:
            c2.set_var('i2', ci[icon_cache_offset+3])
            n2.set_var('n2', page[3].NAME)
        else:
            c2.set_var('i2', None)
            n2.set_var('n2', "")

        scroll.up = page_num > 0
        scroll.down = page_num < (self._num_pages-1)
