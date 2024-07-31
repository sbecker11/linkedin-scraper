import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv

def login(driver, username, password):
    driver.get("https://www.linkedin.com/login")
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)  # Wait for login to complete

def get_skills_and_items(driver):
    driver.get("https://www.linkedin.com/in/shawnbecker/details/skills/")
    time.sleep(5)  # Wait for page to load

    skills_data = []

    # Find all skill elements
    skill_elements = driver.find_elements(By.CSS_SELECTOR, ".artdeco-list__item")

    for skill in skill_elements:
        skill_name = skill.find_element(By.CSS_SELECTOR, ".t-bold").text.split('\n')[0].strip()
        
        # Click edit button
        edit_button_parent = driver.find_element(By.CSS_SELECTOR, f"svg[aria-label='Edit {skill_name}']")
        driver.execute_script("arguments[0].click();", edit_button_parent)
        time.sleep(2)  # Wait for modal to open

        selected_items = []

        # Check each section
        sections = ["Experience", "Education", "Licenses & certifications", "Projects", "Patents"]
        for section in sections:
            try:
                section_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, f"//h3[text()='{section}']"))
                )
                items = section_element.find_elements(By.XPATH, "./following-sibling::ul/li")
                
                for item in items:
                    checkbox = item.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                    if checkbox.is_selected():
                        item_text = item.find_element(By.CSS_SELECTOR, "label").text
                        selected_items.append({"section": section, "item": item_text})
            except TimeoutException:
                print(f"Section '{section}' not found for skill '{skill_name}'")

        # Close the modal
        close_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
        driver.execute_script("arguments[0].click();", close_button)
        time.sleep(2)  # Wait for modal to close

        skills_data.append({"skill": skill_name, "selected_items": selected_items})

    return skills_data

def main():
    
    username = os.getenv("LINKEDIN_USERNAME")
    password = os.getenv("LINKEDIN_PASSWORD")

    driver = webdriver.Chrome()  # Make sure you have ChromeDriver installed and in PATH
    try:
        login(driver, username, password)
        skills_data = get_skills_and_items(driver)

        # Save data to JSON file
        with open("profile-skills-items.json", "w") as f:
            json.dump(skills_data, f, indent=2)

        print("Data saved to profile-skills-items.json")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
