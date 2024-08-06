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

from logging_setup import setup_logging
import logging

setup_logging(log_file='app.log', console_level=logging.INFO, file_level=logging.DEBUG)


from element_utils import get_element_info,find_element_by_unique_xpath, find_child_element_by_relative_id, find_child_element_by_relative_xpath, is_clickable_anchor


# basic stdout logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add file handler
file_handler = logging.FileHandler('linkedin_scraper.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(file_handler)

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

def find_edit_skill_link(driver, skill):
    logger.info(f"Attempting to find edit skill link with skill: {skill}")
    
    # Find the parent element
    skill_element_xpath = skill['skillElementXPath']
    parent_skill_element = find_element_by_unique_xpath(driver, skill_element_xpath)
    if parent_skill_element is None:
        logger.error(f"Parent skill element not found with XPath: {skill_element_xpath}")
        return None 
    
    parent_skill_element_info = get_element_info(driver, parent_skill_element)
    print(f"Parent skill element info: {parent_skill_element_info}")
    
    # Scroll the parent skill element into view
    driver.execute_script("arguments[0].scrollIntoView(true);", parent_skill_element)
        
    # Wait a short time for any lazy-loaded content to appear
    driver.implicitly_wait(1)
    
    # try to find the edit skill link by XPath or by id
    edit_skill_link_XPath = skill['editSkillLinkXPath']
    edit_skill_link_id = skill['editSkillLinkId']
    edit_skill_link = \
        find_child_element_by_relative_xpath(parent_skill_element, edit_skill_link_XPath) or \
            find_child_element_by_relative_id(parent_skill_element, edit_skill_link_id)   

    if edit_skill_link is None:
        logger.error(f"edit_skill_link not found with either XPath: {edit_skill_link_XPath} or ID: {edit_skill_link_id}")
        return None 

    return edit_skill_link

def process_skill_modal(driver, skill_name) -> dict:
    logger.info(f"Processing modal for skill: {skill_name} returns skill_data with name and associated_items")
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
                logger.info(f"Associated item: {item_text}")  
              
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
        # Wait for the close_skill_modal_button to be clickable
        close_skill_modal_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Dismiss']"))
        )
        
        # Click the close_skill_modal_button
        close_skill_modal_button.click()
        logger.info("Modal closed successfully")
        
        # Wait for the modal to disappear
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.XPATH, "//div[@role='dialog']"))
        )
        
    except TimeoutException:
        logger.error("Timeout waiting for close_skill_modal_button or for modal to disappear")
    except NoSuchElementException:
        logger.error("close_skill_modal_button not found")
    except Exception as e:
        logger.error(f"Error closing modal: {str(e)}")
        
    # Add a short pause to ensure the modal is fully closed
    time.sleep(1)


# def process_skill(driver, skill):
#     skill_name = skill['name']

#     logger.info(f"Processing skill: {skill_name}")

#     # Find the edit skill link (try XPath first, then ID if XPath fails)
#     edit_skill_link = find_edit_skill_link(driver, skill)

#     if edit_skill_link:
#         if is_clickable_anchor(driver, edit_skill_link):
#             try:
#                 # Scroll the edit skill link into view
#                 # driver.execute_script("arguments[0].scrollIntoView(true);", edit_skill_link)
#                 # time.sleep(0.5)  # Short pause after scrolling

#                 # Click the edit skill link
#                 edit_skill_link.click()
#                 logger.info(f"Clicked edit skill link for skill: {skill_name}")

#                 # Process the modal (you'll need to implement this part)
#                 skill_data = process_skill_modal(driver, skill_name)

#                 if skill_data:
#                     skill['associated_items'] = skill_data['associated_items']

#                 close_skill_modal(driver)

#             except Exception as e:
#                 logger.error(f"Error processing skill {skill_name}: {str(e)}")
#         else:
#             logger.error(f"edit_skill_link not clickable for skill: {skill_name}")
#     else:
#         logger.error(f"Could not find edit skill link for skill: {skill_name}")

# def count_elements_with_id(driver, id_value):
#     elements = driver.find_elements(By.ID, id_value)
#     return len(elements)

# def process_all_skills(driver, skills):
#     for skill in skills:
#         logger.info(f"Processing skill: {skill['name']}")
#         # process the skill
#         process_skill(driver, skill)


# def get_skills(driver):
#     logger.info("Attempting to extract skills...")
    
#     try:
#         WebDriverWait(driver, 20).until(
#             EC.presence_of_element_located((By.XPATH, "//section[contains(@class, 'artdeco-card')]"))
#         )
#     except TimeoutException:
#         logger.warning("Timeout waiting for skills section to load.")
#         return []

#     # Scroll to load all skills
#     last_height = driver.execute_script("return document.body.scrollHeight")
#     while True:
#         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#         time.sleep(2)
#         new_height = driver.execute_script("return document.body.scrollHeight")
#         if new_height == last_height:
#             break
#         last_height = new_height

#     # Extract skills using JavaScript with more detailed information
#     skills = driver.execute_script("""
#         function getXPath(element) {
#             if (element.id !== '')
#                 return 'id("' + element.id + '")';
#             if (element === document.body)
#                 return element.tagName;

#             var ix = 0;
#             var siblings = element.parentNode.childNodes;
#             for (var i = 0; i < siblings.length; i++) {
#                 var sibling = siblings[i];
#                 if (sibling === element)
#                     return getXPath(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
#                 if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
#                     ix++;
#             }
#         }

#         var skillContainers = document.querySelectorAll('div.display-flex.flex-row.justify-space-between');
#         return Array.from(skillContainers).map(container => {
#             var skillElement = container.querySelector('a[data-field="skill_page_skill_topic"] span[aria-hidden="true"]');
#             var editSkillLink = container.querySelector('a[id^="navigation-add-edit-deeplink-edit-skills"]');
#             if (skillElement && editSkillLink) {
#                 var skillXPath = getXPath(skillElement);
#                 // Only include skills with "profileTabSection-ALL-SKILLS" in their XPath
#                 if (skillXPath.includes("profileTabSection-ALL-SKILLS")) {
#                     return {
#                         name: skillElement.textContent.trim(),
#                         skillElementXPath: getXPath(skillElement),
#                         editSkillLinkId: editSkillLink.id,
#                         editSkillLinkXPath: getXPath(editSkillLink)
#                     };
#                 }
#             }
#             return null;
#         }).filter(skill => skill);
#     """)

#     if skills:
#         logger.info(f"Found {len(skills)} skills:")
#         for i, skill in enumerate(skills, 1):
#             logger.info(f"{i}. {skill['name']}")
#             logger.debug(f"   Skill Element XPath: {skill['skillElementXPath']}")
#             logger.debug(f"   edit skill link ID: {skill['editSkillLinkId']}")
#             logger.debug(f"   edit skill link XPath: {skill['editSkillLinkXPath']}")
        
#         # Save skills to a JSON file
#         with open('linkedin_skills_detailed.json', 'w') as f:
#             json.dump(skills, f, indent=2)
#         logger.info("Detailed skills information saved to 'linkedin_skills_detailed.json'")
#     else:
#         logger.warning("No skills found.")
#         capture_screenshot(driver, "skills_not_found")
#         print_page_source(driver)

#     return skills

def click_edit_skill_link(driver, skill_element):
    """ Finds and clicks the edit link for the given skill_element and returns True if successful. """
    try:
        edit_skill_link = skill_element.find_element(By.XPATH, ".//a[contains(@id, 'navigation-add-edit-deeplink-edit-skills')]")
        edit_skill_link.click()
        logger.info(f"Clicked edit link for skill")
        return True
    except Exception as e:
        logger.error(f"Error clicking edit link for skill: {str(e)}")
        return False

def delete_existing_skills_file():
    file_name = "linkedin_skills_data.json"
    try:
        if os.path.exists(file_name):
            os.remove(file_name)
            logger.info(f"Deleted existing {file_name}")
        else:
            logger.info(f"{file_name} does not exist. No deletion needed.")
    except Exception as e:
        logger.error(f"Error deleting {file_name}: {str(e)}")

def append_skill_data(skill_data):
    file_name = "linkedin_skills_data.json"
    try:
        # Read existing data
        if os.path.exists(file_name):
            with open(file_name, 'r') as file:
                existing_data = json.load(file)
        else:
            existing_data = []
        
        # Append new data
        existing_data.append(skill_data)
        
        # Write updated data back to file
        with open(file_name, 'w') as file:
            json.dump(existing_data, file, indent=2)
        
        logger.info(f"Appended skill data for '{skill_data.get('name', 'Unknown')}' to {file_name}")
    except Exception as e:
        logger.error(f"Error appending skill data to {file_name}: {str(e)}")


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
    
    delete_existing_skills_file()
    
    try:
        login(driver, email, pswd)
        go_to_skills_page(driver, username)
        
        print("Current URL:", driver.current_url)
        
        skill_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'pvs-list__item--line-separated')]")
        logger.info(f"found {len(skill_elements)} skills")
        
        for skill_element in skill_elements:
            if click_edit_skill_link(driver, skill_element):
                skill_name = skill_element.find_element(By.XPATH, ".//span[contains(@class, 't-14')]").text
                logger.info(f"Processing skill: {skill_name}")
                skill_data = process_skill_modal(driver, skill_name)
                if skill_data is None:
                    logger.warning(f"Failed to process skill: {skill_name}")
                    continue;
                append_skill_data(skill_data)
                close_skill_modal(driver)
                
                # append skill_data to 'linkedin_skills_data.json'
                
            else:
                logger.warning("Failed to click edit skill link")
        
    
    
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        capture_screenshot(driver, "error_state")
        print_page_source(driver)
    
    finally:
        driver.quit()

if __name__ == "__main__":
    main()