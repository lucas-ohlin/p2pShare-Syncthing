import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dotenv import load_dotenv
import requests
import json
import os
import uuid

load_dotenv()

CONFIG = {
    "central_api_url": os.getenv("API_URL"),
    "central_api_key": os.getenv("API_KEY"),
    "bob_device_id": os.getenv("BOB_DEVICE_ID"),
    "bob_api_url": os.getenv("BOB_API_URL"),
    "bob_api_key": os.getenv("BOB_API_KEY"),
    "leo_device_id": os.getenv("LEO_DEVICE_ID"),
    "leo_api_url": os.getenv("LEO_API_URL"),
    "leo_api_key": os.getenv("LEO_API_KEY"),
}

discoverable_folders_vars = []
def handle_api_error(response, action="perform action"):
    try:
        response.raise_for_status()  
        return True 
    except requests.exceptions.RequestException as e:
        error_message = f"Error when trying to {action}: {e}"
        try:
            error_details = response.json().get('error', response.text)
            error_message = f"Failed to {action}. API Error: {error_details} (Status: {response.status_code})"
        except (json.JSONDecodeError, AttributeError):
            error_message = f"Failed to {action}. Error: {e} (Status: {response.status_code})"
        messagebox.showerror("API Error", error_message)
        return False 

def get_config():
    try:
        r = requests.get(f'{CONFIG["api_url"]}/system/config', headers={'X-API-Key': CONFIG["api_key"]}, timeout=10)
        if handle_api_error(r, "fetch config"):
            return r.json()
    except requests.exceptions.Timeout:
        messagebox.showerror("API Error", "Connection timed out while fetching config.")
    except Exception as e:
        messagebox.showerror("API Error", f"An unexpected error occurred fetching config: {e}")
    return None  

def post_config(config_data):
    try:
        response = requests.post(f'{CONFIG["api_url"]}/system/config', headers={'X-API-Key': CONFIG["api_key"]}, json=config_data, timeout=15)
        return handle_api_error(response, "update config")
    except requests.exceptions.Timeout:
        messagebox.showerror("API Error", "Connection timed out while updating config.")
    except Exception as e:
        messagebox.showerror("API Error", f"An unexpected error occurred updating config: {e}")
    return False 

def get_status():
    try:
        r = requests.get(f'{CONFIG["api_url"]}/system/status', headers={'X-API-Key': CONFIG["api_key"]}, timeout=10)
        if handle_api_error(r, "fetch status"):
            return r.json()
    except requests.exceptions.Timeout:
        messagebox.showerror("API Error", "Connection timed out while fetching status.")
    except Exception as e:
        messagebox.showerror("API Error", f"An unexpected error occurred fetching status: {e}")
    return None

def get_connections():
     try:
        r = requests.get(f'{CONFIG["api_url"]}/system/connections', headers={'X-API-Key': CONFIG["api_key"]}, timeout=10)
        if handle_api_error(r, "fetch connections"):
            return r.json()
     except requests.exceptions.Timeout:
        messagebox.showerror("API Error", "Connection timed out while fetching connections.")
     except Exception as e:
        messagebox.showerror("API Error", f"An unexpected error occurred fetching connections: {e}")
     return None

def refresh_data():
    global CONFIG
    seen_folder_ids = set()

    if not CONFIG["api_key"] or CONFIG["api_key"] == 'YOUR_SYNCTHING_API_KEY':
        messagebox.showwarning("Configuration Needed", "Please set the Syncthing API Key in the Settings tab.")
        return
    if not CONFIG["bob_device_id"] or not CONFIG["leo_device_id"]:
        messagebox.showwarning("Configuration Needed", "Please set Bob's and Leo's Device IDs in the Settings tab.")

    config = get_config()
    status = get_status()
    connections = get_connections()

    if config is None or status is None or connections is None:
        messagebox.showerror("Error", "Failed to load data from Syncthing. Check connection and API key.")
        return

    # Store this device id if it's not hardcoded in the config
    if not CONFIG["this_device_id"]:
        CONFIG["this_device_id"] = status.get('myID', '')
        if not CONFIG["this_device_id"]:
            messagebox.showerror("Error", "Could not determine the Device ID of this Syncthing instance.")
            return  

    this_id = CONFIG["this_device_id"]
    bob_id = CONFIG["bob_device_id"]
    leo_id = CONFIG["leo_device_id"]
    active_user = current_user.get()
    active_user_id = bob_id if active_user == "Bob" else leo_id
    other_user_id = leo_id if active_user == "Bob" else bob_id

    devices = config.get('devices', [])
    folders = config.get('folders', [])

    # Clear UI Elements
    device_listbox.delete(0, tk.END)
    my_folders_listbox.delete(0, tk.END)
    for widget in discoverable_folders_frame.winfo_children():
        widget.destroy()

    # Populate Device List
    connection_details = connections.get('connections', {})
    device_listbox.insert(tk.END, f"Server: ({this_id}) - You are viewing as: {active_user}")
    device_listbox.itemconfig(tk.END, {'bg':'lightblue'})

    for dev in devices:
        dev_id = dev['deviceID']
        if dev_id == this_id: continue  

        name = dev.get('name', 'Unknown Name')
        status_text = "✅ Connected" if connection_details.get(dev_id, {}).get('connected', False) else "❌ Disconnected"
        user_tag = ""
        if dev_id == bob_id:
            user_tag = " (Bob's Device)"
        elif dev_id == leo_id:
             user_tag = " (Leo's Device)"

        device_listbox.insert(tk.END, f"{name}{user_tag} ({dev_id}) - {status_text}")

    # Populate Folder Lists
    my_folders_list = []
    discoverable_folders_list = []

    for folder in folders:
        folder_id = folder['id']
        label = folder['label']
        path = folder['path']
        folder_devices = {d['deviceID'] for d in folder.get('devices', [])} 

        # Ignore folders not involving this instance
        if this_id not in folder_devices:
            continue

        is_shared_with_active = active_user_id in folder_devices
        is_shared_with_other = other_user_id in folder_devices

        display_text = f"{label} ({folder_id}) → {path}"

        if is_shared_with_active:
            my_folders_list.append(display_text)
        elif is_shared_with_other: 
            if folder_id not in seen_folder_ids:
                discoverable_folders_list.append({"text": display_text, "id": folder_id, "label": label})
                seen_folder_ids.add(folder_id)

    # Update My Folders Listbox
    my_folders_listbox.insert(tk.END, *my_folders_list)
    if not my_folders_list:
        my_folders_listbox.insert(tk.END, f"No folders currently shared with {active_user}.")
        my_folders_listbox.itemconfig(tk.END, {'fg':'gray'})
    else:
        discoverable_folders_vars.clear()
        for folder_info in discoverable_folders_list:
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(discoverable_folders_frame, text=folder_info["text"], variable=var)
            cb.pack(anchor="w", padx=5, pady=2)
            discoverable_folders_vars.append((var, folder_info["id"], folder_info["label"]))
    ttk.Button(discoverable_folders_frame, text="Sync Folders", command=sync_selected_folders).pack(pady=10)

def sync_selected_folders():
    selected = [(fid, label) for var, fid, label in discoverable_folders_vars if var.get()]
    if not selected:
        messagebox.showinfo("Nothing Selected", "Please select at least one folder to sync.")
        return

    for folder_id, folder_label in selected:
        sync_discovered_folder(folder_id, folder_label)

def push_folder_to_user(folder, user_api_url, user_api_key):
    try:
        r = requests.get(f"{user_api_url}/system/config", headers={'X-API-Key': user_api_key}, timeout=10)
        r.raise_for_status()
        user_config = r.json()
    except Exception as e:
        messagebox.showerror("API Error", f"Could not fetch config from remote device: {e}")
        return False

    # Check if folder already exists
    if any(f['id'] == folder['id'] for f in user_config.get('folders', [])):
        return True  

    # Add the folder to user's config
    user_config['folders'].append(folder)

    try:
        r = requests.post(f"{user_api_url}/system/config", headers={'X-API-Key': user_api_key}, json=user_config, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        messagebox.showerror("API Error", f"Failed to update remote config: {e}")
        return False

### Add current users ID to the sharing list
def sync_discovered_folder(folder_id, folder_label):
    active_user = current_user.get()
    active_user_id = CONFIG["bob_device_id"] if active_user == "Bob" else CONFIG["leo_device_id"]
    this_id = CONFIG["this_device_id"]

    user_api_url = CONFIG["bob_api_url"] if active_user == "Bob" else CONFIG["leo_api_url"]
    user_api_key = CONFIG["bob_api_key"] if active_user == "Bob" else CONFIG["leo_api_key"]

    if not active_user_id:
        messagebox.showerror("Error", f"Device ID for {active_user} is not set.")
        return

    config = get_config()
    if config is None:
        return

    folder_to_sync = next((f for f in config['folders'] if f['id'] == folder_id), None)
    if not folder_to_sync:
        messagebox.showerror("Error", f"Folder {folder_label} not found.")
        return

    if not messagebox.askyesno("Confirm Sync", f"Start syncing the folder '{folder_label}' for {active_user}?"):
        return

    # Update central config if user's device isn't already in it
    device_ids = {d['deviceID'] for d in folder_to_sync.get('devices', [])}
    if active_user_id not in device_ids:
        folder_to_sync['devices'].append({"deviceID": active_user_id})
        if not post_config(config):
            return

    # Build full folder block to send to user
    folder_for_user = {
        "id": folder_to_sync["id"],
        "label": folder_to_sync.get("label", folder_to_sync["id"]),
        "path": folder_to_sync["path"],  # You could customize path per user if needed
        "type": folder_to_sync.get("type", "sendreceive"),
        "rescanIntervalS": folder_to_sync.get("rescanIntervalS", 60),
        "fsWatcherEnabled": folder_to_sync.get("fsWatcherEnabled", True),
        "devices": [
            {"deviceID": this_id},
            {"deviceID": active_user_id}
        ]
    }

    # Send to the user's own Syncthing
    if push_folder_to_user(folder_for_user, user_api_url, user_api_key):
        messagebox.showinfo("Success", f"Folder '{folder_label}' is now syncing on {active_user}'s device.")
        refresh_data()


### Add device to config
def add_device():
    device_id = device_id_entry.get().strip()
    name = device_name_entry.get().strip()

    if not device_id or not name:
        messagebox.showwarning("Missing Info", "Device ID and Name are required.")
        return

    config = get_config()
    if config is None: return

    # Check if device already exists
    if any(d['deviceID'] == device_id for d in config.get('devices', [])):
        messagebox.showwarning("Already Exists", f"Device ID '{device_id}' already exists.")
        return

    new_device = {
        "deviceID": device_id,
        "name": name,
        "addresses": ["dynamic"],  
        "compression": "metadata",
        "introducer": False 
    }

    config['devices'].append(new_device)

    if post_config(config):
        messagebox.showinfo("Success", f"Device '{name}' added successfully. Remember to approve it on the other device if necessary.")
        refresh_data()
        device_id_entry.delete(0, tk.END)
        device_name_entry.delete(0, tk.END)

def add_folder():
    folder_id = generate_folder_id()
    label = folder_label_entry.get().strip()
    path = folder_path_entry.get().strip()
    # folder_type = sync_type_var.get() 
    folder_type="sendreceive"

    active_user = current_user.get()
    active_user_id = CONFIG["bob_device_id"] if active_user == "Bob" else CONFIG["leo_device_id"]
    this_id = CONFIG["this_device_id"]

    if not label or not path:
        messagebox.showwarning("Missing Info", "Folder label and path are required.")
        return

    if not this_id:
        messagebox.showerror("Error", "Cannot add folder: This instance's Device ID is unknown.")
        return

    if not active_user_id:
        messagebox.showerror("Error", f"Cannot add folder: {active_user}'s Device ID is not set in Settings.")
        return

    if not os.path.exists(path):
        if messagebox.askyesno("Path Not Found", f"The path '{path}' doesn't exist on the server hosting Syncthing. Create it?"):
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create directory: {e}")
                return
        else:
            return

    config = get_config()
    if config is None: return

     # Check if folder ID or path already exists
    for f in config.get('folders', []):
        if f['id'] == folder_id:
            messagebox.showwarning("Already Exists", f"Folder ID '{folder_id}' already exists.")
            return
        if f['path'] == path:
            messagebox.showwarning("Already Exists", f"Folder Path '{path}' is already used by folder '{f['label']}'.")
            return

    new_folder = {
        "id": folder_id,
        "label": label,
        "path": path,
        "type": folder_type,
        "rescanIntervalS": 60,  
        "fsWatcherEnabled": True,  
        "devices": [
            {"deviceID": this_id},         # Share with this central instance
            {"deviceID": active_user_id}   # Share with the current user's device
        ],
    }

    config['folders'].append(new_folder)

    if post_config(config):
        messagebox.showinfo("Success", f"Folder '{label}' added and shared with {active_user}.")
        refresh_data()
        folder_label_entry.delete(0, tk.END)
        folder_path_entry.delete(0, tk.END)

def browse_folder():
    path = filedialog.askdirectory()
    if path:
        folder_path_entry.delete(0, tk.END)
        folder_path_entry.insert(0, path)

def generate_folder_id():
    return uuid.uuid4().hex[:10] 

### Saves API & User IDs
def save_settings():
    global CONFIG
    new_url = api_url_entry.get().strip()
    new_key = api_key_entry.get().strip()
    new_bob_id = bob_id_entry.get().strip()
    new_leo_id = leo_id_entry.get().strip()

    if not new_url or not new_key:
        return

    CONFIG["api_url"] = new_url
    CONFIG["api_key"] = new_key
    CONFIG["bob_device_id"] = new_bob_id
    CONFIG["leo_device_id"] = new_leo_id

    status = get_status()
    if status:
        CONFIG["this_device_id"] = status.get('myID', '')
        refresh_data()
        
        
# GUI Setup
root = tk.Tk()
root.title("P2P Sync Manager")
root.geometry("950x750") 

# User Switcher
current_user = tk.StringVar(value="Bob")  
user_frame = ttk.Frame(root)
user_frame.pack(pady=5, fill="x", padx=10)
tk.Label(user_frame, text="Current View:").pack(side=tk.LEFT, padx=5)
ttk.Radiobutton(user_frame, text="Bob", variable=current_user, value="Bob", command=refresh_data).pack(side=tk.LEFT, padx=5)
ttk.Radiobutton(user_frame, text="Leo", variable=current_user, value="Leo", command=refresh_data).pack(side=tk.LEFT, padx=5)
ttk.Button(user_frame, text="🔄 Refresh View", command=refresh_data).pack(side=tk.RIGHT, padx=5)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=(0,10)) 


# Tab 1: Overview
tab1 = ttk.Frame(notebook)
notebook.add(tab1, text="Overview")

# Devices frame
devices_frame = ttk.LabelFrame(tab1, text="Connected Devices")
devices_frame.pack(fill="x", padx=10, pady=5)
device_listbox = tk.Listbox(devices_frame, height=5)
device_listbox.pack(fill="x", expand=True, padx=5, pady=5)

# Split folder view
folders_pane = ttk.PanedWindow(tab1, orient=tk.VERTICAL)
folders_pane.pack(fill="both", expand=True, padx=10, pady=5)

# My Folders frame
my_folders_frame = ttk.LabelFrame(folders_pane, text="My Folders (Synced)")
folders_pane.add(my_folders_frame, weight=1) 
my_folders_listbox = tk.Listbox(my_folders_frame, height=8)
my_folders_listbox.pack(fill="both", expand=True, padx=5, pady=5)

# Discoverable Folders frame (needs dynamic buttons)
discoverable_folders_frame = ttk.LabelFrame(folders_pane, text="Discoverable Folders")
discoverable_title = discoverable_folders_frame 
folders_pane.add(discoverable_folders_frame, weight=1) 


# Tab 2: Add Device
tab2 = ttk.Frame(notebook)
notebook.add(tab2, text="Add Device")

add_folder_info_label = tk.Label(tab2, text=f"Adding folder for the currently selected user: {current_user.get()}")
add_folder_info_label.pack(pady=(10,0))

device_id_frame = ttk.Frame(tab2)
device_id_frame.pack(fill="x", padx=20, pady=(10, 5))
tk.Label(device_id_frame, text="Device ID:").pack(side=tk.LEFT)
device_id_entry = tk.Entry(device_id_frame, width=50)
device_id_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

device_name_frame = ttk.Frame(tab2)
device_name_frame.pack(fill="x", padx=20, pady=5)
tk.Label(device_name_frame, text="Device Name:").pack(side=tk.LEFT)
device_name_entry = tk.Entry(device_name_frame, width=40)
device_name_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

ttk.Button(tab2, text="➕ Add Device to Syncthing", command=add_device).pack(pady=20)
tk.Label(tab2, text="Note: Add the devices here first.\nThen set their IDs in the Settings tab.", wraplength=400, justify=tk.CENTER).pack(pady=10)


# Tab 3: Add Folder
tab3 = ttk.Frame(notebook)
notebook.add(tab3, text="Add New Folder")

add_folder_info_label = tk.Label(tab3, text=f"Adding folder for the currently selected user: {current_user.get()}")
add_folder_info_label.pack(pady=(10,0))
# Update label text when user switches
current_user.trace_add("write", lambda *args: add_folder_info_label.config(text=f"Adding folder for the currently selected user: {current_user.get()}"))

# Folder Label input  
label_frame = ttk.Frame(tab3)
label_frame.pack(fill="x", padx=20, pady=(10, 5))
tk.Label(label_frame, text="Label:").pack(side=tk.LEFT)
folder_label_entry = tk.Entry(label_frame, width=40)
folder_label_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

# Folder Path input
path_frame = ttk.Frame(tab3)
path_frame.pack(fill="x", padx=20, pady=5)
tk.Label(path_frame, text="Path: ").pack(side=tk.LEFT)
folder_path_entry = tk.Entry(path_frame, width=40)
folder_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
ttk.Button(path_frame, text="Browse...", command=browse_folder).pack(side=tk.RIGHT)

# Sync type options  
# sync_type_var = tk.StringVar(value="sendreceive")

ttk.Button(tab3, text="📁 Add Folder", command=add_folder).pack(pady=20)
tk.Label(tab3, text="This will add the folder to the server and then sync it to the user.", wraplength=400, justify=tk.CENTER).pack(pady=10)


# Tab 4: Settings
tab4 = ttk.Frame(notebook)
notebook.add(tab4, text="Settings")

api_settings_frame = ttk.LabelFrame(tab4, text="Syncthing API Settings")
api_settings_frame.pack(fill="x", padx=10, pady=10)

tk.Label(api_settings_frame, text="API URL").grid(row=0, column=0, padx=5, pady=5, sticky="w")
api_url_entry = tk.Entry(api_settings_frame, width=50)
api_url_entry.grid(row=0, column=1, padx=5, pady=5)
api_url_entry.insert(0, CONFIG["api_url"])

tk.Label(api_settings_frame, text="API Key").grid(row=1, column=0, padx=5, pady=5, sticky="w")
api_key_entry = tk.Entry(api_settings_frame, width=50)
api_key_entry.grid(row=1, column=1, padx=5, pady=5)
api_key_entry.insert(0, CONFIG["api_key"])

user_id_frame = ttk.LabelFrame(tab4, text="User Device IDs")
user_id_frame.pack(fill="x", padx=10, pady=10)

tk.Label(user_id_frame, text="Bob's Device ID").grid(row=0, column=0, padx=5, pady=5, sticky="w")
bob_id_entry = tk.Entry(user_id_frame, width=60)
bob_id_entry.grid(row=0, column=1, padx=5, pady=5)
bob_id_entry.insert(0, CONFIG["bob_device_id"])

tk.Label(user_id_frame, text="Leo's Device ID").grid(row=1, column=0, padx=5, pady=5, sticky="w")
leo_id_entry = tk.Entry(user_id_frame, width=60)
leo_id_entry.grid(row=1, column=1, padx=5, pady=5)
leo_id_entry.insert(0, CONFIG["leo_device_id"])

ttk.Button(tab4, text="Save Settings & Test Connection", command=save_settings).pack(pady=20)

if __name__ == "__main__":
	save_settings()  
	if CONFIG["api_key"] and CONFIG["api_key"] != 'YOUR_SYNCTHING_API_KEY':
		refresh_data()
	else:
		messagebox.showinfo("Setup Required", "Welcome! Please configure your Syncthing API Key and User Device IDs in the Settings tab.")

	root.mainloop()