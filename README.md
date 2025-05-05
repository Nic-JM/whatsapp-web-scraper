# WhatsApp Web Scraper

This is a Selenium-based Python scraper that extracts messages from **WhatsApp Web**. The scraper **ignores group chats** and only collects data from your *private chats*. It saves the messages in a `.json` file as a nested list and serves as the data collection component for a project that will build a language model to mimic your messaging style.

## Features

- Logs into WhatsApp Web by prompting you to scan the QR code
- Automatically finds the names of all private chats by:
  - Scrolling through the sidebar
  - Using logic to determine whether a chat is a group or private
- For each private chat, it scrapes:
  - Sender
  - Message text
  - Timestamp
  - Reply context (if any)
  - Media flags (images, videos, stickers)
- Robust handling of:
  - Sync delays
  - Scroll blockers (e.g. "Click to load more" buttons)

### WhatsApp Web Limitation
> Only messages from the **past year** are available on WhatsApp Web. Messages older than one year will not be accessible.

------------------------------


## How to run the script

### 1. Clone the Repository
git clone https://github.com/Nic-JM/whatsapp_scraper.git
cd whatsapp_scraper

### 2. Set Up Your Own Virtual Environment
python3 -m venv web
source web/bin/activate
pip install -r requirements.txt

### 3. Download ChromeDriver
downlad the relevant chromedriver at https://chromedriver.chromium.org/downloads.
Place the extracted binary in chromedriver-linux64/

### 4. Run The Scraper
python src/fetch_msgs.py
You will then be prompted to to scan the WhatApp Web QR code on your phone

### 5. Output
The messages are saved to: whatsapp_messages.json
The structure is a nested list:
- Each chat contains a list of messages
- Each message includes detailed metadata (sender, time, media type, reply info, etc.)

## Dependencies
See requirements.txt
