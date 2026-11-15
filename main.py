from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from Messenger import *
from BotPress import *
import hashlib
import json
import os

app = Flask(__name__)
# app.secret_key = os.urandom(24)  # Used for session management (change this in production)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False # Session expires when the browser is closed
app.config['SESSION_USE_SIGNER'] = True
app.config['SECRET_KEY'] = os.urandom(24)

drivers = {}

sessions_db = {} # [session.sid] => (dashboard_running,counter,checked_conversations)

f_sessions = {} # In replacement of Flask-session for the time being

BotUrl = "https://mediafiles.botpress.cloud/6b0702c4-fea5-475d-868d-ee9c48b2d30c/webchat/bot.html"

# Initialize session data
@app.route('/')
def login():
    print("LOGIN ROUTE CALLED")
    '''session['conversations'] = [] # List of 'convos' dict() used to display conversations on the dashboard'''
    '''session['chat-tabs'] = dict() # [BotPress chats url link] => driver tab
    session['bot-active'] = False
    session['bot-activation-time'] = None
    session['conversations'] = {} # [link url] => [name,age,link text,messages,botHandled]
    session['dashboard_running'] = False'''
    '''with app.app_context():
        db.session.add(UserSession(id=session.sid, dashboard_running=False, counter=0, checked_conversations = {}))
        db.session.commit()'''
    '''global sessions_db
    sessions_db[session.sid] = [False,0,{}]'''
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    print("DASHBOARD ROUTE CALLED")
    global drivers, sessions_db, f_sessions
    session_id = request.args.get('session_id')
    f_sessions[session_id]['dashboard_running'] = True
    for k in f_sessions[session_id]:
        print("  ",k,":",f_sessions[session_id][k])
    '''
    stored_session = UserSession.query.get(session.sid)
    if stored_session:
        stored_session.dashboard_running = True
        stored_session.counter += 1
        db.session.commit()
    else:
        stored_session = UserSession(id=session.sid, dashboard_running=True, counter=1, checked_conversations = {})
        db.session.add(stored_session)
        db.session.commit()
    '''
    sessions_db[session_id][0] = True
    sessions_db[session_id][1] += 1
    stored_session = sessions_db[session_id]
    dashboard_running, counter, checked_conversations = stored_session
    chatbot_active = f_sessions[session_id].get('bot-active',False)
    chatbot_text = 'Chatbot Active' if chatbot_active else 'Activate Chatbot'
    print("  Reloaded /dashboard - bot active:",chatbot_active,'- counter:',counter)
    driver = drivers[session_id]
    f_sessions[session_id]['conversations'] = ListMarketplaceConversations(driver,f_sessions[session_id])
    print("  Current number of conversations:",len(f_sessions[session_id]['conversations']))
    print("  Conversations checked status:",checked_conversations)
    if (chatbot_active == True) and (counter % 4 == 0):
        print("  Running conversations scan") 
        for link_url in f_sessions[session_id]['conversations']:
            title, age, link, messages, botHandled = f_sessions[session_id]['conversations'][link_url]
            if link_url not in checked_conversations:
                print("  Storing conversation checked status:",link_url,botHandled)
                checked_conversations[link_url] = botHandled
            print(title,"- handled by bot:",botHandled)
            if (botHandled == False):
                continue
            # Open Messenger conversation in browser
            driver.switch_to.window(driver.window_handles[0]) # everything Messenger => first tab
            driver.get(link_url)
            time.sleep(2)
            wait_for_load = WebDriverWait(driver, 10)
            wait_for_load.until(page_fully_loaded)
            # Get conversation messages
            conversationMessages = ReadMessengerConversation(driver,f_sessions[session_id],link_url)
            f_sessions[session_id]['conversations'][link_url][3] = conversationMessages
            if (len(conversationMessages) == 0):
                print("  NO MESSAGES")
                continue
            elif (conversationMessages[-1][0] == "bot"):
                print("  NO NEW USER MESSAGES")
                continue
            print("  NEW USER MESSAGES")
            # NEW USER MESSAGE: STAY FOCUSED ON THIS CONVERSATION FOR A WHILE
            NewUserMessage = True
            ConversationLastMessageTime = time.time()
            ConversationFocusStopTime = ConversationLastMessageTime + 300 # 300 seconds (5 minutes)
            ConversationFocus = True

            while (ConversationFocus == True):
                stored_session = sessions_db[session_id]
                bot_handled = stored_session[2][link_url]
                print("  Focus conversation checked status:",link_url,bot_handled)
                if (bot_handled == 1): # box unchecked
                    break
                if (NewUserMessage == True):
                    # FEED CONVERSATION TO THE BOT
                    print("    Conversation: ",f_sessions[session_id][link_url][0],"is being sent to the bot")

                    # Get browser to the BotPress chat tab
                    if link_url in f_sessions[session_id]['chat-tabs']:
                        driver.switch_to.window(f_sessions[session_id]['chat-tabs'][link_url])
                    else:
                        # Open a new tab using JavaScript
                        driver.execute_script("window.open('', '_blank');")
                        # Switch to the newly opened tab
                        driver.switch_to.window(driver.window_handles[-1])
                        # Store tab window handle
                        f_sessions[session_id]['chat-tabs'][link_url] = driver.window_handles[-1]
                        # Navigate to the bot page URL in the new tab
                        driver.get(BotUrl)
                        time.sleep(2)
                        wait_for_load = WebDriverWait(driver, 10)
                        wait_for_load.until(page_fully_loaded)
                    
                    time.sleep(2)
                    # Send user message to the chatbot
                    SendUserMessageToBotPress(driver,conversationMessages)
                    
                    time.sleep(3)
                    # Read chatbot response
                    botResponse = []
                    botResponseCycle = -1 # iteration at which a response is first observed
                    cyclesLimit = 8
                    for k in range(8):
                        print("    Cycle",k)
                        chatMessages = ReadBotPressConvoMessages(driver)

                        sender, text = chatMessages[-1]
                        if (sender == "bot"): # Bot has responded
                            print(sender,text)
                            # Wait for potential additional message
                            time.sleep(3)
                            chatMessages = ReadBotPressConvoMessages(driver)
                            # Isolate bot response
                            botResponse = []
                            m = -1
                            sender, text = chatMessages[m]
                            while (sender == "bot"):
                                botResponse = [text]+botResponse
                                m -= 1
                                sender, text = chatMessages[m]                               
                                
                            print("    Bot responded with",len(botResponse),"messages:")
                            print("    ",botResponse)

                            if (botResponseCycle == -1):
                                if (len(botResponse) > 0):
                                    botResponseCycle = k
                                    cyclesLimit = k+2
                                    print("      Stop at cycle",cyclesLimit)
                        # Enough time was left for the chatbot to complete response
                        if (botResponseCycle != -1) and (k >= cyclesLimit):
                            break
                        time.sleep(3)

                # Switch back to the first tab: Messenger
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(5)
                if (len(botResponse) != 0): # BOT RESPONSE => POST IT TO MESSENGER
                    RespondInMessenger(driver,botResponse)
                    time.sleep(3)
                    botResponse = []

                # Wait for user response
                NewUserMessage = False
                for k in range(15):
                    # Get current conversation messages
                    messages = ReadMessengerConversation(driver,f_sessions[session_id],link_url)
                    f_sessions[session_id]['conversations'][link_url][3] = messages
                    print("      last message:",messages[-1])
                    if (messages[-1][0] == "user"): # User has responded: Reset conversation focus time window
                        NewUserMessage = True
                        ConversationLastMessageTime = time.time()
                        ConversationFocusStopTime = ConversationLastMessageTime + 90 # 300 seconds (5 minutes)
                        conversationMessages = messages
                        break

                # Evaluate if conversation focus time window has expired 
                CurrentTime = time.time()
                if (CurrentTime > ConversationFocusStopTime):
                    ConversationFocus = False

    drivers[session_id] = driver

    f_sessions[session_id]['dashboard_running'] = False
    
    sessions_db[session_id][0] = False
    sessions_db[session_id][2] = checked_conversations
            
    return render_template('dashboard.html',session_id = session_id,chatbot_active=chatbot_active,
                           chatbot_text=chatbot_text,conversations=f_sessions[session_id]['conversations'])

@app.route('/session', methods=['POST'])
def testSession():
    print("SESSION ROUTE CALLED")
    print("  POST request arguments:",request.args)
    session_id = request.args.get('session_id')
    for k in f_sessions[session_id]:
        print("  ",k,":",f_sessions[session_id][k])
    redirect_url = url_for('dashboard') + '?session_id=' + session_id
    return redirect(redirect_url)

@app.route('/running', methods=['POST'])
def running():
    print("RUNNING ROUTE CALLED")
    print("  POST request arguments:",request.args)
    session_id = request.args.get('session_id')
    print("  Dashboard running:",sessions_db[session_id][0])

    return jsonify({'dashboard_running': sessions_db[session_id][0]})

@app.route('/get_conversations', methods=['POST'])
def get_conversations():
    print("GET CONVERSATIONS ROUTE CALLED")
    print("  POST request arguments:",request.args)
    session_id = request.args.get('session_id')
    driver = drivers[session_id]
    global f_sessions
    if (sessions_db[session_id][0] == False): # dashboard_running
        f_sessions[session_id]['conversations'] = ListMarketplaceConversations(driver,f_sessions[session_id])
        
    return jsonify(f_sessions[session_id]['conversations'])

@app.route('/toggle', methods=['POST'])
def toggle():
    print("TOGGLE ROUTE CALLED")
    print("  POST request arguments:",request.args)
    # Toggle the boolean value (e.g., chatbot_active)
    session_id = request.args.get('session_id')
    global f_sessions
    f_sessions[session_id]['bot-active'] = not f_sessions[session_id]['bot-active']
    print("Chatbot active status:",f_sessions[session_id]['bot-active'])
    if (f_sessions[session_id]['bot-active'] == True):
        f_sessions[session_id]['bot-activation-time'] = time.time()
    redirect_url = url_for('dashboard') + '?session_id=' + session_id
    return redirect(redirect_url)

@app.route('/update_bot_handled', methods=['POST'])
def update_bot_handled():
    print("UPDATE BOT HANDLED ROUTE CALLED")
    print("  POST request arguments:",request.args)
    link_url = request.args.get('linkUrl')
    bot_handled = int(request.args.get('botHandled'))
    session_id = request.args.get('session_id')
    global f_sessions, sessions_db
    # Update the botHandled value for the conversation in session
    f_sessions[session_id]['conversations'][link_url][4] = bot_handled
    # Update it in the database
    sessions_db[session_id][2][link_url] = bot_handled
    print("  updated conversations checked status:",sessions_db[session_id][2])

    return '', 204  # 204 means "No Content"

@app.route('/login', methods=['POST'])
def login_post():
    print("LOGIN POST ROUTE CALLED")
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Create Chrome options with headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Enable headless mode

    # Initialize the WebDriver with the headless options
    driver = webdriver.Chrome(ChromeDriverManager().install())#,options=chrome_options)

    LoginSuccessful = False
    NbAttempts = 0
    passCookies = False
    while (LoginSuccessful == False):
        try:
            LoginMessenger(driver,email,password,passCookies)
            time.sleep(3)
            driver.get("https://www.messenger.com/marketplace/")
            wait_for_load = WebDriverWait(driver, 10)
            wait_for_load.until(page_fully_loaded)
            time.sleep(2)
            url = driver.current_url
            print("Current url:",url)
            if ("https://www.messenger.com/marketplace" in url):
                LoginSuccessful = True
        except Exception as e:
            print("Login messenger error:",e)
            time.sleep(5)
        NbAttempts += 1
        if (NbAttempts >= 5):
            passCookies = True

    time.sleep(4)

    # SESSION MANAGEMENT
    timestamp = str(int(time.time()))
    session_identifier = email + timestamp
    session_id = hashlib.sha256(session_identifier.encode()).hexdigest()
    
    f_sessions[session_id] = {}
    f_sessions[session_id]['chat-tabs'] = dict() # [BotPress chats url link] => driver tab
    f_sessions[session_id]['bot-active'] = False
    f_sessions[session_id]['bot-activation-time'] = None
    f_sessions[session_id]['dashboard_running'] = False
    f_sessions[session_id]['conversations'] = {}
    # Initial listing of marketplace conversations
    f_sessions[session_id]['conversations'] = ListMarketplaceConversations(driver,f_sessions[session_id])# [link url] => [name,age,link text,messages,botHandled]
    time.sleep(2)
    
    NbConversations = len(f_sessions[session_id]['conversations'])
    print(NbConversations," conversations found")

    global sessions_db
    sessions_db[session_id] = [False,0,{}]
    for linkUrl in f_sessions[session_id]['conversations']:
        sessions_db[session_id][2][linkUrl] = 0

    global drivers
    drivers[session_id] = driver

    print("Database checked conversations:",sessions_db[session_id][2])

    # Close the WebDriver when done
    print("redirecting to dashboard")
    redirect_url = url_for('dashboard') + '?session_id=' + session_id
    return redirect(redirect_url) # url_for('dashboard'), session_id=session_id)

if __name__ == '__main__':
    app.run(debug=True)
