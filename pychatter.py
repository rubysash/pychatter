import re
import webbrowser
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import sqlite3
import threading
import queue
import socket
import datetime
import time

import ttkbootstrap as tb
import pygame


# Import the config file
from config import AVAILABLE_COLORS, COLOR_MAPPINGS, DEFAULT_PORT


# Global variables for message history
message_history = []
history_index = -1  # Tracks the position in the history

# Global variable to hold the server socket
server_socket_instance = None
server_thread_stop_event = threading.Event()  # Event to signal the server thread to stop

# for sound
last_sound_time = 0  # Tracks the last time a sound was played
sound_effects = {}

# Log Polling
server_active = False
latest_log_timestamp = None

# Colors
def fetch_connection_colors():
    """
    Fetch the connection colors from the database.
    Returns a dictionary mapping 'ip:port' to the assigned color.
    """
    conn = sqlite3.connect("chat_app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ip, port, color FROM connections")
    connection_colors = {f"{ip}:{port}": color for ip, port, color in cursor.fetchall()}
    conn.close()
    return connection_colors

def assign_color(item):
    """
    Assign a color from available colors based on the hash of the item.
    """
    index = hash(item) % len(AVAILABLE_COLORS)
    return AVAILABLE_COLORS[index]

def setup_color_menu(connections_listbox, log_text, current_log_label, custom_dropdown):
    """
    Set up a right-click context menu on the connections listbox for selecting colors.
    Uses centralized color configuration from config.py.
    """
    # Create the color menu
    color_menu = tk.Menu(connections_listbox, tearoff=0)
    for color in AVAILABLE_COLORS:
        color_menu.add_command(
            label=color,
            command=lambda c=color: assign_color_to_selected(c, connections_listbox, log_text, current_log_label, custom_dropdown)
        )

    # Bind right-click to show the color menu
    connections_listbox.bind("<Button-3>", lambda e: show_color_menu(e, connections_listbox, color_menu))

def show_color_menu(event, connections_listbox, menu):
    """
    Display the context menu at the cursor position.
    """
    # Clear and select the current item
    selection = connections_listbox.curselection()
    if selection:
        connections_listbox.selection_clear(0, "end")
        connections_listbox.selection_set(selection[0])

        # Post the menu at the cursor position
        try:
            menu.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"Error displaying menu: {e}")
    else:
        print("No selection to assign color.")  # Debugging message for no selection

    # Ensure menu unposts after selection
    menu.bind("<FocusOut>", lambda e: menu.unpost())

def assign_color_to_selected(color, connections_listbox, log_text, current_log_label, custom_dropdown=None):
    """
    Assign the selected color to the selected connection and refresh views immediately.
    """
    selection = connections_listbox.curselection()
    if selection:
        selected_index = selection[0]  # Get the current selection index
        selected_connection = connections_listbox.get(selected_index)
        ip, port = selected_connection.split(":")
        save_connection(ip, int(port), color)  # Save the color to the database

        # Refresh the listbox and dropdown menu
        refresh_connections(connections_listbox, custom_dropdown)

        # Update the log text with new color settings
        connection_colors = fetch_connection_colors()
        initialize_color_tags(log_text)
        fetch_and_display_logs(log_text, connection_colors, selected_connection)

        # Reselect the previously selected item in the listbox
        connections_listbox.selection_set(selected_index)
    else:
        print("No connection selected to assign color.")  # Debugging message for no selection

def initialize_color_tags(log_text):
    """
    Predefine color tags in the Text widget for all colors using hex codes.
    Ensures compatibility with ttkbootstrap themes and tkinter.
    """
    for color_name, color_hex in COLOR_MAPPINGS.items():
        try:
            log_text.tag_configure(color_hex, foreground=color_hex)  # Use hex code directly
        except tk.TclError as e:
            print(f"Error configuring color tag for hex '{color_hex}': {e}")

    # Ensure "white bold" tag for outgoing messages
    if "white bold" not in log_text.tag_names():
        log_text.tag_configure("white bold", foreground="#FFFFFF", font="TkDefaultFont 10 bold")


# SQLite Database Setup
def init_db():
    conn = sqlite3.connect("chat_app.db")
    cursor = conn.cursor()

    # Check if the connections table exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS connections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT,
        port INTEGER,
        color TEXT,
        UNIQUE(ip, port)
    )
    """)

    # Ensure the messages table exists with its current schema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        ip TEXT,
        port INTEGER,
        message TEXT,
        delivery_status TEXT DEFAULT 'success'
    )
    """)

    conn.commit()
    conn.close()

# only used if we need to update, kept for knowledge
def update_db_schema():
    conn = sqlite3.connect("chat_app.db")
    cursor = conn.cursor()

    # Check if the delivery_status column exists, and add it if not
    cursor.execute("PRAGMA table_info(messages)")
    columns = cursor.fetchall()
    if not any(column[1] == "delivery_status" for column in columns):
        cursor.execute("ALTER TABLE messages ADD COLUMN delivery_status TEXT DEFAULT 'success'")
        print("Added delivery_status column to messages table.")

    conn.commit()
    conn.close()



# Client/Server Related
def send_message(ip, port, message, log_callback):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((ip, port))
            client_socket.sendall(message.encode())
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_callback(f"[{timestamp}] {ip}:{port}: {message}")
            save_message(timestamp, ip, port, message, delivery_status="success")
    except Exception as e:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_callback(f"[{timestamp}] Failed to send message to {ip}:{port}. Error: {e}")
        save_message(timestamp, ip, port, message, delivery_status="failure")
        messagebox.showerror("Error", f"Failed to send message: {e}")

def start_server_with_default(server_port_entry, message_queue, log_callback):
    """
    Start the server and enable the polling mechanism.
    """
    global server_active
    port = server_port_entry.get()
    try:
        port = int(port) if port else DEFAULT_PORT
        if server_active:
            log_callback("Server is already running.")
            return  # Prevent starting a new server instance
        start_server(port, message_queue, log_callback)
        server_active = True  # Set the flag to indicate the server is running
        log_callback("Server started successfully.")
    except ValueError:
        messagebox.showerror("Error", "Port must be a valid number")
    except Exception as e:
        log_callback(f"Error starting server: {e}")

def start_server(listen_port, message_queue, log_callback):
    """
    Starts a server to listen on a given port for incoming connections.
    Ensures no duplicate server starts and handles client connections in separate threads.
    
    :param listen_port: Port number for the server to listen on.
    :param message_queue: Queue for passing received messages.
    :param log_callback: Function to log messages or errors.
    """
    global server_socket_instance, server_thread_stop_event

    def server_thread():
        """
        The main server loop that listens for incoming connections
        and starts a new thread to handle each client.
        """
        try:
            # Create and configure the server socket
            server_socket_instance = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket_instance.bind(("0.0.0.0", listen_port))
            server_socket_instance.listen(10)  # Allow up to 10 pending connections
            log_callback(f"Server listening on port {listen_port}...")

            while not server_thread_stop_event.is_set():
                try:
                    server_socket_instance.settimeout(1.0)  # Timeout for accept()
                    conn, addr = server_socket_instance.accept()  # Wait for a connection
                    log_callback(f"New connection from {addr[0]}:{addr[1]}")
                    # Start a new thread to handle the client
                    threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
                except socket.timeout:
                    continue  # Allow the loop to check for `server_thread_stop_event`
                except Exception as e:
                    log_callback(f"Error accepting client: {e}")
        except Exception as e:
            log_callback(f"Fatal server error: {e}")
        finally:
            # Ensure the server socket is properly closed
            if server_socket_instance:
                server_socket_instance.close()
                server_socket_instance = None
            log_callback("Server thread exiting.")

    def handle_client(conn, addr):
        """
        Handles communication with a single client.
        Receives data, logs the message, and saves it to the database.
        """
        try:
            data = conn.recv(1024).decode()
            if data:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_callback(f"[{timestamp}] {addr[0]}:{addr[1]}: {data}")
                message_queue.put((timestamp, addr[0], addr[1], data))
                save_message(timestamp, addr[0], addr[1], data)
        except Exception as e:
            log_callback(f"Error handling client {addr}: {e}")
        finally:
            conn.close()

    # Ensure no duplicate server starts
    if server_active:
        log_callback("Server is already active.")
        return

    # Clear the stop event and start the server thread
    server_thread_stop_event.clear()
    threading.Thread(target=server_thread, daemon=True).start()
    log_callback("Server thread started.")

def stop_server(log_callback):
    global server_thread_stop_event, server_socket_instance
    server_thread_stop_event.set()
    if server_socket_instance:
        try:
            server_socket_instance.close()
        except Exception as e:
            log_callback(f"Error closing server socket: {e}")
        finally:
            server_socket_instance = None
    log_callback("Server stopping...")

def toggle_server_status(start_button, server_port_entry, message_queue, log_callback, connections_listbox, log_text, current_log_label, freeze_logs):
    global server_active

    if server_active:  # Stop the server
        stop_server(log_callback)
        start_button.config(text="Start Server", style="ServerStopped.TButton")
        server_active = False
    else:  # Start the server
        start_server_with_default(server_port_entry, message_queue, log_callback)
        if server_active:  # Server started successfully
            start_button.config(text="Server Running", style="ServerRunning.TButton")
            poll_logs(connections_listbox, log_text, current_log_label, freeze_logs)



# Database Save Functions
def save_message(timestamp, ip, port, message, delivery_status="success"):
    conn = sqlite3.connect("chat_app.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (timestamp, ip, port, message, delivery_status) VALUES (?, ?, ?, ?, ?)",
        (timestamp, ip, port, message, delivery_status)
    )
    conn.commit()
    conn.close()

def get_connections():
    conn = sqlite3.connect("chat_app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ip, port, color FROM connections")
    connections = cursor.fetchall()
    conn.close()
    return connections

def save_connection(ip, port, color=None):
    """
    Save or update a connection's details in the database.
    Ensures each combination of ip:port is unique, and updates the color if necessary.
    """
    if not color.startswith("#"):
        color = COLOR_MAPPINGS.get(color, "#FFFFFF")  # Fallback to white if invalid
    conn = sqlite3.connect("chat_app.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO connections (ip, port, color) VALUES (?, ?, ?)", (ip, port, color))
        cursor.execute("UPDATE connections SET color = ? WHERE ip = ? AND port = ?", (color, ip, port))
        conn.commit()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to save connection: {e}")
    finally:
        conn.close()


# Log Helpers/Modifiers

# Simplified Flashing Functions will not hook into windows orange icon on taskbar
def flash_title(app, state=True):
    """
    Blink the application title bar text to alert the user.
    """
    if app.focus_get():  # Stop flashing if the app regains focus
        app.title("Chat Application")
        return
    app.title("New Message!" if state else "Chat Application")
    app.after(500, lambda: flash_title(app, not state))

def flash_taskbar(hwnd, count=5):
    """
    Flash the taskbar icon for the application window.
    
    :param hwnd: The window handle of the application.
    :param count: Number of times to flash (0 for infinite until the user interacts).
    """
    if hwnd:
        FLASHW_ALL = 0x00000003  # Flash both the window caption and taskbar button
        FLASHW_TIMERNOFG = 0x0000000C  # Flash until the window comes to the foreground
        flags = FLASHW_ALL | FLASHW_TIMERNOFG

        flash_info = FLASHWINFO(
            cbSize=ctypes.sizeof(FLASHWINFO),
            hwnd=hwnd,
            dwFlags=flags,
            uCount=count,
            dwTimeout=0,
        )
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(flash_info))
    else:
        print("Invalid HWND provided for taskbar flashing.")

def stop_flashing_taskbar(app_name):
    """
    Stop flashing the taskbar icon for the application window.
    
    :param app_name: The title of the application window.
    """
    hwnd = win32gui.FindWindow(None, app_name)
    if hwnd:
        FLASHW_STOP = 0x00000000  # Stop flashing
        flash_info = FLASHWINFO(
            cbSize=ctypes.sizeof(FLASHWINFO),
            hwnd=hwnd,
            dwFlags=FLASHW_STOP,
            uCount=0,
            dwTimeout=0,
        )
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(flash_info))

def start_flashing_title():
    """
    Start flashing the window title to alert the user of new messages.
    """
    if not app.focus_get():
        flash_title(app)

def stop_flashing_on_focus(event=None):
    """
    Stop flashing and reset the title when the app regains focus.
    """
    app.title("Chat Application")  # Reset title to default

def make_links_clickable(log_text):
    """
    Identify URLs in the log_text widget and make them clickable.
    """
    url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    
    def open_url(event):
        """
        Open the clicked URL in the default web browser.
        """
        start_index = log_text.index("@%s,%s linestart" % (event.x, event.y))
        end_index = log_text.index("@%s,%s lineend" % (event.x, event.y))
        line_text = log_text.get(start_index, end_index)
        match = re.search(url_pattern, line_text)
        if match:
            webbrowser.open(match.group(0))

    # Configure hyperlink tag
    if "hyperlink" not in log_text.tag_names():
        log_text.tag_configure("hyperlink", font="TkDefaultFont 10 bold", underline=1)
    
    # Remove all existing bindings and reapply
    log_text.tag_unbind("hyperlink", "<Button-1>")
    log_text.tag_bind("hyperlink", "<Button-1>", open_url)

    # Search for URLs in the log_text
    log_text.tag_remove("hyperlink", "1.0", "end")
    start = "1.0"
    while True:
        match = re.search(url_pattern, log_text.get(start, "end"))
        if not match:
            break
        start_index = f"{start}+{match.start()}c"
        end_index = f"{start}+{match.end()}c"
        log_text.tag_add("hyperlink", start_index, end_index)
        start = end_index

def log_callback(log_text, message):
    """
    Log callback with distinct sounds for sent and received messages.
    No sounds for server messages or errors.
    """
    log_text["state"] = "normal"
    log_text.insert("end", message + "\n")
    log_text["state"] = "disabled"
    log_text.see("end")
    
    # Skip sounds for server messages and errors
    if message.startswith("Server") or "Failed to send message" in message:
        pass
    # Check if this is an actual message with timestamp
    elif "[" in message and "]" in message:
        # Check if it's a sent message (they end with the actual message text)
        # or a received message (they end with the IP:port)
        is_sent = not bool(re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$', message))
        play_notification('sent' if is_sent else 'received')
    
    start_flashing_title()



def clear_logs(connections_listbox, log_text, current_log_label):
    selection = connections_listbox.curselection()
    if not selection:
        messagebox.showerror("Error", "No connection selected to clear logs.")
        return

    ip_port = connections_listbox.get(selection[0])
    ip, _ = ip_port.split(":")  # Extract only the IP
    response = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete all logs for {ip}?")
    if response:
        # Delete all logs for the selected IP, regardless of the port
        conn = sqlite3.connect("chat_app.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE ip = ?", (ip,))
        conn.commit()
        conn.close()

        # Clear the log display area
        log_text["state"] = "normal"
        log_text.delete("1.0", "end")
        log_text["state"] = "disabled"

        # Update the current log label
        current_log_label.config(text="Logs for: None")
        messagebox.showinfo("Logs Deleted", f"All logs for {ip} have been deleted.")

def poll_logs(connections_listbox, log_text, current_log_label, freeze_logs):
    """
    Periodically check for new logs and update the log_text widget based on the selected filter.
    Only displays the latest 25 logs.
    Respects the freeze_logs toggle to pause polling if needed.
    """
    global latest_log_timestamp, server_active

    # Skip polling if the server is not active or logs are frozen
    if not server_active or freeze_logs.get():
        log_text.after(1000, lambda: poll_logs(connections_listbox, log_text, current_log_label, freeze_logs))
        return

    connection_colors = fetch_connection_colors()  # Fetch connection colors
    initialize_color_tags(log_text)  # Initialize color tags

    selection = connections_listbox.curselection()
    if not selection:
        log_text.after(1000, lambda: poll_logs(connections_listbox, log_text, current_log_label, freeze_logs))
        return

    selected_ip_port = connections_listbox.get(selection[0])
    fetch_and_display_logs(log_text, connection_colors, selected_ip_port)

    log_text.after(1000, lambda: poll_logs(connections_listbox, log_text, current_log_label, freeze_logs))

def fetch_and_display_logs(
    log_text,
    connection_colors,
    selected_ip_port="All Messages",
    limit=100  # Increased default limit
):
    """
    Fetch logs from the database and display them in the log_text widget.
    Displays both outgoing and incoming messages for the selected connection.
    Messages are shown oldest to newest, with abbreviated IPs.
    """
    # Tag configuration remains the same...

    conn = sqlite3.connect("chat_app.db")
    cursor = conn.cursor()

    if selected_ip_port == "All Messages":
        # First, get total count
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]
        
        # Then get the messages with a larger limit
        query = """
            SELECT timestamp, ip, port, message, delivery_status
            FROM messages
            ORDER BY timestamp DESC
            LIMIT ?
        """
        cursor.execute(query, (limit,))
        logs = cursor.fetchall()
        logs = sorted(logs, key=lambda x: x[0])  # Sort chronologically
    else:
        ip, port = selected_ip_port.split(":")
        port = int(port)

        # Get messages for specific connection with a larger limit
        outgoing_query = """
            SELECT timestamp, ip, port, message, delivery_status
            FROM messages
            WHERE ip = ? AND port = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        cursor.execute(outgoing_query, (ip, port, limit))
        outgoing_logs = cursor.fetchall()

        incoming_query = """
            SELECT timestamp, ip, port, message, delivery_status
            FROM messages
            WHERE ip = ? AND port != ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        cursor.execute(incoming_query, (ip, port, limit))
        incoming_logs = cursor.fetchall()

        # Combine and sort chronologically
        logs = sorted(outgoing_logs + incoming_logs, key=lambda x: x[0])

    conn.close()

    log_text["state"] = "normal"
    log_text.delete("1.0", "end")

    server_ports = {int(key.split(":")[1]) for key in connection_colors}
    base_ip_colors = {key.split(":")[0]: color for key, color in connection_colors.items()}

    for timestamp, msg_ip, msg_port, message, delivery_status in logs:
        msg_port = int(msg_port)
        connection_key = f"{msg_ip}:{msg_port}"
        color = connection_colors.get(connection_key, None) or base_ip_colors.get(msg_ip, "white")
        resolved_color = COLOR_MAPPINGS.get(color, color)

        if resolved_color not in log_text.tag_names():
            log_text.tag_configure(resolved_color, foreground=resolved_color)

        timestamp_line = f"{timestamp} {msg_ip}: "
        log_text.insert("end", timestamp_line, resolved_color)

        status_display = f" (FAILED)" if delivery_status == "failure" else ""
        is_outgoing = msg_port in server_ports

        if is_outgoing:
            log_text.insert("end", f"{message}{status_display}\n", "white bold")
        else:
            log_text.insert("end", f"{message}{status_display}\n", resolved_color)

    make_links_clickable(log_text)

    log_text["state"] = "disabled"
    log_text.see("end")


# Sound System
def play_background_music(music_file, volume=0.5, loop=True):
    """
    Play background music (separate from sound effects).
    
    :param music_file: Path to music file
    :param volume: Volume level (0.0 to 1.0)
    :param loop: Whether to loop the music
    """
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1 if loop else 0)
    except Exception as e:
        print(f"Error playing background music: {e}")

def stop_background_music():
    """Stop any playing background music."""
    if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()

def set_volume(volume, channel=None):
    """
    Set volume for specific channel or all channels.
    
    :param volume: Volume level (0.0 to 1.0)
    :param channel: Channel number or None for all channels
    """
    if pygame.mixer.get_init():
        if channel is None:
            # Set volume for all channels
            for i in range(pygame.mixer.get_num_channels()):
                pygame.mixer.Channel(i).set_volume(volume)
        else:
            # Set volume for specific channel
            pygame.mixer.Channel(channel).set_volume(volume)

def init_sound():
    """
    Initialize the pygame mixer with optimal settings and load sent/received sounds.
    Returns True if initialization successful, False otherwise.
    """
    global sound_effects  # Explicitly use the global dictionary
    try:
        pygame.mixer.init(
            frequency=44100,    # Standard CD quality
            size=-16,          # 16-bit sound
            channels=2,        # Stereo
            buffer=512        # Smaller buffer for better responsiveness
        )
        
        # Set up multiple channels for different sound types
        pygame.mixer.set_num_channels(8)  # Allow up to 8 simultaneous sounds
        
        # Pre-load both notification sounds
        try:
            sound_effects['sent'] = pygame.mixer.Sound("sent.wav")
            sound_effects['received'] = pygame.mixer.Sound("received.wav")
            
            # Set their volumes (can be adjusted as needed)
            sound_effects['sent'].set_volume(0.3)
            sound_effects['received'].set_volume(0.3)
            
            print("Notification sounds loaded successfully")
        except Exception as e:
            print(f"Error loading notification sounds: {e}")
            return False
            
        return True
    except Exception as e:
        print(f"Error initializing sound system: {e}")
        return False

def play_notification(sound_type='received', cooldown=0.1):
    """
    Play either sent or received notification sound.
    
    :param sound_type: Type of sound to play ('sent' or 'received')
    :param cooldown: Minimum time between sounds
    """
    global last_sound_time, sound_effects
    now = time.time()
    
    if now - last_sound_time < cooldown:
        return
    
    try:
        if pygame.mixer.get_init() and sound_type in sound_effects:
            sound_effects[sound_type].play()
            last_sound_time = now
    except Exception as e:
        print(f"Error playing {sound_type} sound: {e}")

def cleanup_sound():
    """Clean up sound system resources."""
    global sound_effects
    try:
        # Clear the sound effects dictionary
        sound_effects.clear()
        pygame.mixer.quit()
        print("Sound system cleaned up successfully")
    except Exception as e:
        print(f"Error cleaning up sound system: {e}")

# Message History
def send_and_clear(ip_dropdown, message_entry, log_text):
    global history_index
    message = message_entry.get()
    if not message.strip():  # Skip sending empty messages
        return

    # Validate and parse dropdown value
    dropdown_value = ip_dropdown.get()
    try:
        ip, port = dropdown_value.split(":")
        port = int(port)
    except ValueError:
        messagebox.showerror("Error", "Invalid connection selected.")
        return

    # Send the message
    send_message(
        ip, port, message,
        lambda msg: log_callback(log_text, msg)
    )
    # Add to history and reset history index
    message_history.append(message)
    history_index = len(message_history)  # Reset to allow new input

    # Clear the entry and reset focus
    message_entry.delete(0, tk.END)
    message_entry.focus()

def navigate_history(event, message_entry):
    global history_index
    if not message_history:
        return  # No history to navigate

    if event.keysym == "Up":
        history_index = max(0, history_index - 1)
    elif event.keysym == "Down":
        history_index = min(len(message_history), history_index + 1)

    # Update the message entry if within bounds
    if 0 <= history_index < len(message_history):
        message_entry.delete(0, tk.END)
        message_entry.insert(0, message_history[history_index])
    elif history_index == len(message_history):  # Reset for new input
        message_entry.delete(0, tk.END)



# Connection Management
def add_connection(ip_entry, port_entry, connections_listbox, ip_dropdown):
    ip, port = ip_entry.get(), port_entry.get()
    if ip and port:
        try:
            port = int(port)
            # Assign a default color if none is provided
            default_color = assign_color(f"{ip}:{port}")
            save_connection(ip, port, default_color)
            refresh_connections(connections_listbox, ip_dropdown)
            messagebox.showinfo("Success", f"Connection {ip}:{port} added successfully.")
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Error", f"Failed to add connection: {e}")

def create_custom_dropdown(parent, connections):
    """
    Create a custom dropdown menu with colored items for saved connections.
    """
    selected_connection = tk.StringVar(parent)  # Variable to track the selected item
    default_text = "Select Connection"
    selected_connection.set(default_text)  # Default value

    # Ensure there is at least one option (the default placeholder)
    if not connections:
        connections = [(default_text, "#000000")]  # Add a default option with black text color

    # Create the OptionMenu widget
    dropdown_menu = tk.OptionMenu(parent, selected_connection, *[conn[0] for conn in connections])
    dropdown_menu["menu"].delete(0, "end")  # Clear default menu items

    # Populate dropdown with colored connections or a default placeholder
    for conn, color in connections:
        dropdown_menu["menu"].add_command(
            label=conn,
            command=lambda c=conn: selected_connection.set(c),  # Update the StringVar directly
            foreground=color if color.startswith("#") else "#000000"  # Default to black if invalid
        )

    return dropdown_menu, selected_connection

def on_connection_select(event, connections_listbox, log_text, current_log_label, custom_dropdown_var=None):
    """
    Handles the selection of a connection or "All Messages" filter.
    Updates the logs display based on the selected connection or displays all logs if "All Messages" is selected.
    Updates the custom dropdown if provided.
    """
    initialize_color_tags(log_text)  # Ensure tags are initialized
    connection_colors = fetch_connection_colors()  # Fetch connection colors

    selection = connections_listbox.curselection()
    if selection:
        selected_ip_port = connections_listbox.get(selection[0])

        if selected_ip_port == "All Messages":
            current_log_label.config(text="Logs for: All Messages")
        else:
            ip, port = selected_ip_port.split(":")
            current_log_label.config(text=f"Logs for: {ip}:{port}")

        # Update the custom dropdown variable if provided
        if custom_dropdown_var:
            custom_dropdown_var.set(selected_ip_port)  # Update the StringVar directly

        # Fetch and display logs
        fetch_and_display_logs(log_text, connection_colors, selected_ip_port)

def refresh_connections(connections_listbox, custom_dropdown=None, selected_connection=None):
    """
    Refresh the connections listbox and update the custom dropdown with saved connections and colors.
    """
    # Fetch all connections with their colors
    connections = [(f"{ip}:{port}", color) for ip, port, color in get_connections()]
    connections_listbox.delete(0, "end")

    # Add "All Messages" option
    connections_listbox.insert("end", "All Messages")
    connections_listbox.itemconfig(0, {"fg": "#FFFFFF"})  # Default white for "All Messages"

    # Populate the listbox with connections and their assigned colors
    for idx, (conn, color) in enumerate(connections, start=1):
        connections_listbox.insert("end", conn)
        if color.startswith("#"):  # Ensure the color is a valid hex
            connections_listbox.itemconfig(idx, {"fg": color})

    # Update the custom dropdown if provided
    if custom_dropdown:
        menu = custom_dropdown["menu"]
        menu.delete(0, "end")  # Clear previous menu items
        for conn, color in connections:
            menu.add_command(
                label=conn,
                command=lambda c=conn: selected_connection.set(c),  # Update the StringVar directly
                foreground=color if color.startswith("#") else "#000000"
            )

def bind_log_click(log_text, selected_connection, message_entry):
    """
    Bind click events on the log text area to populate the server:port in the dropdown
    and focus the message entry field.
    
    :param log_text: The text widget containing logs
    :param selected_connection: StringVar linked to the dropdown
    :param message_entry: The entry widget for new messages
    """
    def on_log_click(event):
        try:
            # Get clicked position and line content
            index = log_text.index(f"@{event.x},{event.y}")
            line_start = log_text.index(f"{index} linestart")
            line_end = log_text.index(f"{index} lineend")
            line_text = log_text.get(line_start, line_end).strip()
            
            # Look for IP address in the line
            ip_match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", line_text)
            if ip_match:
                clicked_ip = ip_match.group(1)
                
                # Query database for the IP
                conn = sqlite3.connect("chat_app.db")
                cursor = conn.cursor()
                cursor.execute("SELECT ip, port FROM connections WHERE ip = ? LIMIT 1", (clicked_ip,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    ip, port = result
                    selected_connection.set(f"{ip}:{port}")
                else:
                    print(f"No connection found for IP: {clicked_ip}")

            # Focus the message entry regardless of whether we found an IP
            message_entry.focus_set()
            
        except Exception as e:
            print(f"Error in log click handler: {e}")

    # Unbind any existing handler first
    log_text.unbind("<Button-1>")
    # Bind the new handler
    log_text.bind("<Button-1>", on_log_click)



# gui
def create_gui():
    app = tb.Window(themename="darkly")
    app.title("Chat Application")
    app.geometry("1000x800")

    # Define styles for the server button
    style = ttk.Style()
    style.configure("ServerStopped.TButton", background=COLOR_MAPPINGS["red"], foreground=COLOR_MAPPINGS["White"])
    style.configure("ServerRunning.TButton", background=COLOR_MAPPINGS["green"], foreground=COLOR_MAPPINGS["White"])

    # Frames
    left_frame = ttk.Frame(app)
    left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ns")
    right_frame = ttk.Frame(app)
    right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
    input_frame = ttk.Frame(app)
    input_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
    config_frame = ttk.Frame(app)
    config_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    # Configure frames for dynamic resizing
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(1, weight=1)
    right_frame.grid_rowconfigure(1, weight=1)
    right_frame.grid_columnconfigure(0, weight=1)

    # Left Panel: Connections List
    ttk.Label(left_frame, text="Connections", font=("Helvetica", 12, "bold")).grid(row=0, column=0, pady=5)
    connections_listbox = tk.Listbox(left_frame, height=30, width=30)
    connections_listbox.grid(row=1, column=0, sticky="nsew")
    connections_listbox.config(exportselection=False)

    # Make the left frame and its child components expandable
    left_frame.grid_rowconfigure(1, weight=1)
    left_frame.grid_columnconfigure(0, weight=1)

    # Right Panel: Log Area
    current_log_label = ttk.Label(right_frame, text="Logs for: None", font=("Helvetica", 12, "bold"))
    current_log_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

    log_text = tk.Text(right_frame, wrap="word", state="disabled")
    log_scroll = ttk.Scrollbar(right_frame, orient="vertical", command=log_text.yview)
    log_text["yscrollcommand"] = log_scroll.set
    log_text.grid(row=1, column=0, sticky="nsew")
    log_scroll.grid(row=1, column=1, sticky="ns")

    # Add scroll handler for historical logs
    def on_scrollbar_release(event):
        first_visible = log_text.yview()[0]
        if first_visible < 0.1:  # If we're near the top
            current_selection = connections_listbox.curselection()
            if current_selection:
                selected_ip_port = connections_listbox.get(current_selection[0])
                fetch_and_display_logs(log_text, fetch_connection_colors(), selected_ip_port, limit=500)

    # Bind the scrollbar release event
    log_scroll.bind("<ButtonRelease-1>", on_scrollbar_release)

    # Log controls
    log_control_frame = ttk.Frame(right_frame)
    log_control_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

    # Log controls
    log_control_frame = ttk.Frame(right_frame)
    log_control_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

    delete_logs_button = ttk.Button(log_control_frame, text="Delete Logs",
                                    command=lambda: clear_logs(connections_listbox, log_text, current_log_label))
    delete_logs_button.pack(side="left", padx=5)

    # Add polling toggle
    freeze_logs = tk.BooleanVar(value=False)
    freeze_logs_button = ttk.Checkbutton(
        log_control_frame,
        text="Freeze Auto Scroll",
        variable=freeze_logs
    )
    freeze_logs_button.pack(side="left", padx=5)

    # Input Bar
    message_entry = ttk.Entry(input_frame, width=80)
    message_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
    send_button = ttk.Button(input_frame, text="Send",
                              command=lambda: send_message(selected_connection.get().split(":")[0],
                                                           int(selected_connection.get().split(":")[1]),
                                                           message_entry.get(),
                                                           lambda msg: log_callback(log_text, msg)))
    send_button.grid(row=0, column=1, padx=5, pady=5)

    # Configure send button and key bindings
    send_button.configure(command=lambda: send_and_clear(selected_connection, message_entry, log_text))
    app.bind("<Return>", lambda event: send_and_clear(selected_connection, message_entry, log_text))
    message_entry.bind("<Up>", lambda event: navigate_history(event, message_entry))
    message_entry.bind("<Down>", lambda event: navigate_history(event, message_entry))

    input_frame.grid_columnconfigure(0, weight=1)

    # Config Section
    ttk.Label(config_frame, text="Saved Connections:").grid(row=0, column=0, padx=5, pady=5)
    connections = [(f"{ip}:{port}", color) for ip, port, color in get_connections()]
    custom_dropdown, selected_connection = create_custom_dropdown(config_frame, connections)
    custom_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    ttk.Label(config_frame, text="New Connection IP:").grid(row=1, column=0, padx=5, pady=5)
    ip_entry = ttk.Entry(config_frame, width=20)
    ip_entry.grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(config_frame, text="Port:").grid(row=1, column=2, padx=5, pady=5)
    port_entry = ttk.Entry(config_frame, width=10)
    port_entry.grid(row=1, column=3, padx=5, pady=5)

    add_button = ttk.Button(config_frame, text="Add Connection",
                            command=lambda: add_connection(ip_entry, port_entry, connections_listbox, custom_dropdown))
    add_button.grid(row=1, column=4, padx=5, pady=5)

    start_button = ttk.Button(
        config_frame,
        text="Start Server",
        command=lambda: toggle_server_status(
            start_button, server_port_entry, message_queue,
            lambda msg: log_callback(log_text, msg),
            connections_listbox, log_text, current_log_label, freeze_logs  # Pass freeze_logs here
        ),
        style="ServerStopped.TButton",  # Use the "stopped" style initially
    )
    start_button.grid(row=2, column=4, padx=5, pady=5)

    ttk.Label(config_frame, text="YOUR Server Port:").grid(row=2, column=0, padx=5, pady=5)
    server_port_entry = ttk.Entry(config_frame, width=10)
    server_port_entry.insert(0, DEFAULT_PORT)
    server_port_entry.grid(row=2, column=1, padx=5, pady=5)

    # Bind connection selection
    connections_listbox.bind("<<ListboxSelect>>",
                            lambda event: on_connection_select(event, connections_listbox, log_text, current_log_label, selected_connection))

    # Bind log click handler for text area
    bind_log_click(log_text, selected_connection, message_entry)

    # Re-enable the text widget for click events but keep it read-only
    log_text.config(state="normal", cursor="arrow")

    # Call setup_color_menu to bind the right-click action
    setup_color_menu(connections_listbox, log_text, current_log_label, custom_dropdown)

    # Refresh connections
    refresh_connections(connections_listbox, custom_dropdown, selected_connection)

    # Modify polling to respect freeze_logs
    def modified_poll_logs():
        poll_logs(connections_listbox, log_text, current_log_label, freeze_logs)

    log_text.after(1000, modified_poll_logs)


    # Bind the focus-in event to stop flashing
    app.bind("<FocusIn>", stop_flashing_on_focus)

    return app


# go boldly forth
if __name__ == "__main__":
    #update_db_schema()
    try:
        init_db()
        if init_sound():
            # Optional: Start background music
            # play_background_music("background.mp3", volume=0.3)
            
            message_queue = queue.Queue(maxsize=10)
            app = create_gui()
            app.mainloop()
    except Exception as e:
        print(f"Unhandled exception: {e}")
    finally:
        cleanup_sound()