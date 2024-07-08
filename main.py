import os
import json
from threading import Thread, Lock, Condition
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
import time
from random import random

bots_in_session = 0
bots_in_session_lock = Lock()
bot_start_condition = Condition()
camera_clicks = 0
camera_clicks_lock = Lock()

with open('config.json', 'r') as config_file:
    config_data = json.load(config_file)

num_bots = config_data['num_bots']
session_duration = config_data['session_duration']

def read_links_from_file(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file.readlines()]

def create_browser_instance(bot_id, link, screenshot_dir):
    global bots_in_session
    bot_name = f"Bot_{bot_id}"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--enable-webgl")
    chrome_options.add_argument("--ignore-gpu-blacklist")
    chrome_options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument("--use-file-for-fake-video-capture=./test-video.y4m")
    chrome_options.add_argument('--aggressive-cache-discard')
    chrome_options.add_argument('--disable-cache')
    chrome_options.add_argument('--disable-application-cache')
    chrome_options.add_argument('--js-flags="--max-old-space-size=128"')
    chrome_options.add_argument('--no-zygote')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-background-networking')
    chrome_options.add_argument('--disable-client-side-phishing-detection')
    chrome_options.add_argument('--disable-default-apps')
    chrome_options.add_argument('--disable-translate')
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--metrics-recording-only')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                                
    service = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 15)
    print(f"{bot_name}: Created a new browser instance.")

    try:
        driver.get(link)
        print(f"{bot_name}: Opened link: {link}")
        time.sleep(random() * 5)  # Random delay between 0 and 5 seconds

        try:
            cookies_button = wait.until(EC.element_to_be_clickable((By.ID, "c-p-bn")))
            cookies_button.click()
            print(f"{bot_name}: Accepted cookies.")
        except TimeoutException:
            print(f"{bot_name}: No cookies pop-up appeared.")

        for attempt in range(3):
            try:
                continue_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.btn.btn-secondary.pointer')))
                continue_button.click()
                print(f"{bot_name}: Clicked 'Continue anyway' button.")
                break
            except TimeoutException:
                print(f"{bot_name}: Retrying 'Continue anyway' button click. Attempt {attempt + 1}")
                if attempt == 2:
                    print(f"{bot_name}: 'Continue anyway' button not present after multiple attempts.")

        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.perculus-button-container')))
            driver.execute_script("document.querySelector('div.perculus-button-container').click();")
            print(f"{bot_name}: Clicked 'Join Session' button via JavaScript.")
        except TimeoutException:
            print(f"{bot_name}: 'Join Session' button not present.")

        confirmation_attempts = 5
        for attempt in range(confirmation_attempts):
            try:
                session_confirm_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.footer-button[data-action="open-cam"]')))
                print(f"{bot_name}: Confirmed session join.")
                break
            except TimeoutException:
                print(f"{bot_name}: Retry {attempt + 1}/{confirmation_attempts} - Waiting for session confirmation.")
                if attempt == confirmation_attempts - 1:
                    print(f"{bot_name}: Failed to confirm session join after retries.")
                    return

        # Open camera for the first 10 bots only
        if bot_id <= 10:
            try:
                camera_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.footer-button[data-action="open-cam"]')))
                camera_button.click()
                print(f"{bot_name}: Opened camera.")
            except TimeoutException:
                print(f"{bot_name}: Camera button not found.")

        with bots_in_session_lock:
            bots_in_session += 1
            print(f"{bot_name}: Number of bots in session: {bots_in_session}")

        # Notify the main thread that the bot has joined the session
        with bot_start_condition:
            bot_start_condition.notify()

        # Keep the bot active in the session without exiting
        while True:
            time.sleep(session_duration)

    except Exception as e:
        print(f"{bot_name}: An error occurred - {e}.")
    finally:
        driver.quit()
        print(f"{bot_name}: Browser instance closed.")

    print(f"Bot_{bot_id}: Task completed.")

def main():
    file_path = 'session_links.txt'
    links = read_links_from_file(file_path)
    screenshot_dir = "screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)

    for bot_id, link in enumerate(links, start=1):
        print(f"Starting Bot {bot_id} for link: {link}")
        bot_thread = Thread(target=create_browser_instance, args=(bot_id, link, screenshot_dir))
        bot_thread.start()

        # Wait for the bot to join the session before starting the next one
        with bot_start_condition:
            bot_start_condition.wait()

        print(f"Bot {bot_id} has started and joined the session.")

    print("All bots processed.")

if __name__ == "__main__":
    main()
