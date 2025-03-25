#!/usr/bin/env python3
import os
import time
import json
import pickle
from datetime import datetime
from pathlib import Path
from hut_collection import HutCollection

# Use the same constants as in your app
DATA_DIR = "data"
HUT_DATA_FILE = os.path.join(DATA_DIR, "hut_data.json")

def ensure_data_dir():
    """Ensure the data directory exists"""
    os.makedirs(DATA_DIR, exist_ok=True)

def update_hut_data():
    """Update hut collection and save to storage"""
    print(f"[{datetime.now().isoformat()}] Starting hut data update...")
    
    try:
        # Create HutCollection instance
        print("Creating HutCollection instance...")
        hut_collection = HutCollection()
        
        # Check if huts were properly loaded
        if not hasattr(hut_collection, 'huts') or not hut_collection.huts:
            print("Failed to load huts. HutCollection initialized but no huts were found.")
            return False
        
        # Save the data
        ensure_data_dir()
        
        # Save the hut data
        with open(HUT_DATA_FILE, 'wb') as f:
            pickle.dump(hut_collection, f)
            
        return True
        
    except Exception as e:
        import traceback
        print(f"Error updating hut data: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    update_hut_data() 