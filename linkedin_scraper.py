import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
import time
from click_logger import ClickLogger


# Configure logging
logging.basicConfig(level=logging.INFO)

click_logger = ClickLogger('./click_logger.txt')

# Read the contents of absoluteXPath.js into a string variable
with open('./absoluteXPath.js', 'r') as file:
    absoluteXPath_js_str = file.read()

def getElementXPath(driver, element):
    """Get the XPath of a given element using the JavaScript function."""
    try:
        # Ensure the absoluteXPath function is injected
        driver.execute_script(absoluteXPath_js_str)
        # Now use the function to get the XPath
        xpath = driver.execute_script("return absoluteXPath(arguments[0]);", element)
        logging.debug(f"Generated XPath: {xpath}")
        return xpath
    except Exception as e:
        logging.error(f"Error generating XPath: {str(e)}")
        return None
    
def wait_for_click(driver, timeout=10):
    """Wait for a click event on any element."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Wait for a very short time to see if any element has been clicked
            element = WebDriverWait(driver, 0.1).until(EC.element_to_be_clickable((By.XPATH, "//*[@clicked='true']")))
            return element
        except TimeoutException:
            # No click detected, continue waiting
            pass
    # If we get here, no click was detected within the timeout period
    return None

class AnyClickableElementToBeClicked(object):
    def __call__(self, driver):
        for element in driver.find_elements(By.XPATH,
            "//*[not(ancestor::*[contains(@class, 'click-logging-disabled')]) "
            "and not(contains(@class, 'click-logging-disabled'))]"
        ):
            if element.is_enabled() and element.is_displayed():
                return element
        return False

def log_clicks_loop(driver, timeout=10):
    """Enter a loop and log the XPaths of clicked elements. 
    Wait for the specified timeout (default 10 seconds) for each click."""
    while True:
        print(f"You have {timeout} seconds to click an element")
        
        # Inject the click listener
        driver.execute_script("""
            window.lastClickedElement = null;
            document.addEventListener('click', function(e) {
                window.lastClickedElement = e;
            }, true);
        """)
        
        # Wait for a click for the specified timeout
        start_time = time.time()
        click_event = None
        while time.time() - start_time < timeout:
            try:
                click_event = driver.execute_script("return window.lastClickedElement;")
                if click_event:
                    # Get the XPath immediately after the click
                    xpath = driver.execute_script("""
                        var getXPath = """ + absoluteXPath_js_str + """
                        return getXPath(arguments[0].target);
                    """, click_event)
                    
                    if xpath:
                        click_logger.log_click(xpath)
                        logging.info(f"Clicked element: {xpath}")
                    else:
                        logging.warning("Unable to generate XPath for clicked element")
                    
                    # Reset the lastClickedElement
                    driver.execute_script("window.lastClickedElement = null;")
                    break
            except Exception as e:
                logging.error(f"Error processing clicked element: {str(e)}")
            time.sleep(0.1)
        
        if not click_event:
            logging.info(f"No element clicked within {timeout} seconds. Exiting loop.")
            break

    # Remove the click listener when exiting the loop
    driver.execute_script("""
        document.removeEventListener('click', arguments[0]);
    """)

def login(driver):
    username = os.getenv("LINKEDIN_USERNAME")
    password = os.getenv("LINKEDIN_PASSWORD")
    
    driver.get("https://www.linkedin.com/login")
    
    username_input = driver.find_element(By.ID, "username")
    password_input = driver.find_element(By.ID, "password")
    
    username_input.send_keys(username)
    password_input.send_keys(password)
    
    login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    login_button.click()

def main():
    service = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service)
    try:
        # Initialize the WebDriver (example with Chrome)
        login(driver)
        log_clicks_loop(driver, timeout=100)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()