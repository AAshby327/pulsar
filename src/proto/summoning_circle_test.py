import time

from spell_book_class import SpellBook
from summoning_circle import install_spell_books, summon_goblin_worker

sb1 = SpellBook('neovim')
sb2 = SpellBook('wezterm')
sb3 = SpellBook('fzf')
sb4 = SpellBook('lazygit', dependencies=[sb3, sb1])

def neovim_installer():
    goblin = summon_goblin_worker(sb1)

    goblin.status = 0.0

    for i in range(15):
        goblin.status = ((i+1) / 15)
        if i == 3:
            goblin.logger.info("Downloading neovim...")
        elif i == 8:
            goblin.logger.info("Extracting archive...")
        elif i == 12:
            goblin.logger.info("Installing binaries...")

        time.sleep(0.5)


def wezterm_installer():
    goblin = summon_goblin_worker(sb2)
    goblin.status = 0.0
    goblin.bar_style = 'magenta'

    for i in range(31):
        goblin.status = ((i+1) / 31)
        if i == 3:
            goblin.logger.info("Downloading wezterm...")
        elif i == 4:
            goblin.logger.info("Extracting archive...")
        elif i == 13:
            goblin.logger.info("Installing binaries...")

        time.sleep(0.2)


def fzf_installer():
    goblin = summon_goblin_worker(sb3)
    goblin.status = 0.0
    goblin.bar_style = 'cyan'

    for i in range(10):
        goblin.status = ((i+1 )/ 10)
        if i == 2:
            goblin.logger.info("Downloading fzf...")
        elif i == 5:
            goblin.logger.info("Extracting archive...")
        elif i == 8:
            goblin.logger.info("Installing binaries...")

        time.sleep(0.8)


def lazygit_installer():
    goblin = summon_goblin_worker(sb4)
    goblin.status = 0.0
    goblin.bar_style = 'yellow'

    goblin.wait_for_spell_books(sb4.dependencies)

    for i in range(20):
        goblin.status = ((i+1 )/ 20)
        if i == 3:
            goblin.logger.info("Downloading lazygit...")
        elif i == 7:
            goblin.logger.info("Extracting archive...")
        elif i == 10:
            goblin.logger.info("Checking dependencies...")
        elif i == 15:
            goblin.logger.info("Installing binaries...")

        time.sleep(0.15)

sb1._installer_spell = neovim_installer
sb2._installer_spell = wezterm_installer
sb3._installer_spell = fzf_installer
sb4._installer_spell = lazygit_installer

install_spell_books([sb1, sb2, sb3, sb4], False, False, 2)