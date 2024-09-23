import json
import os
import time
from threading import Thread, Lock, Condition
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

bots_in_session = 0
bots_in_session_lock = Lock()
bot_start_condition = Condition()
camera_clicks = 0
camera_clicks_lock = Lock()

def log_with_timestamp(message):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

with open('config.json', 'r') as config_file:
    config_data = json.load(config_file)

num_bots = config_data['num_bots']
session_duration = config_data['session_duration']
open_camera = config_data['open_camera']
vote = config_data['vote']
vote_time = config_data['vote_time']

vote_time_strp = datetime.strptime(vote_time , "%Y-%m-%d %H:%M:%S")

def read_links_from_file(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file.readlines()]

def create_browser_instance(bot_id, link, screenshot_dir, open_camera):
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
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--mute-audio")
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
    log_with_timestamp(f"{bot_name}: Created a new browser instance.")

    try:
        driver.get(link)
        log_with_timestamp(f"{bot_name}: Opened link: {link}")
        time.sleep(1)
        try:
                screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_before_session_screenshot.png")
                driver.save_screenshot(screenshot_path)
                log_with_timestamp(f"{bot_name}: Screenshot saved to {screenshot_path}")

                wait.until(EC.visibility_of_element_located((By.ID, "cm")))

                cookies_button = wait.until(EC.visibility_of_element_located((By.ID, "c-p-bn")))
                log_with_timestamp(f"{bot_name}: Cookies button is visible.")

                driver.execute_script("arguments[0].scrollIntoView(true);", cookies_button)
                log_with_timestamp(f"{bot_name}: Scrolled cookies button into view.")

                cookies_button = wait.until(EC.element_to_be_clickable((By.ID, "c-p-bn")))
                log_with_timestamp(f"{bot_name}: Cookies button is clickable.")

                cookies_button.click()
                log_with_timestamp(f"{bot_name}: Accepted cookies.")

                log_with_timestamp(f"{bot_name}: Clicked the close button on the modal.")
            except TimeoutException:
                screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_no_popup_screenshot.png")
                driver.save_screenshot(screenshot_path)
                log_with_timestamp(f"{bot_name}: No cookies pop-up appeared.")
            except Exception as e:
                screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_no_cookies_screenshot.png")
                driver.save_screenshot(screenshot_path)
                log_with_timestamp(f"{bot_name}: An error occurred while clicking the cookies button - {e}")


        for attempt in range(3):
            try:
                continue_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.btn.btn-secondary.pointer')))
                continue_button.click()
                log_with_timestamp(f"{bot_name}: Clicked 'Continue anyway' button.")
                break
            except TimeoutException:
                log_with_timestamp(f"{bot_name}: Retrying 'Continue anyway' button click. Attempt {attempt + 1}")
                if attempt == 2:
                    log_with_timestamp(f"{bot_name}: 'Continue anyway' button not present after multiple attempts.")
        if open_camera:                
            try:
                time.sleep(1)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.perculus-button-container')))
                driver.execute_script("document.querySelector('div.perculus-button-container').click();")
                log_with_timestamp(f"{bot_name}: Clicked 'Join Session' button via JavaScript.")
            except TimeoutException:
                log_with_timestamp(f"{bot_name}: 'Join Session' button not present.")

        confirmation_attempts = 5
        for attempt in range(confirmation_attempts):
            try:
                session_confirm_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.footer-button[data-action="open-cam"]')))
                log_with_timestamp(f"{bot_name}: Confirmed session join.")
                time.sleep(1)
                screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_session_screenshot.png")
                driver.save_screenshot(screenshot_path)
                log_with_timestamp(f"{bot_name}: Screenshot saved to {screenshot_path}")

                break
            except TimeoutException:
                log_with_timestamp(f"{bot_name}: Retry {attempt + 1}/{confirmation_attempts} - Waiting for session confirmation.")
                if attempt == confirmation_attempts - 1:
                    log_with_timestamp(f"{bot_name}: Failed to confirm session join after retries.")
                    return

        if bot_id <= 15 and open_camera:
            try:
                time.sleep(2)
                camera_button = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'div.footer-button.icon-background-image[data-action="open-cam"]')))
                driver.execute_script("arguments[0].scrollIntoView(true);", camera_button)
                for _ in range(5):
                    try:
                        screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_before_camera_screenshot.png")
                        driver.save_screenshot(screenshot_path)
                        log_with_timestamp(f"{bot_name}: Screenshot saved to {screenshot_path}")
                        camera_button.click()
                        time.sleep(3)
                        screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_after_camera__screenshot.png")
                        driver.save_screenshot(screenshot_path)
                        log_with_timestamp(f"{bot_name}: Screenshot saved to {screenshot_path}")

                        log_with_timestamp(f"{bot_name}: Opened camera via JavaScript.")
                        break
                    except ElementClickInterceptedException:
                        screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_camera_exception_screenshot.png")
                        driver.save_screenshot(screenshot_path)
                        log_with_timestamp(f"{bot_name}: Screenshot saved to {screenshot_path}")
                        log_with_timestamp(f"{bot_name}: Retrying camera button click.")
                        time.sleep(1)

            except (TimeoutException, NoSuchElementException) as e:
                log_with_timestamp(f"{bot_name}: Camera button not found or could not be clicked - {e}")
                 
        
        if vote:
            while datetime.now() < vote_time_strp:
                log_with_timestamp(f"{bot_name}: Waiting for the vote time.")
                time.sleep(60) 
            try:
                option_css = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.custom-quiz:first-of-type")))
                option_css.click()
                log_with_timestamp(f"{bot_name}: Option A selected.")

                send_button_css = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.answer-button")))
                send_button_css.click()
                log_with_timestamp(f"{bot_name}: Sent the answer.")
            except TimeoutException:
                screenshot_path = os.path.join(screenshot_dir, f"{bot_name}_answer_not_send_screenshot.png")
                driver.save_screenshot(screenshot_path)
                log_with_timestamp(f"{bot_name}: can not send the answer.")        

        with bots_in_session_lock:
            bots_in_session += 1
            log_with_timestamp(f"{bot_name}: Number of bots in session: {bots_in_session}")

        with bot_start_condition:
            bot_start_condition.notify()

        while True:
            try:
                time.sleep(1)
            except Exception as e:
                log_with_timestamp(f"{bot_name}: Error during session keep-alive - {e}")

    except Exception as e:
        log_with_timestamp(f"{bot_name}: An error occurred - {e}.")
    finally:
        driver.quit()
        log_with_timestamp(f"{bot_name}: Browser instance closed.")

    log_with_timestamp(f"Bot_{bot_id}: Task completed.")

def main():
    file_path = 'session_links.txt'
    links = read_links_from_file(file_path)
    screenshot_dir = "screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)

    batch_size = 10  # Number of bots to start per batch
    max_bots = min(len(links), num_bots)

    for i in range(0, max_bots, batch_size):
        batch_end = min(i + batch_size, max_bots)
        bot_threads = []

        for bot_id in range(i + 1, batch_end + 1):
            link = links[bot_id - 1]  # Adjust index for 0-based list indexing
            log_with_timestamp(f"Starting Bot {bot_id} for link: {link}")
            bot_thread = Thread(target=create_browser_instance, args=(bot_id, link, screenshot_dir, open_camera))
            bot_threads.append(bot_thread)
            bot_thread.start()

        # Wait for all bots in the current batch to start
        with bot_start_condition:
            for _ in range(len(bot_threads)):
                bot_start_condition.wait()

        log_with_timestamp(f"Batch {i // batch_size + 1} has started and joined the session.")

    log_with_timestamp("All bots processed.")




if __name__ == "__main__":
    main()

