import streamlit as st
from hut_collection import HutCollection
import datetime
import time
import threading
import pickle
from pathlib import Path
import pandas as pd
import folium
from streamlit_folium import st_folium

# Cache file for storing hut data
CACHE_FILE = "hut_cache.pkl"
CACHE_DURATION = 3600  # 1 hour in seconds

def load_cached_huts():
    """Load huts from cache if available and not expired"""
    if Path(CACHE_FILE).exists():
        try:
            with open(CACHE_FILE, 'rb') as f:
                cache_time, huts = pickle.load(f)
                if time.time() - cache_time < CACHE_DURATION:
                    st.sidebar.success("Using cached hut data")
                    return huts
                else:
                    st.sidebar.info("Cache expired, refreshing data...")
        except Exception as e:
            st.sidebar.error(f"Error loading cache: {e}")
    return None

def save_huts_to_cache(huts):
    """Save huts to cache with current timestamp"""
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump((time.time(), huts), f)
        st.sidebar.success("Hut data cached successfully")
    except Exception as e:
        st.sidebar.error(f"Error saving cache: {e}")

def update_hut_collection():
    """Update hut collection and cache"""
    with st.sidebar.status("Fetching fresh hut data..."):
        try:
            # Add debug for HutCollection initialization
            st.sidebar.info("Creating HutCollection instance...")
            hut_collection = HutCollection()
            
            # Check if huts were properly loaded
            if not hasattr(hut_collection, 'huts') or not hut_collection.huts:
                st.sidebar.error("Failed to load huts. HutCollection initialized but no huts were found.")
                
                # Try to explicitly parse huts if the method exists
                if hasattr(hut_collection, '_parse_huts'):
                    st.sidebar.info("Attempting to explicitly parse huts...")
                    try:
                        hut_collection._parse_huts()
                        st.sidebar.info(f"After _parse_huts: {len(hut_collection.huts) if hasattr(hut_collection, 'huts') and hut_collection.huts else 0} huts")
                    except Exception as e:
                        st.sidebar.error(f"Error in _parse_huts: {str(e)}")
                
                # Try to manually add a test hut to see if the collection works
                try:
                    st.sidebar.info("Attempting to add a test hut...")
                    if hasattr(hut_collection, 'add_hut'):
                        # Create a simple test hut
                        class TestHut:
                            def __init__(self):
                                self.id = "test_id"
                                self.name = "Test Hut"
                                self.coordinates = "46.5,7.5"  # Example coordinates in Switzerland
                                self.website = "https://example.com"
                                self.img_url = None
                        
                        test_hut = TestHut()
                        hut_collection.add_hut(test_hut)
                        st.sidebar.info(f"After adding test hut: {len(hut_collection.huts) if hasattr(hut_collection, 'huts') and hut_collection.huts else 0} huts")
                except Exception as e:
                    st.sidebar.error(f"Error adding test hut: {str(e)}")
            
            # Check again after potential explicit parsing
            if hasattr(hut_collection, 'huts') and hut_collection.huts:
                save_huts_to_cache(hut_collection)
                st.sidebar.success(f"Successfully loaded {len(hut_collection.huts)} huts")
            else:
                st.sidebar.error("Still no huts found after initialization")
                
        except Exception as e:
            st.sidebar.error(f"Error initializing hut collection: {str(e)}")
            import traceback
            st.sidebar.error(f"Traceback: {traceback.format_exc()}")
            hut_collection = HutCollection()  # Create an empty collection as fallback
            
    return hut_collection

def get_hut_collection():
    """Get hut collection from cache or create new one"""
    hut_collection = load_cached_huts()
    if hut_collection is None:
        st.sidebar.warning("No cached data found. Fetching fresh data...")
        hut_collection = update_hut_collection()
    
    # Add debug information
    if hasattr(hut_collection, 'huts'):
        hut_count = len(hut_collection.huts) if isinstance(hut_collection.huts, list) else len(hut_collection.huts.keys()) if isinstance(hut_collection.huts, dict) else 0
        st.sidebar.info(f"Loaded {hut_count} huts")
    else:
        st.sidebar.error("Hut collection doesn't have 'huts' attribute")
    
    return hut_collection

def format_availability(availability):
    """Format availability information for display"""
    if availability:
        return f"{availability.places} places available"
    return "No availability information"

def main():
    st.title("HüttenCheckr")
    
    # Add a button to view the hut_collection.py file content
    if st.sidebar.button("Show HutCollection Code"):
        try:
            with open("hut_collection.py", "r") as f:
                code = f.read()
                st.sidebar.code(code, language="python")
        except Exception as e:
            st.sidebar.error(f"Could not read hut_collection.py: {str(e)}")
    
    # Add a button to manually create a test hut collection
    if st.sidebar.button("Create Test Hut Collection"):
        try:
            # Create a simple test hut collection with one hut
            class TestHut:
                def __init__(self, id, name, coordinates):
                    self.id = id
                    self.name = name
                    self.coordinates = coordinates
                    self.website = f"https://example.com/{id}"
                    self.img_url = None
            
            class TestAvailability:
                def __init__(self, places):
                    self.places = places
            
            # Create a minimal HutCollection with test data
            test_collection = HutCollection()
            test_collection.huts = {}
            
            # Add a test hut
            test_hut = TestHut("test1", "Test Mountain Hut", "46.5,7.5")
            test_collection.huts[test_hut.id] = test_hut
            
            # Save to cache
            save_huts_to_cache(test_collection)
            st.sidebar.success("Created and saved test hut collection")
            st.experimental_rerun()
        except Exception as e:
            st.sidebar.error(f"Error creating test collection: {str(e)}")
    
    # Initialize or load hut collection
    hut_collection = get_hut_collection()
    
    # Get all huts for comparison
    all_huts = hut_collection.huts if hasattr(hut_collection, 'huts') else {}
    
    if not all_huts:
        st.error("No huts found in the collection. Please try refreshing the data.")
        
        # Add debug information
        st.write("### Debug Information")
        st.write(f"Hut collection type: {type(hut_collection)}")
        st.write(f"Hut collection attributes: {dir(hut_collection)}")
        
        # Try to manually get all huts
        st.write("### Attempting to get huts manually")
        try:
            if hasattr(hut_collection, 'get_all_huts'):
                manual_huts = hut_collection.get_all_huts()
                st.write(f"get_all_huts() returned: {type(manual_huts)} with {len(manual_huts) if manual_huts else 0} items")
                if manual_huts:
                    st.write(f"First item: {manual_huts[0] if isinstance(manual_huts, list) else next(iter(manual_huts))}")
        except Exception as e:
            st.write(f"Error getting huts manually: {str(e)}")
        
        # Try to reinitialize
        if st.button("Attempt to reinitialize hut collection"):
            # Force a fresh update by deleting the cache file
            if Path(CACHE_FILE).exists():
                Path(CACHE_FILE).unlink()
                st.info("Cache file deleted")
            
            hut_collection = update_hut_collection()
            st.experimental_rerun()

    # Date selection
    min_date = datetime.date.today()
    max_date = min_date + datetime.timedelta(days=180)  # 6 months ahead
    selected_date = st.date_input(
        "Select a date",
        min_value=min_date,
        max_value=max_date,
        value=min_date
    )

    # Convert date to ISO format string (YYYY-MM-DD)
    date_str = selected_date.isoformat()  # This will give us YYYY-MM-DD format

    # Get available huts
    available_huts = hut_collection.get_all_available_huts(date_str, 0)
    
    # If all_huts contains strings instead of hut objects, try to get the actual hut objects
    if all_huts:
        # Check if all_huts is a dictionary
        if isinstance(all_huts, dict):
            # Get the first value to check its type
            if all_huts:
                first_key = next(iter(all_huts))
                first_hut = all_huts[first_key]
                if isinstance(first_hut, str):
                    # Try to get the actual hut objects from the collection
                    all_huts = hut_collection.get_all_huts()
        # If it's a list-like object
        elif len(all_huts) > 0 and isinstance(all_huts[0], str):
            # Try to get the actual hut objects from the collection
            all_huts = hut_collection.get_all_huts()
    
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
                    
                # Check if hut is in available_huts
                is_available = False
                availability_info = ""
                
                for available_hut, availability in available_huts:
                    if (hasattr(hut, 'id') and hasattr(available_hut, 'id') and available_hut.id == hut.id) or \
                       (hasattr(hut, 'name') and hasattr(available_hut, 'name') and available_hut.name == hut.name):
                        is_available = True
                places = hut.get_availability_for_date(date_str).places
                map_data.append({
                    "lat": lat,
                    "lon": lon,
                    "name": getattr(hut, 'name', str(hut)),
                    "color": "green" if places > 0 else "red",
                    "availability": places
                })
            except (ValueError, AttributeError) as e:
                # Optionally log the error for debugging
                # print(f"Error processing hut {getattr(hut, 'name', 'unknown')}: {str(e)}")
                continue

    if map_data:
        # Convert to DataFrame for map display
        df = pd.DataFrame(map_data)
        
        # Add dropdown to select specific hut or all huts
        hut_names = [hut["name"] for hut in map_data]
        hut_names.sort()  # Sort alphabetically
        hut_options = ["All Huts"] + hut_names
        selected_hut = st.selectbox("Select a hut to display", hut_options)
        
        # Filter data based on selection
        if selected_hut != "All Huts":
            df = df[df["name"] == selected_hut]
        
        # Create a folium map centered on the mean coordinates or selected hut
        if selected_hut != "All Huts":
            # Center on the selected hut
            center_lat = df['lat'].iloc[0]
            center_lon = df['lon'].iloc[0]
            zoom_start = 12  # Closer zoom for single hut
        else:
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
        st.error("No hut location data available to display on the map.")

    # Add information about last update
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE, 'rb') as f:
            cache_time, _ = pickle.load(f)
            last_update = datetime.datetime.fromtimestamp(cache_time)
            st.sidebar.info(f"Last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")

    # Add manual refresh button
    if st.sidebar.button("Refresh Hut Data"):
        st.sidebar.info("Updating hut data... This may take a few minutes.")
        hut_collection = update_hut_collection()
        st.rerun()

if __name__ == "__main__":
    main() 