"""
whatsapp_scraper.py

Author: Nic Mos
Date: 2025-05-04
Description: A Selenium-based scraper that logs into WhatsApp Web, identifies private 
chats, scrolls through message history, and exports messages to a JSON file for analysis.

Dependencies:
    - selenium
    - numpy
    - json
    - re
    - time
    - datetime
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
from datetime import datetime
from selenium.common.exceptions import StaleElementReferenceException
import re
import numpy as np
import json
from selenium.common.exceptions import TimeoutException


STARTING_MESSAGE = """Hello!! I'm a scraper that uses Selenium to save your messages.
You will be required to scan the QR code to log in to your WhatsApp account so I can gain access to your messages.
This scraper will find all the chats you have with your contacts and then save their messages to separate text files.
No group messages will be saved, as the purpose of this scraper is to archive personal conversations.
"""

def _has_element(parent, xpath):
    """
    Returns wether or not the HTML element is present 

    Args:
        parent (WebElement): The parent element that potentially contains the child node.
        xpath (str): The XPath expression used to find the child element.
    
    Returns:
        bool: True if the element exists, False otherwise.
    """
    try:
        parent.find_element(By.XPATH, xpath)
        return True
    except:
        return False

def is_private_chat(chat_name_div):
    """
    Returns wether or not the chat selsected is a private or group chat

    Args:
        chat_name_div (WebElement): The element of the chat that contains all the information about it
    
    Returns:
        bool: True if the chat is a private chat, False otherwise.
    """
    
    veiwable_msg_span = chat_name_div.find_element(By.XPATH, './/div[@class="_ak8k"]')
    profile_photo = chat_name_div.find_element(By.XPATH, './/div[@class="_ak8n"]')


    if _has_element(veiwable_msg_span, './/span[@dir="auto"]'):
        text = veiwable_msg_span.find_element(By.XPATH, './/span[@dir="auto"]').text.strip()
        if not text or (len(str(text)) == 0):
            return True
        if _has_element(veiwable_msg_span, './/span[@class="x1rg5ohu _ao3e"]'):
            # this is the element <You> or <+27 724 ...> before the message
            return False
        return True
    
    if _has_element(profile_photo, './/span[@data-icon="default-group"]'):
        return False

    if _has_element(veiwable_msg_span, './/span[contains(@title, "Group")]'):
        return False

    if _has_element(veiwable_msg_span, './/span[contains(@title, "group")]'):
        return False
    
    if _has_element(veiwable_msg_span, './/span[contains(@title, " changed to +")]'):
        return False

    return True

def find_scroll_speed(last_max, current_min, current_speed):
    """
    Returns the number of pixels, which is used to iteritevely update the scroll speed
    ensuring fast scrolling without loss of information

    Args:
        last_max (int): The number associated with the last veiwable chat before the scroll
        current_min (int): The number associated with the first veiwable chat after the scroll
        current_speed (int): the current speed of scrolling
    
    Returns:
        int: The updated speed for scrolling
    """
    if current_min < last_max:
        return current_speed + 50
    
    if current_min > last_max:
        return max(current_speed - 25, 25)

    else:
        return current_speed



def find_contact_names(driver):
    """
    Scans the WhatsApp chat list and returns a set of contact names for private (non-group) chats.

    Args:
        driver (WebDriver): The Selenium WebDriver instance controlling the browser.

    Returns:
        set: A set containing the names of all contacts with whom the user has private chats.
    """

    side_panel = driver.find_element(By.ID, "pane-side")
    last_height = 0
    count = 0

    #Identify how many chats the user has
    chat_list_div = driver.find_element(By.XPATH, '//div[@aria-label="Chat list" and @role="grid"]')
    number_of_chats = chat_list_div.get_attribute("aria-rowcount")
    print(f"\nYou have {number_of_chats} total chats!")

    set_of_names = set()
    max_height_of_scroll = 0
    current_speed = 150
    scroll_back_up = False

    while True:
        first_div = True
        prev_max_height = max_height_of_scroll
        current_min_height = 0
        current_height = driver.execute_script("return arguments[0].scrollTop", side_panel)

        #Find the list of chats visible 
        chat_name_divs = driver.find_elements(
            By.XPATH, '//div[contains(@class, "x10l6tqk xh8yej3 x1g42fcv")]'
        )

        for chat_name_div in chat_name_divs:
            try:
                style = chat_name_div.get_attribute("style")
                string_match = re.search(r'translateY\((\d+)px\)', style)
                if string_match:
                    px_height = int(string_match.group(1))
                else:
                    continue

                if px_height > max_height_of_scroll:
                    max_height_of_scroll = px_height

                if first_div:
                    current_min_height = px_height
                    first_div = False

                if not is_private_chat(chat_name_div):
                    continue

                # Get the private chat name
                name_span = chat_name_div.find_element(By.XPATH, './/span[@title]')
                chat_name = name_span.get_attribute("title")

                #search if the chat name is in the chat of names
                if chat_name not in set_of_names:
                    set_of_names.add(chat_name)
            
            except StaleElementReferenceException:
                continue

        if current_height == last_height:
            count += 1
        else:
            count = 0
        
        if count == 3 and not scroll_back_up:
            print("Bottom of visible chat logs reached! Scrolling back up to make sure "
                  "no chats have been missed!"
            )
            scroll_back_up = True

        elif count == 3 and scroll_back_up:
            break
            
        last_height = current_height

        #scroll down by 100 pixels | using javaScript to scroll; not action
        current_speed = find_scroll_speed(prev_max_height, current_min_height, current_speed)
        if not scroll_back_up:
            driver.execute_script(f"arguments[0].scrollTop += {current_speed}", side_panel)
        else:
            #if scrolling to top of chat from bottom -> must be negative
            driver.execute_script(f"arguments[0].scrollTop -= {current_speed}", side_panel)

        time.sleep(0.5)
    
    return set_of_names


def ensure_BMP_characters(element):
    """
    Removes non-BMP (Basic Multilingual Plane) characters such as certain emojis
    from the 'title' attribute of a web element, which is the name of the chat/contact. This is necessary because ChromeDriver
    only supports characters in the BMP (i.e., up to 16-bit code points).

    Args:
        element (WebElement): The element whose title attribute may contain emojis.

    Returns:
        str: The cleaned string containing only BMP characters.
    """

    try:
        raw = element.get_attribute("title")
        return ''.join(c for c in raw if ord(c) <= 0xFFFF)
    except Exception as e:
        print("[WARN] Could not read title:", e)
        return ""

def strip_non_bmp(text):
    """
    Removes non-BMP (Basic Multilingual Plane) characters from a string. This is useful 
    when entering contact names into the WhatsApp Web search bar, as ChromeDriver does 
    not support characters beyond 16-bit code points.

    Args:
        text (str): The input string potentially containing non-BMP characters.

    Returns:
        str: The input string with only BMP characters (i.e., ord(c) <= 0xFFFF).
    """
    return ''.join(c for c in text if ord(c) <= 0xFFFF)

def search_for_contact(contact, driver):
    """
    Searches for a specific contact in the WhatsApp search bar and selects the correct chat.

    This function enters the contact name into the search box, waits for the search results 
    to load, and attempts to match the exact contact name (after removing non-BMP characters). 
    If the contact is found, it clicks on the appropriate chat to open it.

    Args:
        contact (str): The contact name to search for.
        driver (webdriver.Chrome): The Selenium WebDriver instance controlling the browser.
    """

    search_box = driver.find_element(
        By.XPATH,'//div[@contenteditable="true" and @role="textbox" and @data-tab="3"]'
    )

    search_box.click()
    search_box.send_keys(Keys.CONTROL + 'a')
    search_box.send_keys(Keys.BACKSPACE)
    time.sleep(2)
    search_box.send_keys(strip_non_bmp(contact))
    time.sleep(2)
    search_box.send_keys(Keys.ENTER)

    try:
        results_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, './/div[@aria-label="Search results."]'))
        )
    except TimeoutException:
        print(f"[WARN] Search results for '{contact}' did not appear.")
        return

    chats_in_results = results_div.find_elements(
        By.XPATH, './/div[@class="x10l6tqk xh8yej3 x1g42fcv" and @role="listitem"]'
    )

    found = False
    for chat in chats_in_results:
        if not _has_element(chat, './/span[@dir="auto" and @title]'):
            continue
        
        chat_name_span = chat.find_element(By.XPATH, './/span[@dir="auto" and @title]')
        chat_name = ensure_BMP_characters(chat_name_span)

        if chat_name == strip_non_bmp(contact):
            chat.click()
            found = True
            break

    if not found:
        print(f"[WARN] Could not find contact '{contact}' in search results.")


def return_index(np_array, value):
    """
    Returns the index of the first occurrence of a value in a NumPy array.

    Args:
        np_array (np.ndarray): A NumPy array to search within.
        value (any): The value to locate in the array.

    Returns:
        int: The index of the first occurrence of the value. Returns -1 if the value is not found.
    """
    try:
        i = np.where(np_array == value)[0][0]
        return i
    except:
        #Not in array
        return -1

def identify_and_resolve_stopping_reason(driver):
    """
    Identifies and resolves the reason why scrolling up in a WhatsApp chat has stopped.

    When attempting to scroll to the top of a chat, there are several possible reasons 
    why scrolling halts:
        1. The messages are still syncing.
        2. A popup requires user interaction to load older messages.
        3. The top of the chat has been reached.
        4. Syncing has been paused.

    This function detects the reason by examining the visible message at the top of the chat 
    and takes the appropriate action to allow scraping to continue.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.

    Returns:
        str or None: A keyword representing the action taken or to take.
                     - "syncing" if messages are still syncing
                     - "break" if top of chat is reached
                     - None if no known condition is found
    """

    #possible message options
    informative_msg_options = np.array(["Syncing older messages. Click to see progress.", 
                               "Click here to get older messages from your phone.",
                               "Use WhatsApp on your phone to see older messages."])

    # Re-find the chat container to avoid stale references
    chat = driver.find_element(
        By.XPATH, '//div[@class="x10l6tqk x13vifvy x17qophe xyw6214 '
        'x9f619 x78zum5 xdt5ytf xh8yej3 x5yr21d x6ikm8r x1rife3k xjbqb8w x1ewm37j"]'
    )

    # Check for the top-of-chat message container
    if _has_element(chat, './/div[@class="x78zum5 x6s0dn4 x1r0jzty x17zd0t2"]'):

        informative_msg = chat.find_element(
            By.XPATH, './/div[@class="x78zum5 x6s0dn4 x1r0jzty x17zd0t2"]'
        ).text

        msg_index = return_index(informative_msg_options, informative_msg)

        if msg_index == 0:
            print("Your messages for the chat are still syncing. "
                  "Make sure to have your phone on and Whatsapp open!"
            )
            return "syncing"

        elif msg_index == 1:
            button = chat.find_element(
                By.XPATH, './/button[@class="x14m1o6m x126m2zf x1b9z3ur x9f619 x1rg5ohu '
                'x1okw0bk x193iq5w x123j3cw xn6708d x10b6aqq x1ye3gou x13a8xbf xdod15v x2b8uid '
                'x1lq5wgf xgqcy7u x30kzoy x9jhf4c"]'
            )
            button.click()
            time.sleep(5)

        elif msg_index == 2:
            return "break"
        
        elif _has_element(chat, './/span[@data-icon="alert-sync-paused"]'):
            print("Paused due to sync alert. Attempting to click the button.")
            button = chat.find_element(By.XPATH, './/button[contains(@class, "x14m1o6m")]')
            button.click()
            time.sleep(5)

        else:
            return None
 
    return None



def scroll_to_top_of_private_chat(driver):
    """
    Scrolls to the top of a private chat in WhatsApp Web.

    Unlike the side panel (chat list), the actual chat window renders all messages 
    currently visible in the DOM as you scroll. To access the full conversation, 
    it's necessary to scroll to the very top of the chat before attempting to 
    extract messages.

    This function handles scrolling incrementally and attempts to resolve interruptions 
    such as:
        - Message syncing in progress.
        - "Click to load more" buttons.
        - Sync pause alerts.
        - End of chat reached.

    Args:
        driver (WebDriver): The Selenium WebDriver instance controlling Chrome.
    """

    chat_block = driver.find_element(
        By.XPATH, '//div[@class="x10l6tqk x13vifvy x17qophe xyw6214 x9f619 x78zum5 xdt5ytf'
        ' xh8yej3 x5yr21d x6ikm8r x1rife3k xjbqb8w x1ewm37j" and @tabindex="0"]'
    )
    current_height = 0
    count = 0
    prev_height = 626

    while True:
        current_height = driver.execute_script("return arguments[0].scrollTop", chat_block)

        if current_height == prev_height:
            count += 1
        else:
            count = 0
        
        prev_height = current_height
 
        if count == 1:
            action_to_take = identify_and_resolve_stopping_reason(driver)
            if action_to_take == "break":
                break

            if action_to_take == "syncing":
                time.sleep(10)

                while True:
                    if identify_and_resolve_stopping_reason(driver) != "syncing":
                        count = 0
                        break
                    time.sleep(1)

        if count == 8:
            # Assume we've reached the top of the chat if it stops changing
            break

        driver.execute_script("arguments[0].scrollTop -= 700", chat_block)
        time.sleep(2)


def QR_code(driver):
    """
    This function  waits for the user to scan the QR code using their phone, 
    and confirms that the login was successful by waiting until the chat list becomes available.

    Args:
        driver (WebDriver): The Selenium WebDriver instance controlling Chrome.
    """
    driver.get("https://web.whatsapp.com")

    try:
        # Wait until the chat list appears, indicating login is complete
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@aria-label="Chat list" and @role="grid"]')))

        print("Log in succesful!")
    
    except:
        print("Log in failed!")

def collect_messages(all_contact_names, driver):
    """
    Collects and structures message data from private WhatsApp chats.

    For each private contact, this function:
        1. Opens the chat by searching for the contact name.
        2. Scrolls to the top of the chat to load all visible messages.
        3. Iterates through each message and extracts relevant data including:
            - Original message details
            - Reply information (if the message is a reply)
            - Media indicators (image, sticker, video)
            - Timestamps and sender names

    Args:
        all_contact_names (set): A set of contact names to collect messages from.
        driver (webdriver.Chrome): The Selenium WebDriver instance controlling Chrome.

    Returns:
        list: A list of lists. Each sublist contains all parsed messages for a contact.
              Each message is represented as:
              [reply_sender, reply_message, reply_media, 
               message_information, messages_text, image, sticker, video]
    """
    messages_df = []

    for contact in all_contact_names:
        search_for_contact(contact, driver)

        time.sleep(10)
        scroll_to_top_of_private_chat(driver)

        print(f"Beginning to read messages from chat with {contact}!")

        rows_of_messages = driver.find_element(
            By.XPATH, '//div[@class="x3psx0u xwib8y2 xkhd6sd xrmvbpv"]'
        )

        all_messages_in_chat = rows_of_messages.find_elements(
            By.XPATH, './/div[@tabindex="-1" and @role="row"]'
        )

        current_contact_messages = []

        for message_div in all_messages_in_chat:
            reply_sender = None
            reply_message = None
            reply_media = False
            message_information_div = None
            message_information = None
            image = False
            sticker = False
            video = False
            messages_text = None
            
            # Handle replies
            if _has_element(message_div, './/div[@class="_ahy0"]'):
                reply_div = message_div.find_element(By.XPATH, './/div[@class="_ahy0"]')

                reply_sender = reply_div.find_element(
                    By.XPATH, './/span[@dir="auto" and contains(@class, "_ao3e")]'
                ).text

                if _has_element(reply_div, './/span[@dir="auto" and @class="quoted-mention _ao3e"]'):
                    reply_message = reply_div.find_element(
                        By.XPATH, './/span[@dir="auto" and @class="quoted-mention _ao3e"]'
                    ).text
                
                if _has_element(reply_div, './/span[@data-icon="status-image"]'):
                    reply_media = True
                elif _has_element(reply_div, './/span[@data-icon="status-video"]'):
                    reply_media = True

            # Handle messages with text
            if _has_element(message_div, './/div[@class="copyable-text"]'):
                message_information_div = message_div.find_element(
                    By.XPATH, './/div[@class="copyable-text"]'
                )
                message_information = message_information_div.get_attribute("data-pre-plain-text")


                try:
                    text_span = message_div.find_element(By.XPATH, 
                                    './/span[@class="_ao3e selectable-text copyable-text"]/span')

                    messages_text = text_span.text
                except:
                    messages_text = None


            else:
                # Handle media with no text
                if _has_element(message_div, './/div[@class="_amk6 _amlo"]'):
                    message_information_div = message_div.find_element(
                        By.XPATH, './/div[@class="_amk6 _amlo"]'
                    )
                    name_of_sender_span = message_information_div.find_element(By.XPATH, './span')
                    name_of_sender = name_of_sender_span.get_attribute("aria-label")

                    if _has_element(message_information_div, './/span[@class="x1rg5ohu x16dsc37" and @dir="auto"]'):
                        time_of_message_div = message_information_div.find_element(
                            By.XPATH, './/span[@class="x1rg5ohu x16dsc37" '
                            'and @dir="auto"]'
                        )
                        time_of_message = time_of_message_div.text
                    else:
                        time_of_message = "Unknown time"

                    message_information = f"[{time_of_message}, None] {name_of_sender}:"

            # Determine media types
            if _has_element(message_div, './/span[@data-icon="media-download"]'):
                if _has_element(message_div, './/div[@aria-label="Open picture"]'):
                    image = True
                else:
                    sticker = True

            # Photo
            elif _has_element(message_div, './/div[@aria-label="Open picture"]'):
                image = True


            # Sticker
            elif _has_element(message_div, './/div[contains(@label, "Sticker")]'):
                sticker = True

            # Video
            elif _has_element(message_div, './/span[@data-icon="msg-video"]'):
                video = True
            
            all_info_of_message = [reply_sender, reply_message, 
                                   reply_media, message_information, 
                                   messages_text, image, sticker, video]

            current_contact_messages.append(all_info_of_message)
        
        messages_df.append(current_contact_messages)

    return messages_df



def main():
    print(STARTING_MESSAGE)
    input("\nPress enter when you are ready!")

    # Initiate driver
    options = Options()
    options.add_argument("--start-maximized")
    service = Service()
    driver = webdriver.Chrome(options, service)

    QR_code(driver)

    # Find all the private chats
    all_contact_names = find_contact_names(driver)

    #Collect messages from each chat
    messages = collect_messages(all_contact_names, driver)

    # Save the messages
    with open("whatsapp_messages.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)


if __name__=='__main__':
    main()