from ttkbootstrap import Style

def print_theme_colors():
    """
    Parse and print all available named colors for the current ttkbootstrap theme.
    """
    style = Style()
    theme = style.theme  # Get the current theme name
    print(f"Colors for theme: {theme}")

    colors = style.colors

    # Debug structure of `colors`
    print(f"Type of colors: {type(colors)}")
    print(f"Raw colors data: {colors}\n")

    # Process as a tuple of tuples
    for color_data in colors:
        if isinstance(color_data, (list, tuple)) and len(color_data) == 2:
            color_name, hex_value = color_data
            print(f"{color_name}: {hex_value}")
        else:
            print(f"Unexpected color structure: {color_data}")

print_theme_colors()


from tkinter import Tk, Text

root = Tk()
text = Text(root)
text.pack()

colors_to_test = ["red", "Charcoal Gray", "silver", "#343A40"]

for color in colors_to_test:
    try:
        text.tag_configure(color, foreground=color)
        print(f"Successfully configured color: {color}")
    except Exception as e:
        print(f"Failed to configure color '{color}': {e}")

root.mainloop()
