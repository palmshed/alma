#!/usr/bin/env python3
"""Generate a .DS_Store file for the Alma DMG."""

import os
import sys

from ds_store import DSStore
from mac_alias import Alias


def main():
    staging_dir = os.path.realpath(sys.argv[1])
    background = os.path.join(staging_dir, "background.png")
    dsstore = os.path.join(staging_dir, ".DS_Store")

    bg_alias = Alias.for_file(background)

    icvp = {
        "backgroundType": 2,
        "backgroundImageAlias": bg_alias.to_bytes(),
        "iconSize": 128.0,
        "textSize": 12,
        "arrangeBy": "none",
        "showIconPreview": True,
        "labelOnBottom": True,
        "gridSpacing": 0,
        "gridOffsetX": 0.0,
        "gridOffsetY": 0.0,
        "viewOptionsVersion": 1,
    }

    bwsp = {
        "WindowBounds": "{{100, 200}, {680, 420}}",
        "SidebarWidth": 0,
        "ShowSidebar": False,
        "ShowStatusBar": False,
        "ShowPathbar": False,
        "ShowToolbar": False,
        "ShowTabView": False,
    }

    with DSStore.open(dsstore, "w+") as d:
        d["."]["icvp"] = icvp
        d["."]["bwsp"] = bwsp
        d["."]["vSrn"] = ("long", 1)
        d["."]["fwsw"] = ("long", 680)
        d["."]["fwvh"] = ("long", 420)
        d["Alma.app"]["Iloc"] = (170, 150)
        d["Applications"]["Iloc"] = (510, 150)


if __name__ == "__main__":
    main()
