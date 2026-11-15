from HtmlUtilities import *
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def SendUserMessageToBotPress(driver,conversationMessages):
    print("  Sending user messages to Botpress chat")
    # Switch to the iframe containing all conversation elements
    iframe = driver.find_element_by_id('bp-web-widget')
    driver.switch_to.frame(iframe)

    # Wait for the text input area to be visible and interactable within the iframe
    wait = WebDriverWait(driver, 10)
    
    # Find the textarea element by its ID
    textarea = wait.until(EC.presence_of_element_located((By.ID, "input-message")))

    # Find the button element by its ID
    button = wait.until(EC.presence_of_element_located((By.ID, "btn-send")))

    # Isolate last conversation messages if it was sent by a prospect (new message)
    userMessages = []
    for msg in reversed(conversationMessages): 
        sender, text = msg
        if (sender == "user"):
            userMessages = [text]+userMessages
        else:
            break
        
    # Send user messages to the bot
    for message in userMessages:
        textarea.send_keys(message)
        button.click()
        time.sleep(2)

def ReadBotPressConvoMessages(driver):
    print("  Read BotPress chat messages")
    # Browser must be focused on a botpress chat prior to calling this function

    wait = WebDriverWait(driver, 10)
    chat_msgs = []
    
    # Wait for all message containers to appear
    message_containers = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[class*="bpw-message-big-container"]'))
    )

    # Now, select the chat bubbles inside the container
    msg_bubble_div_class = "bpw-bubble-undefined bpw-chat-bubble bpw-bubble-text"
    for container in message_containers:
        # Get the full class name of the container
        full_class_name = container.get_attribute("class")
        # Check if it's from the user or the bot based on class name
        if "bpw-from-user" in full_class_name:
            sender = "user"
        elif "bpw-from-bot" in full_class_name:
            sender = "bot"
        print("   ",sender,"message container")
        '''chat_bubbles = container.find_elements(By.CSS_SELECTOR, 'div[class*="{}"]'.format(msg_bubble_div_class))'''
        chat_bubbles = WebDriverWait(container, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[class^="bpw-bubble-undefined bpw-chat-bubble"]'))
        )
        '''
        # Find all <div> elements with class "bpw-chat-bubble-content"    
        msg_bubble_div_class = "bpw-bubble-undefined bpw-chat-bubble bpw-bubble-text"
        chat_bubbles = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[class*="{}"]'.format(msg_bubble_div_class))))
        '''
        # Iterate through each chat bubble and get the text content of <p> elements
        print("    ",len(chat_bubbles),"chat bubbles")
        for chat_bubble in chat_bubbles:
            chat_bubble_class = chat_bubble.get_attribute('class')
            # Skip irrelevant bubble types
            if 'bpw-bubble-typing' in chat_bubble_class:
                continue
            
            # Find <span> elements within the current chat bubble
            bubble_text = ""
            if ("bpw-bubble-text" in chat_bubble_class):
                # Find <p> elements within the current chat bubble
                p_elements = wait.until(find_elements_by_tag_name_under_parent(chat_bubble,'p'))
                print("    ",len(p_elements),"p elements in text bubble")
                p_element = p_elements[0]
                bubble_text = p_element.text                
            elif ("bpw-bubble-single-choice" in chat_bubble_class):
                bubble_text = chat_bubble.find_element(By.CSS_SELECTOR, 'div.bpw-chat-bubble-content div').text
            else:
                print("    Unhandled bubble class:",chat_bubble_class)
            
            # Iterate through <p> elements and print their text content
            for p_element in p_elements:
                chat_msgs.append((sender,bubble_text))
            
    return chat_msgs
