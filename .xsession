#!/bin/bash
source ~/.bashrc

## Keyboard setup (adjust -layout se to your own layout)
setxkbmap -model pc105 -layout fr -variant nodeadkeys
xmodmap -e "keycode 78 = "  # Disable spurious scroll lock
xmodmap -e "keycode 108 = ISO_Level3_Shift"  # Fix AltGr
xmodmap -e "clear mod5"
xmodmap -e "add mod5 = ISO_Level3_Shift"

## Flags to disable hardware acceleration
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe

echo "$(date): .xsession started" >> ~/.xsession-log

exec i3
