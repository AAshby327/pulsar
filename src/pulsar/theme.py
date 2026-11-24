from rich.theme import Theme

# Tokyo Night theme

RED     = '#f7768e'
ORANGE  = '#ff9e64'
YELLOW  = '#e0af68'
CREME   = '#cfc9c2'
GREEN   = '#9ece6a'
AQUA    = '#73dacb'
LIME    = '#b4f9f8'
CYAN    = '#73dacb'
SKY     = '#7dcfff'
BLUE    = '#7aa2f7'
PURPLE  = '#bb9af7'

FOREGROUND_1    = '#c0caf5'
FOREGROUND_2    = '#a9b1d6'
FOREGROUND_3    = '#9aa5ce'

BACKGROUND_1    = '#565f89'
BACKGROUND_2    = '#414868'
BACKGROUND_3    = '#1a1b26'

tokyo_night = Theme({
    'red': RED,
    'orange': ORANGE,
    'yellow': YELLOW,
    'creme': CREME,
    'green': GREEN,
    'aqua': AQUA,
    'lime': LIME,
    'cyan': CYAN,
    'sky': SKY,
    'blue': BLUE,
    'purple': PURPLE,
    'magenta': PURPLE,

    'white': FOREGROUND_1,
    'black': BACKGROUND_3,

    'repr.number': ORANGE,
    'repr.number_complex': ORANGE,
})