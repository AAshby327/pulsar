""" Wezterm spell book.

beep boop.

"""

from spell_book_class import SpellBook

wezterm_book = SpellBook('wezterm')

@wezterm_book.installer
def install():
    """Install Wezterm"""
    print("Installing Wezterm")