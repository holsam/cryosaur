'''
CRYOSAUR: utility functions for printing cryosaur icon/title to terminal
'''

# -- Import external dependencies
from rich import print

# -- DINO_ICON: define constant for header containing dinosaur icon and cryosaur text
DINO_ICON = '''
             __
            / _)    
     .-^^^-/ /    ▛▘▛▘▌▌▛▌▛▘▀▌▌▌▛▘
  __/       /     ▙▖▌ ▙▌▙▌▄▌█▌▙▌▌ 
 <__.|_|-|_|          ▄▌
'''

# -- print_icon_header: prints DINO_ICON to terminal in bold green
def print_icon_header():
    print(f'[bold green]{DINO_ICON}[/bold green]')
