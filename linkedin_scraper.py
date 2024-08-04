from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchElementException

from selenium.webdriver.common.action_chains import ActionChains
from collections import OrderedDict
import time
import os
import re
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def capture_screenshot(driver, filename):
    driver.save_screenshot(f"{filename}.png")
    print(f"Screenshot saved as {filename}.png")

def print_page_source(driver):
    print("Current page source:")
    print(driver.page_source[:1000])  # Print first 1000 characters to avoid overwhelming output
    print("...")

def login(driver, email, pswd):
    print("Attempting to log in...")
    driver.get("https://www.linkedin.com/login")
    capture_screenshot(driver, "login_page")
    
    try:
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        username_field.send_keys(email)
        
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(pswd)
        
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        print("Login form submitted")
        capture_screenshot(driver, "after_login")
        
        # Wait for the homepage to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "global-nav"))
        )
        print("Successfully logged in")
    except Exception as e:
        print(f"Login failed: {str(e)}")
        capture_screenshot(driver, "login_error")
        print_page_source(driver)

def go_to_skills_page(driver, username):
    print("Navigating to skills page...")
    driver.get(f"https://www.linkedin.com/in/{username}/details/skills/")
    
    # Wait for the page to finish loading
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'scaffold-finite-scroll')]"))
        )
    except TimeoutException:
        print("Page load timeout. Proceeding anyway.")
    
    time.sleep(10)  # Wait additional time for any dynamic content to load
    capture_screenshot(driver, "skills_page")
    print_page_source(driver)
    print("Current URL:", driver.current_url)
    
    # Debug: Check for skill containers
    skill_containers = driver.find_elements(By.XPATH, "//div[contains(@class, 'display-flex') and contains(@class, 'flex-row') and contains(@class, 'justify-space-between')]")
    print(f"Found {len(skill_containers)} skill containers")

def find_skills_container(driver):
    print("Searching for skills container...")
    possible_xpaths = [
        "//section[contains(@class, 'skills')]",
        "//section[contains(@class, 'artdeco-card')]",
        "//div[contains(@class, 'scaffold-finite-scroll__content')]",
        "//div[contains(@class, 'pvs-list__container')]"
    ]
    
    for xpath in possible_xpaths:
        try:
            skills_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            print(f"Skills container found using XPath: {xpath}")
            return skills_container
        except TimeoutException:
            print(f"XPath {xpath} not found. Trying next...")
    
    print("Could not find skills container with any known XPath.")
    capture_screenshot(driver, "skills_container_not_found")
    print_page_source(driver)
    return None

def safe_find_elements(driver, by, value, timeout=10):
    try:
        elements = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((by, value))
        )
        return elements
    except TimeoutException:
        print(f"Timeout while searching for elements: {value}")
        return []
    except WebDriverException as e:
        print(f"WebDriverException while searching for elements: {value}")
        print(f"Error: {str(e)}")
        return []
    
def find_edit_button_by_xpath(driver, edit_button_xpath):
    try:
        edit_button = driver.find_element(By.XPATH, edit_button_xpath)
        return edit_button
    except NoSuchElementException:
        logger.error(f"Edit button not found with XPath: {edit_button_xpath}")
        return None

def find_edit_button_by_id(driver, edit_button_id):
    try:
        edit_button = driver.find_element(By.ID, edit_button_id)
        return edit_button
    except NoSuchElementException:
        logger.error(f"Edit button not found with ID: {edit_button_id}")
        return None

def process_skill_modal(driver, skill_name):
    logger.info(f"Processing modal for skill: {skill_name}")
    try:
        # Wait for the modal to appear
        modal = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
        )
        
        # Find all checkboxes in the modal
        checkboxes = modal.find_elements(By.XPATH, ".//input[@type='checkbox']")
        
        skill_data = {
            "name": skill_name,
            "associated_items": []
        }
        
        for checkbox in checkboxes:
            if checkbox.is_selected():
                # If checkbox is checked, get the associated label text
                label = checkbox.find_element(By.XPATH, "./following-sibling::label")
                item_text = label.text.strip()
                skill_data["associated_items"].append(item_text)
                logger.info(f"Associated item for {skill_name}: {item_text}")
        
        logger.info(f"Processed {len(skill_data['associated_items'])} associated items for {skill_name}")
        return skill_data
    
    except TimeoutException:
        logger.error(f"Timeout waiting for modal to appear for skill: {skill_name}")
    except NoSuchElementException as e:
        logger.error(f"Element not found in modal for skill {skill_name}: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing modal for skill {skill_name}: {str(e)}")
    
    return None

def close_skill_modal(driver):
    logger.info("Attempting to close the modal")
    try:
        # Wait for the close button to be clickable
        close_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Dismiss']"))
        )
        
        # Click the close button
        close_button.click()
        logger.info("Modal closed successfully")
        
        # Wait for the modal to disappear
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.XPATH, "//div[@role='dialog']"))
        )
        
    except TimeoutException:
        logger.error("Timeout waiting for close button or for modal to disappear")
    except NoSuchElementException:
        logger.error("Close button not found")
    except Exception as e:
        logger.error(f"Error closing modal: {str(e)}")
        
    # Add a short pause to ensure the modal is fully closed
    time.sleep(1)

def close_skill_modal(driver):
    logger.info("Attempting to close the modal")
    try:
        # Wait for the close button to be clickable
        close_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Dismiss']"))
        )
        
        # Click the close button
        close_button.click()
        logger.info("Modal closed successfully")
        
        # Wait for the modal to disappear
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.XPATH, "//div[@role='dialog']"))
        )
        
    except TimeoutException:
        logger.error("Timeout waiting for close button or for modal to disappear")
    except NoSuchElementException:
        logger.error("Close button not found")
    except Exception as e:
        logger.error(f"Error closing modal: {str(e)}")
        
    # Add a short pause to ensure the modal is fully closed
    time.sleep(1)


def process_skill(driver, skill):
    skill_name = skill['name']
    skill_element_xpath = skill['skillElementXPath']
    edit_button_xpath = skill['editButtonXPath']
    edit_button_id = skill['editButtonId']

    logger.info(f"Processing skill: {skill_name}")

    # Find the edit button (try XPath first, then ID if XPath fails)
    edit_button = find_edit_button_by_xpath(driver, edit_button_xpath)
    if edit_button is None:
        edit_button = find_edit_button_by_id(driver, edit_button_id)

    if edit_button:
        try:
            # Scroll the button into view
            driver.execute_script("arguments[0].scrollIntoView(true);", edit_button)
            time.sleep(0.5)  # Short pause after scrolling

            # Click the edit button
            edit_button.click()
            logger.info(f"Clicked edit button for skill: {skill_name}")

            # Process the modal (you'll need to implement this part)
            process_skill_modal(driver, skill_name)

            # Close the modal (you'll need to implement this part)
            close_skill_modal(driver)

        except Exception as e:
            logger.error(f"Error processing skill {skill_name}: {str(e)}")
    else:
        logger.error(f"Could not find edit button for skill: {skill_name}")

def process_all_skills(driver, skills):
    for skill in skills:
        process_skill(driver, skill)


def get_skills(driver):
    logger.info("Attempting to extract skills...")
    
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//section[contains(@class, 'artdeco-card')]"))
        )
    except TimeoutException:
        logger.warning("Timeout waiting for skills section to load.")
        return []

    # Scroll to load all skills
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # Extract skills using JavaScript with more detailed information
    skills = driver.execute_script("""
        function getXPath(element) {
            if (element.id !== '')
                return 'id("' + element.id + '")';
            if (element === document.body)
                return element.tagName;

            var ix = 0;
            var siblings = element.parentNode.childNodes;
            for (var i = 0; i < siblings.length; i++) {
                var sibling = siblings[i];
                if (sibling === element)
                    return getXPath(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
                if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
                    ix++;
            }
        }

        var skillContainers = document.querySelectorAll('div.display-flex.flex-row.justify-space-between');
        return Array.from(skillContainers).map(container => {
            var skillElement = container.querySelector('a[data-field="skill_page_skill_topic"] span[aria-hidden="true"]');
            var editButton = container.querySelector('a[id^="navigation-add-edit-deeplink-edit-skills"]');
            if (skillElement && editButton) {
                var skillXPath = getXPath(skillElement);
                // Only include skills with "profileTabSection-ALL-SKILLS" in their XPath
                if (skillXPath.includes("profileTabSection-ALL-SKILLS")) {
                    return {
                        name: skillElement.textContent.trim(),
                        skillElementXPath: getXPath(skillElement),
                        editButtonId: editButton.id,
                        editButtonXPath: getXPath(editButton)
                    };
                }
            }
            return null;
        }).filter(skill => skill);
    """)

    if skills:
        logger.info(f"Found {len(skills)} skills:")
        for i, skill in enumerate(skills, 1):
            logger.info(f"{i}. {skill['name']}")
            logger.debug(f"   Skill Element XPath: {skill['skillElementXPath']}")
            logger.debug(f"   Edit Button ID: {skill['editButtonId']}")
            logger.debug(f"   Edit Button XPath: {skill['editButtonXPath']}")
        
        # Save skills to a JSON file
        with open('linkedin_skills_detailed.json', 'w') as f:
            json.dump(skills, f, indent=2)
        logger.info("Detailed skills information saved to 'linkedin_skills_detailed.json'")
    else:
        logger.warning("No skills found.")
        capture_screenshot(driver, "skills_not_found")
        print_page_source(driver)

    return skills

def main():
    chrome_driver_path = os.getenv("CHROME_DRIVER_PATH")
    email = os.getenv("LINKEDIN_EMAIL")
    pswd = os.getenv("LINKEDIN_PSWD")
    username = os.getenv("LINKEDIN_USERNAME")

    if not all([chrome_driver_path, email, pswd, username]):
        print("Please ensure all environment variables are set.")
        return

    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service)
    
    try:
        login(driver, email, pswd)
        go_to_skills_page(driver, username)
        
        print("Current URL:", driver.current_url)
        
        skills = get_skills(driver)
        
        if skills:
            print(f"Successfully extracted {len(skills)} skills.")
            process_all_skills(driver, skills)

        else:
            print("Failed to extract any skills.")

        # Capture final state
        # capture_screenshot(driver, "final_state")
        # print_page_source(driver)
    
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        capture_screenshot(driver, "error_state")
        print_page_source(driver)
    
    finally:
        driver.quit()

if __name__ == "__main__":
    main()