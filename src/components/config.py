import os
import json
import tkinter.messagebox as messagebox

CONFIG_DIR = os.path.join("data")
CONFIG_FILE = os.path.join(CONFIG_DIR, "sync_config.json")

def load_config():
	os.makedirs(CONFIG_DIR, exist_ok=True)
	if os.path.exists(CONFIG_FILE):
		with open(CONFIG_FILE, 'r') as f:
			config = json.load(f)
		return config
	else:
		empty_config = {
			"api_url": "",
			"api_key": "",
			"this_device_id": "",
			"users": {
				"Bob": {"device_id": "", "api_url": "", "api_key": ""},
				"Leo": {"device_id": "", "api_url": "", "api_key": ""}
			}
		}
		with open(CONFIG_FILE, 'w') as f:
			json.dump(empty_config, f, indent=4)
		
		# Show a message to the user that they need to fill in the config
		messagebox.showinfo(
			"No existing config found. A new empty config file has been created.\n\n"
			"Please fill in your Syncthing API details in the Settings tab."
		)
  
		return empty_config

def save_config(config):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        messagebox.showerror("Config Error", f"Error saving configuration: {e}")
        return False

CONFIG = load_config()