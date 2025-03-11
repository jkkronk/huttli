from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime


class availability:
    def __init__(self, date, places):
        # Convert date string to datetime object if it's a string
        if isinstance(date, str):
            # Try common date formats
            date_formats = [
                "%Y-%m-%d",  # 2024-03-21
                "%d.%m.%Y",  # 21.03.2024
                "%d/%m/%Y",  # 21/03/2024
                "%B %d, %Y"  # March 21, 2024
            ]
            
            for fmt in date_formats:
                try:
                    self.date = datetime.strptime(date, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"Unable to parse date: {date}")
        else:
            self.date = date
        self.places = places

    def __str__(self):
        return f"{self.date.strftime('%Y-%m-%d')} - {self.places}"

    def get_iso_date(self):
        """Return date in ISO format (YYYY-MM-DD)"""
        return self.date.strftime("%Y-%m-%d")

class Hut:
    name = ""
    coordinates = ""
    website = ""
    img_url = ""
    id = ""
    availability = []

    def __init__(self, url):
        self.url = url
        self.soup = self._parse_hut(url)

    def __str__(self):
        return f"{self.name} - {self.coordinates} - {self.website} - {self.img_url}"
    
    def _parse_hut(self, url):
        """
        Parses the hut reservation webpage and extracts relevant information using Selenium.
        Args:
            url: URL of the hut reservation page
        Returns:
            BeautifulSoup object of the parsed page
        """
        # Set up Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)

        try:
            # Load the page
            driver.get(url)
            
            # First wait for the page to load completely
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            # Wait for Angular app to be ready
            WebDriverWait(driver, 20).until(
                lambda driver: driver.execute_script('return window.getAllAngularTestabilities') is not None
            )
            
            # Wait until Angular is stable
            WebDriverWait(driver, 20).until(
                lambda driver: driver.execute_script(
                    'return window.getAllAngularTestabilities().every(t => t.isStable())'
                )
            )
            
            # Store the initial page source for other parsing
            self.soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Now try to find the calendar
            try:
                # Wait for page to be fully loaded and stable
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                
                # Try to find and click the calendar button
                calendar_button_selectors = [
                    "button[aria-label*='calendar']",
                    "button[aria-label*='Choose date']",
                    "input[type='date']",
                    ".date-picker-trigger",
                    "[data-test='date-picker-button']",
                    "mat-datepicker-toggle button"  # Angular Material datepicker toggle
                ]
                
                calendar_button = None
                for selector in calendar_button_selectors:
                    try:
                        calendar_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        break
                    except:
                        continue
                
                if calendar_button:
                    # Try to click the button
                    try:
                        calendar_button.click()
                        # Wait a moment for calendar to appear
                        time.sleep(1)
                    except Exception as click_error:
                        print(f"Error clicking calendar button: {click_error}")
                        # Try JavaScript click as fallback
                        try:
                            driver.execute_script("arguments[0].click();", calendar_button)
                            time.sleep(1)
                        except Exception as js_click_error:
                            print(f"JavaScript click also failed: {js_click_error}")
                else:
                    print("Could not find calendar button")
                    return self.soup

                # Try to find the calendar container with multiple approaches
                calendar_found = False
                for attempt in range(3):
                    try:
                        # Try different selectors for the opened calendar
                        calendar_selectors = [
                            "mat-calendar",  # Angular Material calendar
                            ".mat-calendar-content",
                            ".calendar-container",
                            "[role='dialog'] [role='grid']",  # Calendar popup grid
                            ".cdk-overlay-container mat-calendar"  # Angular overlay calendar
                        ]
                        
                        for selector in calendar_selectors:
                            try:
                                calendar = WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                                )
                                if calendar.is_displayed():
                                    calendar_found = True
                                    break
                            except:
                                continue
                        
                        if calendar_found:
                            # Function to parse calendar cells for a given month
                            def parse_calendar_cells():
                                cell_selectors = [
                                    ".mat-calendar-body-cell",
                                    "td[role='gridcell'] button",
                                    ".calendar-day:not(.disabled)",
                                    "[aria-label*='202']"  # Matches dates with year 202x
                                ]
                                
                                calendar_cells = []
                                for selector in cell_selectors:
                                    calendar_cells = driver.find_elements(By.CSS_SELECTOR, selector)
                                    if calendar_cells:
                                        break
                                
                                if not calendar_cells:
                                    print("No calendar cells found with any selector")
                                    return []
                                
                                month_availability = []
                                # Parse each calendar cell
                                for cell in calendar_cells:
                                    try:
                                        # Try multiple ways to get the date
                                        date_str = cell.get_attribute('aria-label')
                                        if not date_str:
                                            date_str = cell.get_attribute('data-date')
                                        if not date_str:
                                            continue
                                            
                                        # Try multiple selectors for availability number
                                        preview_selectors = [
                                            '.custom-preview',
                                            '.availability-count',
                                            '[class*="places-left"]'
                                        ]
                                        
                                        places_text = None
                                        for selector in preview_selectors:
                                            try:
                                                preview_elem = cell.find_element(By.CSS_SELECTOR, selector)
                                                if preview_elem:
                                                    places_text = preview_elem.text.strip()
                                                    break
                                            except:
                                                continue
                                        
                                        if places_text:
                                            # Extract just the number from text
                                            import re
                                            number_match = re.search(r'\d+', places_text)
                                            if number_match:
                                                places = int(number_match.group())
                                                month_availability.append(availability(date_str, places))
                                                
                                    except Exception as cell_error:
                                        print(f"Error parsing calendar cell: {cell_error}")
                                        continue
                                
                                return month_availability

                            # Parse current month
                            current_month_availability = parse_calendar_cells()
                            all_availability = current_month_availability
                            
                            # Try to get next 5 months (6 months total including current)
                            next_month_selectors = [
                                ".mat-calendar-next-button",
                                "button[aria-label='Next month']",
                                ".mat-calendar-controls button:last-child"
                            ]
                            
                            for month in range(5):  # Do this 5 times for next 5 months
                                next_button = None
                                for selector in next_month_selectors:
                                    try:
                                        next_button = WebDriverWait(driver, 5).until(
                                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                        )
                                        break
                                    except:
                                        continue
                                
                                if next_button:
                                    try:
                                        next_button.click()
                                        # Wait for calendar to update
                                        time.sleep(1)
                                        # Parse next month
                                        next_month_availability = parse_calendar_cells()
                                        all_availability.extend(next_month_availability)
                                    except Exception as click_error:
                                        print(f"Error clicking next month button: {click_error}")
                                        # Try JavaScript click as fallback
                                        try:
                                            driver.execute_script("arguments[0].click();", next_button)
                                            time.sleep(1)
                                            # Parse next month
                                            next_month_availability = parse_calendar_cells()
                                            all_availability.extend(next_month_availability)
                                        except Exception as js_click_error:
                                            print(f"JavaScript click for next month also failed: {js_click_error}")
                                            break  # Stop if we can't navigate to next month
                                else:
                                    print(f"Could not find next month button for month {month + 2}")
                                    break

                            # Store all months' availability
                            self.availability = all_availability
                            break
                            
                    except Exception as e:
                        print(f"Attempt {attempt + 1} failed: {str(e)}")
                        time.sleep(2)  # Wait before retry
                
                if not calendar_found:
                    print("Calendar could not be found after multiple attempts")
                    # Take screenshot for debugging
                    try:
                        driver.save_screenshot("calendar_not_found.png")
                        print("Screenshot saved as calendar_not_found.png")
                    except:
                        print("Could not save screenshot")
                    return self.soup

            except Exception as calendar_error:
                print(f"Could not load calendar: {calendar_error}")
                print(f"Current URL: {driver.current_url}")
                # Take screenshot for debugging
                try:
                    driver.save_screenshot("calendar_error.png")
                    print("Screenshot saved as calendar_error.png")
                except:
                    print("Could not save screenshot")
                self.availability = []
            
            # Updated name selectors based on the HTML structure
            name_selectors = [
                '.hutTitle',  # Add the class from the HTML snippet
                'h2.hutTitle',  # More specific selector
                '.hut_information h2',  # Parent-child relationship
            ]
            
            for selector in name_selectors:
                name_elem = self.soup.select_one(selector)
                if name_elem:
                    self.name = name_elem.text.strip()
                    break
            else:
                self.name = "Name not found"
            
            # Look for coordinates with multiple selectors
            coord_selectors = [
                '.description h3.title:contains("Coordinates:") + p',
            ]
            
            for selector in coord_selectors:
                coords_elem = self.soup.select_one(selector)
                if coords_elem:
                    self.coordinates = coords_elem.text.strip()
                    break
            else:
                self.coordinates = "Coordinates not found"
            
            # Look for website link with multiple selectors
            website_selectors = [
                '.hutWebsite .hyperLink',  # Based on the provided HTML
                '.hutWebsite a',  # More general selector
                'a[target="_blank"]',  # Links that open in new tab
                '[data-test="hut-website"]'
            ]
            
            for selector in website_selectors:
                website_elem = self.soup.select_one(selector)
                if website_elem and 'href' in website_elem.attrs:
                    self.website = website_elem['href']
                    break
            else:
                self.website = url  # Fallback to the reservation page URL
            
            # Look for image with multiple selectors
            img_selectors = [
                '.hero .hut_picture',  # Based on the provided HTML
                '.hero img',  # More general hero image selector
                'img[alt="hut"]',  # Image with alt text
                '.hut_picture',  # Direct class selector
                '.hut-image img',  # Keep some fallbacks
                '.main-image img',
                '.featured-image'
            ]
            
            for selector in img_selectors:
                img_tag = self.soup.select_one(selector)
                if img_tag and 'src' in img_tag.attrs:
                    # Get the highest resolution image if srcset is available
                    if 'srcset' in img_tag.attrs:
                        srcset = img_tag['srcset']
                        # Get the last URL in srcset (typically highest resolution)
                        highest_res = srcset.split(',')[-1].split()[0]
                        self.img_url = highest_res
                    else:
                        self.img_url = img_tag['src']
                    break
            else:
                self.img_url = ""
            
            self.id = url.split('/')[-2]
            
            return self.soup
            
        except Exception as e:
            print(f"Error parsing hut: {str(e)}")
            try:
                print(f"Current URL: {driver.current_url}")
                print(f"Page source preview: {driver.page_source[:500]}")
            except:
                pass
            raise
        
        finally:
            driver.quit()
        
    def get_availability_for_date(self, target_date):
        """
        Get availability for a specific date
        Args:
            target_date: Date string in any supported format or datetime.date object
        Returns:
            availability object if found, None otherwise
        """
        # Convert target_date to datetime.date if it's a string
        if isinstance(target_date, str):
            try:
                target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Invalid date format. Please use YYYY-MM-DD: {target_date}")

        for avail in self.availability:
            if avail.date == target_date:
                return avail
        return None

    def is_available(self, target_date, min_places=1):
        """
        Check if the hut is available for a specific date with minimum required places
        Args:
            target_date: Date string in YYYY-MM-DD format or datetime.date object
            min_places: Minimum number of places needed (default 1)
        Returns:
            Boolean indicating if hut is available
        """
        avail = self.get_availability_for_date(target_date)
        if avail:
            return avail.places >= min_places
        return False

    def get_next_available_dates(self, min_places=1, limit=5):
        """
        Get the next available dates with at least min_places available
        Args:
            min_places: Minimum number of places needed (default 1)
            limit: Maximum number of dates to return (default 5)
        Returns:
            List of availability objects for available dates
        """
        available_dates = []
        for avail in sorted(self.availability, key=lambda x: x.date):
            if avail.places >= min_places:
                available_dates.append(avail)
                if len(available_dates) >= limit:
                    break
        return available_dates

    def get_availability_range(self, start_date, end_date):
        """
        Get availability for a range of dates
        Args:
            start_date: Start date string
            end_date: End date string
        Returns:
            List of availability objects within the date range
        """
        range_availability = []
        for avail in self.availability:
            if start_date <= avail.date <= end_date:
                range_availability.append(avail)
        return sorted(range_availability, key=lambda x: x.date)

    def get_max_availability(self):
        """
        Get the date with maximum available places
        Returns:
            availability object with most places, or None if no availability
        """
        if not self.availability:
            return None
        return max(self.availability, key=lambda x: x.places)

class HutCollection:
    base_url = "https://www.hut-reservation.org/reservation/book-hut/"
    huts = {}

    def __init__(self):
        self._parse_huts()

    def _parse_huts(self, num_huts=2):#439):
        """
        Parse huts from the base URL and add them to the collection
        Args:
            num_huts: Number of huts to parse (default 439)
        """
        for i in range(1, num_huts + 1):
            try:
                # Construct URL with leading zeros (e.g., 001, 002, etc.)
                hut_id = str(i)
                url = f"{self.base_url}{hut_id}/wizard/"
                
                print(f"Parsing hut {i}/{num_huts}: {url}")
                hut = Hut(url)
                
                if hut.name != "Name not found":  # Only add if we successfully parsed the hut
                    self.huts[hut.name] = hut
                    print(f"Successfully added hut: {hut.name}")
                else:
                    print(f"Skipping hut {i} - name not found")
                    
            except Exception as e:
                print(f"Error parsing hut {i}: {str(e)}")
                continue

    def add_hut(self, hut):
        self.huts[hut.name] = hut

    def __str__(self):
        return f"{self.huts}"
    
    def get_hut_by_name(self, name):
        return self.huts[name]
    
    def get_availability(self, name, target_date):
        """
        Get availability for a specific hut on a specific date
        Args:
            name: Name of the hut
            target_date: Date string to check
        Returns:
            availability object if found, None otherwise
        """
        if name not in self.huts:
            return None
        return self.huts[name].get_availability_for_date(target_date)

    def get_all_availability(self, date):
        huts = []
        for hut in self.huts:   
            if date in self.huts[hut].availability:
                huts.append(self.huts[hut])
        return huts
    
    def get_all_huts(self):
        return self.huts
    
    def get_all_available_huts(self, target_date, min_places=1):
        """
        Get all huts that have availability on a specific date
        Args:
            target_date: Date string to check
            min_places: Minimum number of places needed (default 1)
        Returns:
            List of tuples (hut, availability) for available huts
        """
        available_huts = []
        for hut in self.huts.values():
            avail = hut.get_availability_for_date(target_date)
            if avail and avail.places >= min_places:
                available_huts.append((hut, avail))
        return available_huts

    def search_huts(self, query):
        """
        Search for huts by name
        Args:
            query: Search string
        Returns:
            List of Hut objects matching the query
        """
        query = query.lower()
        return [hut for hut in self.huts.values() 
                if query in hut.name.lower()]

    def filter_huts_by_coordinates(self, lat_range=None, lon_range=None):
        """
        Filter huts by coordinate ranges
        Args:
            lat_range: Tuple of (min_lat, max_lat)
            lon_range: Tuple of (min_lon, max_lon)
        Returns:
            List of Hut objects within the coordinate ranges
        """
        filtered_huts = []
        for hut in self.huts.values():
            try:
                # Parse coordinates (assuming format "lat, lon")
                if hut.coordinates and "," in hut.coordinates:
                    lat, lon = map(float, hut.coordinates.split(','))
                    
                    if lat_range and not (lat_range[0] <= lat <= lat_range[1]):
                        continue
                    if lon_range and not (lon_range[0] <= lon <= lon_range[1]):
                        continue
                    
                    filtered_huts.append(hut)
            except (ValueError, AttributeError):
                continue
        return filtered_huts

    def get_huts_with_min_capacity(self, date, min_places):
        """
        Get all huts that have at least min_places available on a specific date
        Args:
            date: Date string to check
            min_places: Minimum number of places needed
        Returns:
            List of tuples (hut, availability) meeting the criteria
        """
        return [(hut, avail) for hut, avail in self.get_all_available_huts(date)
                if avail.places >= min_places]

    def find_consecutive_availability(self, start_date, num_nights, min_places=1):
        """
        Find huts available for consecutive nights
        Args:
            start_date: Start date string
            num_nights: Number of consecutive nights needed
            min_places: Minimum number of places needed per night
        Returns:
            List of Hut objects available for the entire period
        """
        available_huts = []
        for hut in self.huts.values():
            consecutive_available = True
            for i in range(num_nights):
                # Note: This assumes dates can be compared as strings
                # You might need to adjust based on your date format
                current_date = start_date  # You'll need to implement date addition
                if not hut.is_available(current_date, min_places):
                    consecutive_available = False
                    break
            if consecutive_available:
                available_huts.append(hut)
        return available_huts

    def get_huts_sorted_by_availability(self, date):
        """
        Get all huts sorted by number of available places on a specific date
        Args:
            date: Date string to check
        Returns:
            List of tuples (hut, availability) sorted by places available
        """
        available_huts = self.get_all_available_huts(date)
        return sorted(available_huts, key=lambda x: x[1].places, reverse=True)



