import os
import json
from threading import Thread, Lock, Condition
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
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
open_camera = config_data['open_camera']

def allow_camera_permissions(driver):
    try:
        # Wait for the permissions modal to be present
        permissions_modal = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button#permission-allow-button"))
        )

        # Scroll to the allow button and click it
        allow_button = driver.find_element(By.CSS_SELECTOR, "button#permission-allow-button")
        driver.execute_script("arguments[0].scrollIntoView(true);", allow_button)
        ActionChains(driver).move_to_element(allow_button).click().perform()
        print("Permissions granted.")
    except TimeoutException:
        print("No permissions modal found.")
    except Exception as e:
        print(f"An error occurred while allowing permissions: {e}")

def read_links_from_file(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file.readlines()]

def create_browser_instance(bot_id, link, screenshot_dir,open_camera):
    global bots_in_session
    bot_name = f"Bot_{bot_id}"

    # Path to the fake video file
    fake_video_path = os.path.abspath("/home/ubuntu/LoadTest/test-video.Y4M")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--enable-webgl")
    chrome_options.add_argument("--ignore-gpu-blacklist")
    chrome_options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--disable-hang-monitor")
    chrome_options.add_argument("--disable-client-side-phishing-detection")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-prompt-on-repost")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-breakpad")
    chrome_options.add_argument("--disable-component-extensions-with-background-pages")
    chrome_options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    chrome_options.add_argument("--disable-site-isolation-trials")
    chrome_options.add_argument("--metrics-recording-only")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--no-pings")
    chrome_options.add_argument("--password-store=basic")
    chrome_options.add_argument("--use-mock-keychain")
    chrome_options.add_argument("--use-fake-device-for-media-stream")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.geolocation": 1,
        "profile.default_content_setting_values.notifications": 1
    })
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    service = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 15)
    print(f"{bot_name}: Created a new browser instance.")

    try:
        driver.get(link)
        print(f"{bot_name}: Opened link: {link}")
        time.sleep(1)  # Random delay between 0 and 5 seconds

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
           # Additional check to ensure the camera stream is active
           screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_before_session_screenshot.png")
           driver.save_screenshot(screenshot_path)
           print(f"{bot_name}: Screenshot saved to {screenshot_path}")
            
           if open_camera:
               allow_camera_permissions(driver)

           # Ensure the cookie banner is visible
           wait.until(EC.visibility_of_element_located((By.ID,"cm")))

           # Wait until the cookies button is present in the DOM and visible
           cookies_button = wait.until(EC.visibility_of_element_located((By.ID,"c-p-bn")))
           print(f"{bot_name}: Cookies button is visible.")

           # Scroll the cookies button into view
           driver.execute_script("arguments[0].scrollIntoView(true);", cookies_button)
           print(f"{bot_name}: Scrolled cookies button into view.")

           # Wait until the cookies button is clickable
           cookies_button = wait.until(EC.element_to_be_clickable((By.ID, "c-p-bn")))
           print(f"{bot_name}: Cookies button is clickable.")

           # Click the cookies button
           cookies_button.click()
           print(f"{bot_name}: Accepted cookies.")

           print(f"{bot_name}: Clicked the close button on the modal.")
        except TimeoutException:
           print(f"{bot_name}: No cookies pop-up appeared.")
        except Exception as e:
           print(f"{bot_name}: An error occurred while clicking the cookies button - {e}")

        try:
            time.sleep(1)
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
                time.sleep(1)
                screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_session_screenshot.png")
                driver.save_screenshot(screenshot_path)
                print(f"{bot_name}: Screenshot saved to {screenshot_path}")

                break
            except TimeoutException:
                print(f"{bot_name}: Retry {attempt + 1}/{confirmation_attempts} - Waiting for session confirmation.")
                if attempt == confirmation_attempts - 1:
                    print(f"{bot_name}: Failed to confirm session join after retries.")
                    return

        # Open camera for the first 10 bots only
        if bot_id <= 15 and open_camera:
            try:
                # Wait for potential overlays or modals to disappear
                time.sleep(2)
                camera_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.footer-button.icon-background-image[data-action="open-cam"]')))
                driver.execute_script("arguments[0].scrollIntoView(true);", camera_button)  # Scroll into view
                for _ in range(5):  # Try clicking up to 5 times
                    try:
                        screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_before_camera_screenshot.png")
                        driver.save_screenshot(screenshot_path)
                        print(f"{bot_name}: Screenshot saved to {screenshot_path}")
                        camera_button.click()
                        time.sleep(1)
                        screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_after_camera__screenshot.png")
                        driver.save_screenshot(screenshot_path)
                        print(f"{bot_name}: Screenshot saved to {screenshot_path}")

                        print(f"{bot_name}: Opened camera via JavaScript.")
                        break
                    except ElementClickInterceptedException:
                        screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_camera_exception_screenshot.png")
                        driver.save_screenshot(screenshot_path)
                        print(f"{bot_name}: Screenshot saved to {screenshot_path}")
                        print(f"{bot_name}: Retrying camera button click.")
                        time.sleep(1)


            except (TimeoutException, NoSuchElementException) as e:
                print(f"{bot_name}: Camera button not found or could not be clicked - {e}")

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

   # Check if there are more links than the number of bots specified and adjust if necessary
    max_bots = min(len(links), num_bots)
    
    for bot_id in range(1, max_bots + 1):
        link = links[bot_id - 1]  # Adjust index for 0-based list indexing
        print(f"Starting Bot {bot_id} for link: {link}")
        bot_thread = Thread(target=create_browser_instance, args=(bot_id, link, screenshot_dir, open_camera))
        bot_thread.start()

        # Wait for the bot to join the session before starting the next one
        with bot_start_condition:
            bot_start_condition.wait()

        print(f"Bot {bot_id} has started and joined the session.")

    print("All bots processed.")

if __name__ == "__main__":
    main()
