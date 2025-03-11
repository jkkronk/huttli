import streamlit as st
from hut_collection import HutCollection
import datetime
import time
import threading
import pickle
from pathlib import Path

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
                    return huts
        except Exception as e:
            st.error(f"Error loading cache: {e}")
    return None

def save_huts_to_cache(huts):
    """Save huts to cache with current timestamp"""
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump((time.time(), huts), f)
    except Exception as e:
        st.error(f"Error saving cache: {e}")

def update_hut_collection():
    """Update hut collection and cache"""
    hut_collection = HutCollection()
    save_huts_to_cache(hut_collection)
    return hut_collection

@st.cache_resource
def get_hut_collection():
    """Get hut collection from cache or create new one"""
    hut_collection = load_cached_huts()
    if hut_collection is None:
        hut_collection = update_hut_collection()
    return hut_collection

def format_availability(availability):
    """Format availability information for display"""
    if availability:
        return f"{availability.places} places available"
    return "No availability information"

def main():
    st.title("Mountain Hut Availability Checker")
    
    # Initialize or load hut collection
    hut_collection = get_hut_collection()
    
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

    # Minimum places filter
    min_places = st.number_input("Minimum number of places needed", min_value=1, value=1)

    # Get available huts
    available_huts = hut_collection.get_all_available_huts(date_str, min_places)

    if available_huts:
        st.success(f"Found {len(available_huts)} available huts for {selected_date}")
        
        # Display huts in a grid
        cols = st.columns(3)
        for idx, (hut, availability) in enumerate(available_huts):
            with cols[idx % 3]:
                st.subheader(hut.name)
                if hut.img_url:
                    st.image(hut.img_url, use_column_width=True)
                st.write(f"**Available Places:** {availability.places}")
                st.write(f"**Location:** {hut.coordinates}")
                if hut.website:
                    st.markdown(f"[Visit Website]({hut.website})")
                st.divider()
    else:
        st.warning(f"No huts available on {selected_date} with {min_places} places.")

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