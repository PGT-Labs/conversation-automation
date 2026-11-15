from selenium.webdriver.common.by import By
import time

def page_fully_loaded(driver):
    return driver.execute_script("return document.readyState") == "complete"

def find_elements_by_tag_name(tag_name):
    return lambda driver: driver.find_elements(By.TAG_NAME, tag_name)  

def find_elements_by_tag_name_under_parent(parent, tag_name):
    return lambda driver: parent.find_elements(By.TAG_NAME, tag_name)  

def find_elements_by_partial_class_name(partial_class_name):
    return lambda driver: driver.find_elements(By.XPATH, f'//*[contains(@class, "{partial_class_name}")]')   
