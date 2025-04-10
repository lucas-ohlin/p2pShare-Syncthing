from tkinter import messagebox
import requests
import json

class SyncthingAPI():
	def __init__(self, config):
		self.config = config

	def handle_api_error(self, response, action="perform action"):
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

	def get_config(self):
		try:
			r = requests.get(f'{self.config["api_url"]}/system/config', headers={'X-API-Key': self.config["api_key"]}, timeout=10)
			if self.handle_api_error(r, "fetch config"):
				return r.json()
		except requests.exceptions.Timeout:
			messagebox.showerror("API Error", "Connection timed out while fetching config.")
		except Exception as e:
			messagebox.showerror("API Error", f"An unexpected error occurred fetching config: {e}")
		return None  

	def post_config(self, config_data):
		try:
			response = requests.post(f'{self.config["api_url"]}/system/config', headers={'X-API-Key': self.config["api_key"]}, json=config_data, timeout=15)
			return self.handle_api_error(response, "update config")
		except requests.exceptions.Timeout:
			messagebox.showerror("API Error", "Connection timed out while updating config.")
		except Exception as e:
			messagebox.showerror("API Error", f"An unexpected error occurred updating config: {e}")
		return False 

	def get_status(self):
		try:
			r = requests.get(f'{self.config["api_url"]}/system/status', headers={'X-API-Key': self.config["api_key"]}, timeout=10)
			if self.handle_api_error(r, "fetch status"):
				return r.json()
		except requests.exceptions.Timeout:
			messagebox.showerror("API Error", "Connection timed out while fetching status.")
		except Exception as e:
			messagebox.showerror("API Error", f"An unexpected error occurred fetching status: {e}")
		return None

	def get_connections(self):
		try:
			r = requests.get(f'{self.config["api_url"]}/system/connections', headers={'X-API-Key': self.config["api_key"]}, timeout=10)
			if self.handle_api_error(r, "fetch connections"):
				return r.json()
		except requests.exceptions.Timeout:
			messagebox.showerror("API Error", "Connection timed out while fetching connections.")
		except Exception as e:
			messagebox.showerror("API Error", f"An unexpected error occurred fetching connections: {e}")
		return None
