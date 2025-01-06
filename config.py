# config.py
DEFAULT_PORT = 6443

# Standard color palette with exact mappings
COLOR_MAPPINGS = {
    "red": "#FF0000",
    "orange": "#FFA500",
    "yellow": "#FFFF00",
    "green": "#008000",
    "blue": "#0000FF",
    "indigo": "#4B0082",
    "violet": "#EE82EE",
    "Royal Blue": "#4582ec",       # primary
    "Light Gray": "#adb5bd",       # secondary
    "Medium Sea Green": "#02b875", # success
    "Light Cyan": "#17a2b8",       # info
    "Sandy Brown": "#f0ad4e",      # warning
    "Indian Red": "#d9534f",       # danger
    "Ghost White": "#F8F9FA",      # light
    "Charcoal Gray": "#343A40",    # dark
    "White": "#ffffff",            # bg
    "Silver": "#bfbfbf",           # border
    "Gainsboro": "#e5e5e5",        # active
}


# List of available colors (replaces ROYGBIV_COLORS)
AVAILABLE_COLORS = list(COLOR_MAPPINGS.keys())