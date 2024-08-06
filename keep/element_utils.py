from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import ElementNotInteractableException
import logging
logger = logging.getLogger(__name__)

def get_element_info(driver, element):
    try:
        element_info = driver.execute_script("""
            var el = arguments[0];
            var rect = el.getBoundingClientRect();
            return {
                tagName: el.tagName,
                id: el.id,
                className: el.className,
                textContent: el.textContent.trim().substring(0, 50),
                isDisplayed: el.offsetParent !== null,
                location: {
                    x: rect.left,
                    y: rect.top
                },
                size: {
                    width: rect.width,
                    height: rect.height
                }
            };
        """, element)
        return element_info
    except WebDriverException as e:
        return f"Error getting element info: {str(e)}"

def get_element_attributes(driver, element):
    try:
        attributes = driver.execute_script("""
            var items = {};
            for (index = 0; index < arguments[0].attributes.length; ++index) {
                items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value
            };
            return items;
        """, element)
        return attributes
    except WebDriverException as e:
        return f"Error getting element attributes: {str(e)}"

def get_element_properties(driver, element, only_own_properties=False):
    try:
        properties = driver.execute_script("""
            var items = {};
            var obj = arguments[0];
            var onlyOwn = arguments[1];
            for (var prop in obj) {
                if (!onlyOwn || obj.hasOwnProperty(prop)) {
                    try {
                        items[prop] = obj[prop] !== null ? obj[prop].toString() : 'null';
                    } catch (e) {
                        items[prop] = "Cannot convert to string";
                    }
                }
            }
            return items;
        """, element, only_own_properties)
        return properties
    except WebDriverException as e:
        return f"Error getting element properties: {str(e)}"

def find_element_by_unique_xpath(driver, xpath, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return element
    except TimeoutException:
        return f"Element with XPath '{xpath}' not found within {timeout} seconds"
    except NoSuchElementException:
        return f"Element with XPath '{xpath}' not found in the document"

def find_child_element_by_relative_xpath(parent_element, child_xpath):
    try:
        child_element = parent_element.find_element(By.XPATH, child_xpath)
        return child_element
    except NoSuchElementException:
        logger.error(f"Child element with XPath '{child_xpath}' not found under the parent element")
        return None

def find_child_element_by_relative_id(parent_element, id_pattern):
    try:
        child_element = parent_element.find_element(By.XPATH, f".//*[contains(@id, '{id_pattern}')]")
        return child_element
    except NoSuchElementException:
        logger.error(f"Child element with ID containing '{id_pattern}' not found under the parent element")
        return None
    
def is_clickable_anchor(driver, element):
    try:
        # Check if the element is an anchor tag
        if element.tag_name.lower() != 'a':
            logger.warning(f"Element is not an anchor tag. Tag name: {element.tag_name}")
            return False

        # Check if the element has an href attribute
        href = element.get_attribute('href')
        if not href:
            logger.warning("Anchor tag does not have an href attribute")
            return False

        # Check if the element is displayed and enabled
        if not (element.is_displayed() and element.is_enabled()):
            logger.warning("Anchor tag is not displayed or not enabled")
            return False

        # Check if the element is clickable (in the DOM and visible)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, f".//*[@id='{element.get_attribute('id')}']")))

        return True

    except StaleElementReferenceException:
        logger.error("Element is stale (no longer attached to the DOM)")
        return False
    except ElementNotInteractableException:
        logger.error("Element is not interactable")
        return False
    except Exception as e:
        logger.error(f"Error checking if element is clickable anchor: {str(e)}")
        return False
