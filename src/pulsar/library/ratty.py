import typer

from pulsar.library import SpellBook

spellbook = SpellBook(
    name=__name__,
    invoke_without_command=True,
)
print(f"Running {spellbook.name} script")


@spellbook.app.command()
def version():
    return "Ratty version 123"
