from dotenv import load_dotenv
import os
load_dotenv()

CONFIG = {
  "api_url": os.getenv("API_URL"),
  "api_key": os.getenv("API_KEY"),
  "bob_device_id": os.getenv("BOB_DEVICE_ID"),
  "bob_api_url": os.getenv("BOB_API_URL"),
  "bob_api_key": os.getenv("BOB_API_KEY"),
  "leo_device_id": os.getenv("LEO_DEVICE_ID"),
  "leo_api_url": os.getenv("LEO_API_URL"),
  "leo_api_key": os.getenv("LEO_API_KEY"),
}
