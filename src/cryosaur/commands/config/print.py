'''
CRYOSAUR: config TOML printing functions
'''

# -- Import external dependencies
import tomllib
from pathlib import Path
from rich.console import Console
from rich.text import Text
from rich.tree import Tree
from typing import Any


console = Console()

# -- build_toml_tree: returns a Tree instance from a parsed TOML file 
def build_toml_tree(data: dict[str, Any], filename: str) -> Tree:
    tree = Tree(Text(filename, style='bold'))

    # -- format_value: returns Text instance containing stylised value
    def format_value(value: Any) -> Text:
        text = Text()
        if value in [None, '', list]:
            text.append("(empty)", style="dim italic")
        else:
            text.append(repr(value), style="cyan")
        return text

    # -- add_line: returns None, but adds a given line to the Tree
    def add_line(parent: Tree, key: str, value: Any) -> None:
        line = Text()
        line.append(key, style='yellow')
        line.append(': ')
        line.append_text(format_value(value))
        parent.add(line)

    # -- add_value: returns None, but adds a value to the Tree
    def add_value(parent: Tree, key: str, value: Any) -> None:
        # Empty nested table
        if isinstance(value, dict):
            if not value:
                add_line(parent, key, None)
                return
            branch = parent.add(Text(key, style='yellow'))
            for child_key, child_value in value.items():
                add_value(branch, child_key, child_value)
            return
        # List / array
        if isinstance(value, list):
            add_list(parent, key, value)
            return
        # Scalar value
        add_line(parent, key, value)

    # -- add_list: returns None, but renders a TOML array/array of tables to Tree
    def add_list(parent: Tree, key: str, values: list[Any]) -> None:
        # Array of tables ([[table]])
        is_array_of_tables = bool(values) and all(isinstance(item, dict) for item in values)
        if is_array_of_tables:
            branch = parent.add(Text(key, style='yellow'))
            for item in values:
                item_branch = branch.add(Text("[item]", style='dim'))
                if not item:
                    item_branch.add(Text('(empty)', style='dim italic'))
                    continue
                for child_key, child_value in item.items():
                    add_value(item_branch, child_key, child_value)
            return
        # Ordinary TOML array
        line = Text()
        line.append(key, style='yellow')
        line.append(": ", style='white')
        if values:
            line.append(repr(values), style='cyan')
        else:
            line.append('(empty)', style='dim italic')
        parent.add(line)

    for key, value in data.items():
        add_value(tree, key, value)
    return tree

# -- print_toml: print parsed TOML data as a tree
def print_toml(path: Path) -> None:
    with path.open('rb') as f:
        data = tomllib.load(f)
    console = Console()
    console.print()
    console.print(build_toml_tree(data, path.name))
    console.print()
