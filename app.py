import streamlit as st
from hut_collection import HutCollection
from datetime import datetime, date, timedelta
import time
import pickle
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import json

# Storage constants
DATA_DIR = "data"
HUT_DATA_FILE = os.path.join(DATA_DIR, "hut_data.json")
CACHE_METADATA_FILE = os.path.join(DATA_DIR, "cache_metadata.json")
CACHE_DURATION = 3600  # 1 hour in seconds


def format_availability(availability):
    """Format availability information for display"""
    if availability:
        return f"{availability.places} places available"
    return "No availability information"

def get_hut_collection():
    """
    Get the HutCollection object, either from cache or by creating a new one.
    Returns:
        HutCollection object
    """
    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Check if we have a cached version
    if os.path.exists(HUT_DATA_FILE):
        try:
            # Check cache metadata to see if it's still valid
            if os.path.exists(CACHE_METADATA_FILE):
                with open(CACHE_METADATA_FILE, 'r') as f:
                    metadata = json.load(f)
                    last_update = metadata.get('timestamp', 0)
                    current_time = time.time()
                    
                    # If cache is still valid, load from it
                    if current_time - last_update < CACHE_DURATION:
                        with open(HUT_DATA_FILE, 'r') as f:
                            hut_data = json.load(f)
                            hut_collection = HutCollection(use_cache=True)
                            return hut_collection
            
            # If we get here, cache is expired or metadata is missing
            return update_hut_collection()
            
        except Exception as e:
            st.sidebar.error(f"Error loading cached data: {e}")
            return update_hut_collection()
    else:
        # No cache exists, create a new collection
        return update_hut_collection()

def update_hut_collection():
    """
    Update the HutCollection by creating a new instance and saving to cache.
    Returns:
        Updated HutCollection object
    """
    try:
        # Create a new HutCollection
        hut_collection = HutCollection(use_cache=True, background_updates=True)
        
        # Save to cache
        save_huts_to_cache(hut_collection)
        
        return hut_collection
    except Exception as e:
        st.sidebar.error(f"Error updating hut collection: {e}")
        # Try to create a minimal collection as fallback
        return HutCollection(use_cache=False)

def save_huts_to_cache(hut_collection):
    """
    Save the HutCollection to cache files
    Args:
        hut_collection: HutCollection object to save
    """
    try:
        # Create data directory if it doesn't exist
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Save hut data
        with open(HUT_DATA_FILE, 'w') as f:
            # Convert hut collection to serializable format if needed
            # For now, we're just saving a placeholder
            json.dump({"status": "cached"}, f)
        
        # Update metadata with current timestamp
        with open(CACHE_METADATA_FILE, 'w') as f:
            metadata = {
                "timestamp": time.time(),
                "version": "1.0"
            }
            json.dump(metadata, f)
            
    except Exception as e:
        st.sidebar.error(f"Error saving to cache: {e}")

def main():
    st.title("Are there places in SAC huts available?")
    # Initialize or load hut collection
    hut_collection = get_hut_collection()
    hut_collection.background_updates = True
    hut_collection.update_interval = 1#3600
    hut_collection.start_background_updates()
    save_huts_to_cache(hut_collection)
    
    # Get all huts for comparison
    all_huts = hut_collection.huts if hasattr(hut_collection, 'huts') else {}
    
    if not all_huts:
        st.error("No huts found in the collection. Please try refreshing the data.")
                
        # Try to manually get all huts
        st.write("### Attempting to get huts manually")
        try:
            if hasattr(hut_collection, 'get_all_huts'):
                manual_huts = hut_collection.get_all_huts()
                st.write(f"get_all_huts() returned: {type(manual_huts)} with {len(manual_huts) if manual_huts else 0} items")
                if manual_huts:
                    st.write(f"First item: {list(manual_huts.values())[0] if isinstance(manual_huts, dict) else manual_huts[0] if isinstance(manual_huts, list) else 'Unknown type'}")
        except Exception as e:
            st.write(f"Error getting huts manually: {str(e)}")
        
        # Try to reinitialize
        if st.button("Attempt to reinitialize hut collection"):
            # Force a fresh update
            if os.path.exists(HUT_DATA_FILE):
                os.remove(HUT_DATA_FILE)
            if os.path.exists(CACHE_METADATA_FILE):
                os.remove(CACHE_METADATA_FILE)
            st.info("Cache files deleted")
            
            hut_collection = update_hut_collection()
            st.experimental_rerun()
        return

    # Date selection
    min_date = date.today()
    max_date = min_date + timedelta(days=180)  # 6 months ahead
    selected_date = st.date_input(
        "Select a date",
        min_value=min_date,
        max_value=max_date,
        value=min_date
    )

    # Convert date to ISO format string (YYYY-MM-DD)
    date_str = selected_date.isoformat()  # This will give us YYYY-MM-DD format

    # Get available huts
    try:
        available_huts = hut_collection.get_all_available_huts(date_str, 0)
        #st.sidebar.success(f"Found {len(available_huts)} huts with availability data for {date_str}")
    except Exception as e:
        st.sidebar.error(f"Error getting available huts: {e}")
        available_huts = []
    
    # Create map data for all huts
    map_data = []
    
    if all_huts:  # Only process if we have huts
        # Handle both dictionary and list cases
        huts_to_process = all_huts.values() if isinstance(all_huts, dict) else all_huts
        
        for hut in huts_to_process:
            try:
                # Skip huts without valid coordinates
                if not hasattr(hut, 'coordinates') or not hut.coordinates:
                    continue
                
                # Handle different coordinate formats (comma or slash separator)
                if ',' in hut.coordinates:
                    lat, lon = map(float, hut.coordinates.split(','))
                elif '/' in hut.coordinates:
                    lat, lon = map(float, hut.coordinates.split('/'))
                else:
                    # Skip if coordinates don't have a recognized separator
                    continue
                    
                # Get availability for this hut on the selected date
                avail = None
                try:
                    avail = hut.get_availability_for_date(date_str)
                except Exception as e:
                    # Silently continue if availability can't be determined
                    pass
                
                places = avail.places if avail else 0
                
                map_data.append({
                    "lat": lat,
                    "lon": lon,
                    "name": getattr(hut, 'name', str(hut)),
                    "color": "green" if places > 0 else "red",
                    "availability": places
                })
            except Exception as e:
                # Skip this hut if there's an error
                continue

    if map_data:
        # Convert to DataFrame for map display
        df = pd.DataFrame(map_data)
        
        # Create a folium map centered on the mean coordinates
        if not df.empty:
            # Center on the mean of all huts
            center_lat = df['lat'].mean()
            center_lon = df['lon'].mean()
            zoom_start = 8  # Default zoom for all huts
            
            # Create the map with a specific height and zoom level
            m = folium.Map(
                location=[center_lat, center_lon], 
                zoom_start=zoom_start,
                tiles="CartoDB positron",  # Lighter, cleaner map style
                control_scale=True  # Add distance scale
            )
            
            # Count available and unavailable huts
            available_count = sum(1 for row in map_data if row['color'] == 'green')
            
            # Add markers for each hut
            for _, row in df.iterrows():
                # Find the full hut object to get website and image URL
                hut_obj = None
                huts_to_process = all_huts.values() if isinstance(all_huts, dict) else all_huts
                
                for hut in huts_to_process:
                    if hasattr(hut, 'name') and hut.name == row['name']:
                        hut_obj = hut
                        break
                
                # Create more detailed popup content
                popup_content = f"<b>{row['name']}</b>"
                
                # Add availability information
                if row['color'] == 'green':
                    popup_content += f"<br>{row['availability']} places available"
                else:
                    popup_content += "<br>Not available for selected date"
                
                # Add website link if available
                if hut_obj and hasattr(hut_obj, 'website') and hut_obj.website:
                    popup_content += f'<br><a href="{hut_obj.website}" target="_blank">Visit Website</a>'
                
                # Add image if available
                if hut_obj and hasattr(hut_obj, 'img_url') and hut_obj.img_url:
                    popup_content += f'<br><img src="{hut_obj.img_url}" style="max-width:200px; max-height:150px; margin-top:10px;">'
                
                icon_color = row['color']  # 'green' for available, 'red' for unavailable
                
                # Create a simpler custom DivIcon with the availability number
                folium.Marker(
                    location=[row['lat'], row['lon']],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=row['name'],
                    icon=folium.DivIcon(
                        icon_size=(30, 30),
                        icon_anchor=(15, 15),
                        html=f'''
                            <div style="
                                font-size: 10pt; 
                                color: white; 
                                background-color: {icon_color}; 
                                border-radius: 50%; 
                                width: 24px; 
                                height: 24px; 
                                display: flex; 
                                align-items: center; 
                                justify-content: center;
                                box-shadow: 0 0 3px rgba(0,0,0,0.4);
                            ">
                                {row["availability"]}
                            </div>
                        '''
                    )
                ).add_to(m)
            
            # Display the map with explicit width and height
            st_folium(m, width=800, height=600, returned_objects=[])
        else:
            st.warning("No huts found with valid location data")
    else:
        st.error("No hut location data available to display on the map.")


if __name__ == "__main__":
    main() 