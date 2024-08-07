
import time
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.remote.webelement import WebElement
from bs4 import BeautifulSoup
from bs4.element import Tag
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
        logger.info("Entered email")
        
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        password_field.send_keys(pswd)
        logger.info("Entered password")
        
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        )
        login_button.click()
        logger.info("Clicked login button")
        
        # Wait for either the navigation bar or a security challenge
        WebDriverWait(driver, 20).until(
            EC.any_of(
                EC.presence_of_element_located((By.ID, "global-nav")),
                EC.presence_of_element_located((By.ID, "challenge-node"))
            )
        )
        
        # Check if there's a security challenge
        if "checkpoint/challenge" in driver.current_url:
            logger.info("Security challenge detected")
            # Handle the security challenge here
            # This is a placeholder - you'll need to implement the actual challenge handling
            challenge_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "input__email_verification_pin"))
            )
            # Assume you have a function to get the verification code
            def get_verification_code():
                # Implement the logic to get the verification code
                pass
            
            # ...
            
            verification_code = "123456"  # Replace with the actual logic to get the verification code
            challenge_input.send_keys(verification_code)
            
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "email-pin-submit-button"))
            )
            submit_button.click()
            logger.info("Submitted security challenge response")
        
        # Wait for the navigation bar to confirm successful login
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "global-nav"))
        )
        logger.info("Successfully logged in")
    except TimeoutException as e:
        logger.error(f"Timeout during login process: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise
    
def go_to_skills_page(driver, username) -> None:
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
    capture_page_source(driver, "skills_page.txt")
    logger.info(f"Current URL: {driver.current_url}")

def capture_screenshot(driver, filename) -> None:
    if not filename.endswith(".png"):
        raise ValueError("Filename must end with .png")
    driver.save_screenshot(f"{filename}")
    logger.info(f"Screenshot saved as {filename}")

def capture_page_source(driver, filename) -> None:
    if not filename.endswith(".txt"):
        raise ValueError("Filename must end with .txt")
    with open(filename,"w") as file:
        file.write(driver.page_source)
    logger.info(f"Page source saved as {filename}")

def scroll_to_skill(driver, skill_name):
    try:
        # Locate the skill element by its name
        skill_element = driver.find_element_by_xpath(f"//span[text()='{skill_name}']")
        
        # Get the position of the skill element
        skill_position = driver.execute_script("return arguments[0].getBoundingClientRect().top + window.scrollY;", skill_element)
        
        # Scroll to the skill element's position
        driver.execute_script("window.scrollTo(0, arguments[0]);", skill_position)
        time.sleep(1)
        
        logger.info(f"{skill_name} is now in view.")
    except Exception as e:
        logger.error(f"An error occurred while scrolling to {skill_name}: {e}")


def process_skill_modal(driver, skill_name):
    try:
        # scroll skill listing page to make this skill_name visible
        scroll_to_skill(driver, skill_name)
        time.sleep(3)          

        # prompt user to click the edit skill link from the skill listing page
        logger.info(f"click {skill_name}")
        
        # now pause for up to 15 seconds for user to click the edit_skill_link 
        # and the edit_skill_modal appears
        # the modal has "pe-edit-form-page__modal" as one of its class names
        edit_skill_modal = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "pe-edit-form-page__modal")) 
        )
        # wait until the modal appears
        time.sleep(5)          
        
        # scroll vertically to the bottom of the modal to load all selected items
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        
        # find all selected items in the modal
        selected_items = edit_skill_modal.find_elements(By.CLASS_NAME, "selected-item")
        logger.info(f"found {len(selected_items)} selected items")
              
        # scroll to the top to make the dismiss button visible
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(5)
        
        # the modal's dismiss button has aria-label="Dismiss" 
        dismiss_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Dismiss']")) 
        )
        # if dismiss is not found in modal then raise an exception and exit
        if dismiss_button is None:
            raise Exception("dismiss_button not found in modal")
        dismiss_button.click()
        
        logger.info(f"Successfully finished process_skill_modal for skill_name: {skill_name}")
        return selected_items
        
    except Exception as e:
        logger.error(f"Error process_skill_modal for skill_name: {skill_name} exception:{str(e)}")    

def find_skill_containers(driver):
    logger.info("Attempting to find all skill containers...")
    skill_containers = []
    skills = []
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
                # Step 1: Find the div with class "pvs-navigation__icon"
                try:
                    icon_div = container.find_element(By.XPATH, ".//div[@class='pvs-navigation__icon']")
                    if icon_div is None:
                        logger.warn(f"Could not find pvs-navigation__icon div for container ID: {container.get_attribute('id')}")
                    else:
                        logger.info(f"Found pvs-navigation__icon div for container ID: {container.get_attribute('id')}")
        
                        # Step 2: Find the svg element within the div
                        svg_element = None
                        try:
                            svg_element = icon_div.find_element(By.XPATH, "./svg[@aria-label]")
                        except NoSuchElementException:
                            logger.warning("Could not find SVG element with aria-label in icon_div")
 
                        if svg_element is None:
                            # look for teh svg within  the innerHTML of the div
                            icon_div_innerHtml = icon_div.get_attribute('innerHTML')
                            pattern = r'aria-label="Edit\s*(.*?)"'
                            match = re.search(pattern, icon_div_innerHtml)

                            if match:
                                logger.info(f"Found pattern: {repr(pattern)} in icon_div_innerHtml")

                                skill_name = match.group(1)
                                if skill_name is None:
                                    logger.warning(f"Could not find skill_name in pattern: {repr(pattern)}")
                                else:
                                    logger.info(f"!!! Found skill_name: [{skill_name}]")
                                    skills.append(skill_name)
                                    selected_items = process_skill_modal(driver, skill_name)
                                    logger.info(f"skill:{skill_name} has {len(selected_items)} selected_items")
                                    

                            else:
                                logger.warning(f"Could not find pattern: {repr(pattern)} in icon_div_innerHtml")
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
                                skills.append(skill_name)
                                selected_items = process_skill_modal(driver, skill_name)
                                logger.info(f"skill:{skill_name} has {len(selected_items)} selected_items")


                except NoSuchElementException:
                    logger.warning(f"find_element pvs-navigation__icon div fo skill container Skill: {skill_name} raised NoSuchElementException")
                except Exception as e:
                    logger.error(f"Error processing skill:{skill_name} : {str(e)}")
            
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

    logger.info(f"Total skills found {len(skills)}")
    return skills

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
        logger.info("Login successful, proceeding to skills page")
        go_to_skills_page(driver, username)
        capture_page_source(driver, "after_go_to_skills_page.txt")

        skill_containers = find_skill_containers(driver)
        logger.info(f"Found {len(skill_containers)} skill containers")
        capture_page_source(driver, f"after-found-{len(skill_containers)}-skill-containers.txt")
    
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        capture_page_source(driver, "error_state.txt")
    
    finally:
        logger.info("Quitting webdriver")
        driver.quit()
        
if __name__ == "__main__":
    main()
