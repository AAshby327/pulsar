import typer

from pulsar.library import SpellBook

book = SpellBook(
    name=__name__,
    invoke_without_command=True,
)
print("Running ratty script")


@book.app.command()
def version():
    return "Ratty version 123"
