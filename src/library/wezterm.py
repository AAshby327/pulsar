""" Wezterm spell book.

beep boop.

"""

from library import SpellBook

wezterm_book = SpellBook('wezterm')

@wezterm_book.installer
def install():
    """Install Wezterm"""
    print("Installing Wezterm")