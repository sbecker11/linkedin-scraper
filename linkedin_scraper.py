
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def login(driver, email, pswd):
    logger.info("Attempting to log in...")
    driver.get("https://www.linkedin.com/login")
    
    try:
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        username_field.send_keys(email)
        
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(pswd)
        
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "global-nav"))
        )
        logger.info("Successfully logged in")
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise

def go_to_skills_page(driver, username):
    logger.info("Navigating to skills page...")
    driver.get(f"https://www.linkedin.com/in/{username}/details/skills/")
    
    # Wait for the page to finish loading
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'scaffold-finite-scroll')]"))
        )
    except TimeoutException:
        logger.warning("Page load timeout. Proceeding anyway.")
    
    time.sleep(10)  # Wait additional time for any dynamic content to load
    capture_screenshot(driver, "skills_page.png")
    capture_page_source(driver, "skills_page.txt")
    logger.info(f"Current URL: {driver.current_url}")
    
    # Debug: Check for skill containers
    skill_containers = driver.find_elements(By.XPATH, "//div[contains(@class, 'display-flex') and contains(@class, 'flex-row') and contains(@class, 'justify-space-between')]")
    logger.info(f"Found {len(skill_containers)} skill containers")
    return skill_containers

def capture_screenshot(driver, filename):
    if not filename.endswith(".png"):
        raise ValueError("Filename must end with .png")
    driver.save_screenshot(f"{filename}")
    logger.info(f"Screenshot saved as {filename}")

def capture_page_source(driver, filename):
    if not filename.endswith(".txt"):
        raise ValueError("Filename must end with .txt")
    with open(filename,"w") as file:
        file.write(driver.page_source)
    logger.info(f"Page source saved as {filename}")

def find_skill_containers(driver):
    logger.info("Attempting to find all skill containers...")
    skill_containers = []
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    max_scroll_attempts = 10  # Adjust this value as needed

    while scroll_attempts < max_scroll_attempts:
        # Find all skill containers, including both ALL-SKILLS and INDUSTRY-KNOWLEDGE-SKILLS
        current_containers = driver.find_elements(By.XPATH, "//li[starts-with(@id, 'profilePagedListComponent-') and contains(@id, '-SKILLS-VIEW-DETAILS-profileTabSection-')]")
        
        # Filter for ALL-SKILLS containers
        new_all_skills_containers = [
            container for container in current_containers 
            if 'ALL-SKILLS' in container.get_attribute('id') 
            and container not in skill_containers
        ]
        
        if new_all_skills_containers:
            for container in new_all_skills_containers:
                skill_containers.append(container)
                # Try to find the skill name from the SVG aria-label
                try:
                    # Step 1: Find the div with class "pvs-navigation__icon"
                    icon_div = container.find_element(By.XPATH, ".//div[@class='pvs-navigation__icon']")
                    if icon_div is None:
                        logger.warn(f"Could not find pvs-navigation__icon div for container ID: {container.get_attribute('id')}")
                    else:
                        logger.info(f"Found pvs-navigation__icon div for container ID: {container.get_attribute('id')}")
        
                        # Step 2: Find the svg element within the div
                        svg_element = icon_div.find_element(By.XPATH, "./svg[@aria-label]")
                        if svg_element is None:
                            logger.warn(f"Could not find SVG element within pvs-navigation__icon div for container ID: {container.get_attribute('id')}")
                        else:
                            logger.info(f"Found SVG element within pvs-navigation__icon div for container ID: {container.get_attribute('id')}")
                        
                             # Extract and process the skill name
                            skill_name = svg_element.get_attribute('aria-label')
                            if skill_name is None:
                                logger.warning("Could not extract skill name from SVG element")
                            else:
                                if skill_name.startswith("Edit "):
                                    skill_name = skill_name[5:]  # Remove "Edit " prefix
                                logger.info(f"Found new ALL-SKILLS container. Skill: {skill_name}")

                except NoSuchElementException:
                    logger.warning("Could not find SVG element with aria-label for a skill container")
                except Exception as e:
                    logger.error(f"Error extracting skill name: {str(e)}")
            
            logger.info(f"Found {len(new_all_skills_containers)} new ALL-SKILLS containers. Total: {len(skill_containers)}")
            scroll_attempts = 0  # Reset scroll attempts if we found new containers
        else:
            scroll_attempts += 1
            logger.info(f"No new ALL-SKILLS containers found. Scroll attempt {scroll_attempts}/{max_scroll_attempts}")

        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for potential new content to load

        # Check if scrolled
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break  # Stop if the page height didn't change after scrolling
        last_height = new_height

        # Check for "Show more" button and click if present
        try:
            show_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Show more')]")
            show_more_button.click()
            logger.info("Clicked 'Show more' button")
            time.sleep(2)  # Wait for new content to load after clicking
            scroll_attempts = 0  # Reset scroll attempts after clicking "Show more"
        except NoSuchElementException:
            pass  # No "Show more" button found, continue scrolling

    logger.info(f"Total unique ALL-SKILLS containers found: {len(skill_containers)}")
    return skill_containers

def main():
    chrome_driver_path = os.getenv("CHROME_DRIVER_PATH")
    email = os.getenv("LINKEDIN_EMAIL")
    pswd = os.getenv("LINKEDIN_PSWD")
    username = os.getenv("LINKEDIN_USERNAME")

    if not all([chrome_driver_path, email, pswd, username]):
        logger.error("Please ensure all environment variables are set.")
        return

    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service)
    
    try:
        login(driver, email, pswd)
        go_to_skills_page(driver, username)
        
        skill_containers = find_skill_containers(driver)
        logger.info(f"Found {len(skill_containers)} skill containers")
        
        # Capture final state
        capture_screenshot(driver, "after_find_skills.png")
        capture_page_source(driver, "after_find_skills.txt")
        logger.info("Captured page state after finding skills")
    
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        capture_screenshot(driver, "error_state.png")
        capture_page_source(driver, "error_state.txt")
    
    finally:
        driver.quit()
        
if __name__ == "__main__":
    main()
