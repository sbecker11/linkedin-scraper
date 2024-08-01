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
    

def get_skills(driver):
    print("Attempting to extract skills...")
    
    # Wait for the skills section to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//section[contains(@class, 'artdeco-card')]"))
        )
    except TimeoutException:
        print("Timeout waiting for skills section to load.")
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

    # Extract skills using JavaScript, focusing on elements with both skill text and edit button
    skills = driver.execute_script("""
        var skillContainers = document.querySelectorAll('div.display-flex.flex-row.justify-space-between');
        return Array.from(skillContainers).map(container => {
            var skillElement = container.querySelector('a[data-field="skill_page_skill_topic"] span[aria-hidden="true"]');
            var editButton = container.querySelector('a[id^="navigation-add-edit-deeplink-edit-skills"]');
            if (skillElement && editButton) {
                return skillElement.textContent.trim();
            }
            return null;
        }).filter(skill => skill);
    """)

    if skills:
        print(f"Found {len(skills)} skills:")
        for i, skill in enumerate(skills, 1):
            print(f"{i}. {skill}")
        
        # Save skills to a JSON file
        with open('linkedin_skills.json', 'w') as f:
            json.dump(skills, f, indent=2)
        print("Skills saved to 'linkedin_skills.json'")
    else:
        print("No skills found.")
        capture_screenshot(driver, "skills_not_found")
        print_page_source(driver)

    return skills

def clean_skill_text(text):
    # Remove any text related to endorsements or assessments
    text = re.sub(r'\d+\s+endorsements?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Passed LinkedIn Skill Assessment', '', text, flags=re.IGNORECASE)
    # Remove any text in parentheses (often contains additional info we don't want)
    text = re.sub(r'\s*\([^)]*\)', '', text)
    return text.strip()


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
        else:
            print("Failed to extract any skills.")
        
        # Capture final state
        capture_screenshot(driver, "final_state")
        print_page_source(driver)
    
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        capture_screenshot(driver, "error_state")
        print_page_source(driver)
    
    finally:
        driver.quit()

if __name__ == "__main__":
    main()