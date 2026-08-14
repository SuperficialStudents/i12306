from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import json
import os

CURRENT_PATH = os.path.abspath(__file__)
PARENT_DIR = os.path.dirname(CURRENT_PATH)
ROOT_DIR = os.path.dirname(PARENT_DIR)


class Login:
    def __init__(self):
        self.login_url = 'https://kyfw.12306.cn/otn/resources/login.html'
        self.init_url = 'https://kyfw.12306.cn/otn/view/index.html'
        self.driver = webdriver.Chrome()

    @staticmethod
    def login_succeeded(url, cookies):
        """Login is done when uamauthclient set `tk`, or the personal-center page is reached.

        Current 12306 QR/password success first goes to /otn/login/userLogin then
        /otn/passport?redirect=..., not necessarily the exact init_url.
        """
        url = url or ""
        names = {c["name"] for c in cookies}
        return "tk" in names or "/otn/view/index.html" in url

    def _wait_logged_in(self, driver):
        return self.login_succeeded(driver.current_url, driver.get_cookies())

    def _login(self):
        self.driver.get(self.login_url)
        print(">>> Please complete login in the opened browser (QR or password)...")
        try:
            WebDriverWait(self.driver, 1000).until(self._wait_logged_in)
        except TimeoutException:
            url = ""
            names = []
            try:
                url = self.driver.current_url
                names = [c["name"] for c in self.driver.get_cookies()]
            except Exception:
                pass
            print(f">>> login timeout, current url={url}, cookies={names}")
            raise

    def _save_cookies(self):
        cookies = self.driver.get_cookies()
        cookies_dir = os.path.join(ROOT_DIR, "cookies")
        os.makedirs(cookies_dir, exist_ok=True)

        self.driver.get('https://kyfw.12306.cn/otn/login/conf')
        conf = json.loads(self.driver.find_element(By.TAG_NAME, 'pre').text)
        user_name = conf['data']['user_name']

        with open(os.path.join(cookies_dir, f"{user_name}.json"), "w") as f:
            json.dump(cookies, f)
        with open(os.path.join(cookies_dir, "cookies.json"), "w") as f:        # cookies.json始终保存最后登录cookies
            json.dump(cookies, f)
        self.driver.quit()

    def run(self):
        self._login()
        self._save_cookies()


if __name__ == "__main__":
    login = Login()
    login.run()
