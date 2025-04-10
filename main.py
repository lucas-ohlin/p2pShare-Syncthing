from config import CONFIG
from syncthing_api import SyncthingAPI
api = SyncthingAPI(CONFIG)

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import os
import uuid

discoverable_folders_vars = []
def refresh_data():
    global CONFIG
    seen_folder_ids = set()

    if not CONFIG["api_key"] or CONFIG["api_key"] == 'YOUR_SYNCTHING_API_KEY':
        messagebox.showwarning("Configuration Needed", "Please set the Syncthing API Key in the Settings tab.")
        return
    if not CONFIG["bob_device_id"] or not CONFIG["leo_device_id"]:
        messagebox.showwarning("Configuration Needed", "Please set Bob's and Leo's Device IDs in the Settings tab.")

    config = api.get_config()
    status = api.get_status()
    connections = api.get_connections()

    if config is None or status is None or connections is None:
        messagebox.showerror("Error", "Failed to load data from Syncthing. Check connection and API key.")
        return

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
        status_text = "Connected" if connection_details.get(dev_id, {}).get('connected', False) else "Disconnected"
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

    # If multiple folders selected, show a single confirmation dialog
    folder_names = ", ".join([label for _, label in selected])
    if len(selected) > 1:
        confirm_message = f"Start syncing the following folders for {current_user.get()}?\n\n{folder_names}"
    else:
        confirm_message = f"Start syncing the folder '{folder_names}' for {current_user.get()}?"

    if not messagebox.askyesno("Confirm Sync", confirm_message):
        return

    successful_syncs = []
    failed_syncs = []

    # Process all selected folders
    for folder_id, folder_label in selected:
        result = sync_discovered_folder(folder_id, folder_label, skip_confirmation=True, skip_success_message=True)
        if result:
            successful_syncs.append(folder_label)
        else:
            failed_syncs.append(folder_label)
    
    # Refresh once after all syncs are done
    refresh_data()
    
    # Show a single summary message 
    if successful_syncs:
        success_msg = f"Successfully synced folder{'s' if len(successful_syncs) > 1 else ''}:\n" + "\n".join(successful_syncs)
        if failed_syncs:
            success_msg += f"\n\nFailed to sync:\n" + "\n".join(failed_syncs)
        messagebox.showinfo("Sync Complete", success_msg)
    elif failed_syncs:
        messagebox.showerror("Sync Failed", f"Failed to sync folder{'s' if len(failed_syncs) > 1 else ''}:\n" + "\n".join(failed_syncs))
        
def unsync_folder():
    selected_index = my_folders_listbox.curselection()
    if not selected_index:
        messagebox.showinfo("No Selection", "Please select a folder to unsync.")
        return
    
    selected_text = my_folders_listbox.get(selected_index)
    # Extract folder ID from the display text (Format: "Label (ID) → Path")
    import re
    match = re.search(r'\(([^)]+)\)', selected_text)
    if not match:
        messagebox.showerror("Error", "Could not identify folder ID.")
        return
    
    folder_id = match.group(1)
    active_user = current_user.get()
    active_user_id = CONFIG["bob_device_id"] if active_user == "Bob" else CONFIG["leo_device_id"]
    user_api_url = CONFIG["bob_api_url"] if active_user == "Bob" else CONFIG["leo_api_url"]
    user_api_key = CONFIG["bob_api_key"] if active_user == "Bob" else CONFIG["leo_api_key"]
    
    if not messagebox.askyesno("Confirm Unsync", f"Are you sure you want to stop syncing the folder '{selected_text}'?\n\nThis will remove it from {active_user}'s device configuration but won't delete any files."):
        return
    
    config = api.get_config()
    if config is None:
        return
    
    folder_found = False
    for folder in config.get('folders', []):
        if folder['id'] == folder_id:
            folder_found = True
            # Remove the active users device ID from devices list
            folder['devices'] = [d for d in folder.get('devices', []) if d['deviceID'] != active_user_id]
            break
    
    if not folder_found:
        messagebox.showerror("Error", f"Folder with ID '{folder_id}' not found in configuration.")
        return
    
    # Post updated config to central server
    if not api.post_config(config):
        messagebox.showerror("Error", "Failed to update central server configuration.")
        return
    
    if user_api_url and user_api_key:
        try:
            # Fetch users config
            r = requests.get(f"{user_api_url}/system/config", headers={'X-API-Key': user_api_key}, timeout=10)
            r.raise_for_status()
            user_config = r.json()
            
            # Remove folder from user's config
            user_config['folders'] = [f for f in user_config.get('folders', []) if f['id'] != folder_id]
            
            # Update users config
            r = requests.post(f"{user_api_url}/system/config", headers={'X-API-Key': user_api_key}, json=user_config, timeout=10)
            r.raise_for_status()
            
            messagebox.showinfo("Success", f"Folder successfully unsynced from {active_user}'s device.")
        except Exception as e:
            messagebox.showwarning("Partial Success", 
                f"Folder was removed from central server, but failed to update {active_user}'s device configuration: {str(e)}\n\n"
                f"You may need to manually remove the folder from {active_user}'s Syncthing configuration.")
    else:
        messagebox.showinfo("Success", 
            f"Folder was removed from central server configuration.\n\n"
            f"Note: {active_user}'s API details are not configured, so you may need to manually remove the folder from their Syncthing configuration.")
    refresh_data()

def push_folder_to_user(folder, user_api_url, user_api_key):
    try:
        # Fetch users full config
        r = requests.get(f"{user_api_url}/system/config", headers={'X-API-Key': user_api_key}, timeout=10)
        r.raise_for_status()
        user_config = r.json()
    except Exception as e:
        messagebox.showerror("API Error", f"Could not fetch config from remote device: {e}")
        return False

    # Get the server device ID
    central_device_id = CONFIG.get("this_device_id")
    if not central_device_id:
        messagebox.showerror("Error", "Central device ID (this_device_id) not available.")
        return False

    # Make sure the central device is in the users devices list
    if not any(dev["deviceID"] == central_device_id for dev in user_config.get("devices", [])):
        user_config["devices"].append({
            "deviceID": central_device_id,
            "name": "CentralServer",
            "addresses": ["dynamic"],
            "compression": "metadata",
            "introducer": False
        })

    if any(f['id'] == folder['id'] for f in user_config.get('folders', [])):
        return True

    user_folder = folder.copy()
    user_folder["devices"] = [
        {"deviceID": central_device_id},
        {"deviceID": folder["devices"][1]["deviceID"]} 
    ]
    user_config["folders"].append(user_folder)

    try:
        r = requests.post(f"{user_api_url}/system/config", headers={'X-API-Key': user_api_key}, json=user_config, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        messagebox.showerror("API Error", f"Failed to update remote config: {e}")
        return False

### Add current users ID to the sharing list
def sync_discovered_folder(folder_id, folder_label, skip_confirmation=False, skip_success_message=False):
    active_user = current_user.get()
    active_user_id = CONFIG["bob_device_id"] if active_user == "Bob" else CONFIG["leo_device_id"]
    this_id = CONFIG["this_device_id"]

    user_api_url = CONFIG["bob_api_url"] if active_user == "Bob" else CONFIG["leo_api_url"]
    user_api_key = CONFIG["bob_api_key"] if active_user == "Bob" else CONFIG["leo_api_key"]

    if not active_user_id:
        messagebox.showerror("Error", f"Device ID for {active_user} is not set.")
        return False

    config = api.get_config()
    if config is None:
        return False

    folder_to_sync = next((f for f in config['folders'] if f['id'] == folder_id), None)
    if not folder_to_sync:
        messagebox.showerror("Error", f"Folder {folder_label} not found.")
        return False

    # Only show confirmation if not skipped (for batch processing)
    if not skip_confirmation and not messagebox.askyesno("Confirm Sync", f"Start syncing the folder '{folder_label}' for {active_user}?"):
        return False

    # Update central config if user isn't in it
    device_ids = {d['deviceID'] for d in folder_to_sync.get('devices', [])}
    if active_user_id not in device_ids:
        folder_to_sync['devices'].append({"deviceID": active_user_id})
        if not api.post_config(config):
            return False

    # Build full folder block to send to user
    folder_for_user = {
        "id": folder_to_sync["id"],
        "label": folder_to_sync.get("label", folder_to_sync["id"]),
        "path": folder_to_sync["path"],   
        "type": folder_to_sync.get("type", "sendreceive"),
        "rescanIntervalS": folder_to_sync.get("rescanIntervalS", 60),
        "fsWatcherEnabled": folder_to_sync.get("fsWatcherEnabled", True),
        "devices": [
            {"deviceID": this_id},
            {"deviceID": active_user_id}
        ]
    }

    # Send to the users own Syncthing
    success = push_folder_to_user(folder_for_user, user_api_url, user_api_key)
    if success and not skip_success_message:
        messagebox.showinfo("Success", f"Folder '{folder_label}' is now syncing on {active_user}'s device.")
        refresh_data()
        
    return success

### Add device to config
def add_device():
    device_id = device_id_entry.get().strip()
    name = device_name_entry.get().strip()

    if not device_id or not name:
        messagebox.showwarning("Missing Info", "Device ID and Name are required.")
        return

    config = api.get_config()
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

    if api.post_config(config):
        messagebox.showinfo("Success", f"Device '{name}' added successfully. Remember to approve it on the other device if necessary.")
        refresh_data()
        device_id_entry.delete(0, tk.END)
        device_name_entry.delete(0, tk.END)

def add_folder():
    folder_id = generate_folder_id()
    label = folder_label_entry.get().strip()
    path = folder_path_entry.get().strip()
    folder_type = "sendreceive"

    active_user = current_user.get()
    active_user_id = CONFIG["bob_device_id"] if active_user == "Bob" else CONFIG["leo_device_id"]
    user_api_url = CONFIG["bob_api_url"] if active_user == "Bob" else CONFIG["leo_api_url"]
    user_api_key = CONFIG["bob_api_key"] if active_user == "Bob" else CONFIG["leo_api_key"]
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

    config = api.get_config()
    if config is None: return

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
            {"deviceID": this_id},
            {"deviceID": active_user_id}
        ],
    }

    config['folders'].append(new_folder)
    if api.post_config(config):
        # Push the folder to the users Syncthing
        if push_folder_to_user(new_folder, user_api_url, user_api_key):
            messagebox.showinfo("Success", f"Folder '{label}' added and synced to {active_user}'s device.")
        else:
            messagebox.showwarning("Partial Success", f"Folder added to central config, but failed to sync with {active_user}.")
        
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

    status = api.get_status()
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

my_folders_buttons_frame = ttk.Frame(my_folders_frame)
my_folders_buttons_frame.pack(fill="x", padx=5, pady=5)
ttk.Button(my_folders_buttons_frame, text="🔄 Refresh", command=refresh_data).pack(side=tk.LEFT, padx=5)
ttk.Button(my_folders_buttons_frame, text="❌ Unsync Selected Folder", command=unsync_folder).pack(side=tk.LEFT, padx=5)

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
	refresh_data()	
	root.mainloop()