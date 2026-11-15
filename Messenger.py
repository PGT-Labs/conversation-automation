from HtmlUtilities import *
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

msg_div_class = 'x6prxxf x1fc57z9 x1yc453h x126k92a'

def LoginMessenger(driver,email,password,passCookies):
    # Visit messenger.com
    driver.get("https://www.messenger.com/login.php")
    wait = WebDriverWait(driver, 10)
    wait.until(page_fully_loaded)

    if (passCookies == False):
        print("RECHERCHE DU BOUTON DE REFUS DES COOKIES")
        # Cookies refusal
        button = None
        partial_class_name = "_42ft _4jy0 _alf7 _4jy3 _4jy1"
        elements = wait.until(find_elements_by_partial_class_name(partial_class_name))
        print("FILTRAGE DES ELEMENTS DIV")
        # Filter the list to find only <div> elements
        btn_elements = [element for element in elements if element.tag_name == 'button']
        print("LISTE D'ELEMENTS DIV:",btn_elements)
        # Now you can work with the found <div> elements
        for btn_element in btn_elements:
            print(btn_element.text)
        if (len(btn_elements) == 1):
            button = btn_elements[0]

        print("BOUTON REFUS DES COOKIES TROUVE:",button)

        if button is None:
            print("button not found yet")
            try:
                button = driver.find_element_by_xpath("//button[@title='Refuser les cookies optionnels']")
            except Exception as e:
                print(e)
            if button is None:
                flash('Cookies refusal button not found', 'error')
                print("exiting")
                exit()
        button.click()
    
    # Find the username and password input elements by their attributes
    email_input = driver.find_element_by_id("email")
    password_input = driver.find_element_by_id("pass")
    continue_button = driver.find_element_by_id("loginbutton")
    
    # Enter the username and password
    email_input.send_keys(email)
    password_input.send_keys(password)
    time.sleep(2)
    continue_button.click()

def ListMarketplaceConversations(driver,session):
    print("  LIST MARKETPLACE CONVERSATIONS")
    # THE DRIVER MUST BE FOCUSED ON MESSENGER.COM/MARKETPLACE
    url = driver.current_url
    print("    Current url:",url)
    if not ("https://www.messenger.com/marketplace" in url):
        driver.get("https://www.messenger.com/marketplace/")
        time.sleep(2)

    wait = WebDriverWait(driver, 10)
    
    # Look for links
    links = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@href, "marketplace/t")]')))

    print("    ",len(links),"links found")

    # Iterate through the links to isolate marketplace conversations
    message_class = "x6prxxf x1fc57z9 x1yc453h x126k92a"
    msg_span_class = "x1lliihq x193iq5w x6ikm8r x10wlt62 xlyipyv xuxw1ft x1j85h84"
    bold_msg_span_class = "x6s0dn4 x78zum5 x193iq5w xeuugli xg83lxy"

    conversation_urls = []
    k = 0
    NbRetries = 3
    Success = False
    while (Success == False) and (k < NbRetries):
        try:
            for link in links:
                link_text = link.text
                link_url = link.get_attribute("href")
                if "marketplace/t" in link_url:
                    print("  ",link_url)
                    conversation_urls.append(link_url)
                    if not link_url in session['conversations']:
                        print("    New conversation:")
                        print("    texte du lien:",link_text,"fin texte")
                        convo_msgs = link.find_elements_by_class_name(message_class)
                        print("      ",len(convo_msgs),"messages")

                        span_elements = link.find_elements_by_tag_name("span")
                        filtered_span_elements = [span for span in span_elements if msg_span_class in span.get_attribute("class")]

                        # STORING CONVERSATION DATA: URL => (TITLE, AGE, LINK)        
                        if (len(filtered_span_elements) >= 2):
                            convo_name = link_text.split("\n")[0]
                            convo_age = filtered_span_elements[-1].text
                            print("      last message",convo_age,"ago")
                            session['conversations'][link_url] = [convo_name,convo_age,link_text,[],int(session['bot-active'])]
            Success = True
        except Exception as e:
            print(e)
        k += 1

    deleted_conversations = []
    for link_url in session['conversations']:
        if link_url not in conversation_urls:
            print("Conversation",link_url,"deleted from Messenger")
            deleted_conversations.append(link_url)
    for link_url in deleted_conversations:    
        del session['conversations'][link_url]

    return session['conversations']

def ReadMessengerConversation(driver,session,link_url):
    print("  READ MESSENGER CONVERSATION")
    # STORING CONVERSATION MESSAGES
    for k in range(3):
        messages = []
        print("    Messenger messages load attempt",k)
        wait = WebDriverWait(driver, 10)
        try:
            div_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[class*="{}"]'.format(msg_div_class))))        
            print("     ",len(div_elements)," div elements found")
            for div in div_elements:
                div_class = div.get_attribute('class')
        except Exception as e:
            print("     Conversation messages collection failed:")
            print(e)
        time.sleep(4)
        print("    ",len(messages),"collected messages vs",len(session['conversations'][link_url][3]),"known")
        if (len(messages) > len(session['conversations'][link_url][3])):
            break       

    print("    ",messages)

    return messages

def RespondInMessenger(driver,messages):
    print("  SENDING CHATBOT RESPONSE IN MESSENGER")
    # Clear any existing text and send new text to the editable element
    for message in messages:
        msgSent = False
        nbRetries = 0
        print("    ",message)
        while (msgSent == False) and (nbRetries < 5):
            try:
                # Locate the parent div (the container)
                wait = WebDriverWait(driver, 10)
                parent_div = wait.until(EC.visibility_of_element_located((By.XPATH, '//div[@contenteditable="true"]')))
                # Locate the actual editable element within the parent div (child p element)
                editable_element = wait.until(find_elements_by_tag_name_under_parent(parent_div,'p'))[0]
                editable_element.clear()
                time.sleep(2)
                editable_element.send_keys(message)
                time.sleep(2)
                editable_element.send_keys(Keys.ENTER)
                time.sleep(2)
                msgSent = True
            except Exception as e:
                print("Couldn't send bot response:",e)
                time.sleep(4)
            nbRetries += 1
