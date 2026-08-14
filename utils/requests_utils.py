from fake_useragent import UserAgent
from datetime import date
import urllib.parse
import requests
import subprocess
import httpx
from datetime import datetime, timedelta
import time
import re
from collections import OrderedDict
import click
import yaml
import json
import os
import sys

from TicketsFilter import TicketFilter
from ticket_flow import plan_run

CURRENT_PATH = os.path.abspath(__file__)
PARENT_DIR = os.path.dirname(CURRENT_PATH)
ROOT_DIR = os.path.dirname(PARENT_DIR)

check_login_url = "https://kyfw.12306.cn/otn/login/checkUser"                                # 检查用户登录状态
query_url = "https://kyfw.12306.cn/otn/leftTicket/queryU"                                    # 查询票务信息
submit_order_url = "https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest"                 # 提交订单
init_dc_url = "https://kyfw.12306.cn/otn/confirmPassenger/initDc"                            # 初始化订单确认界面
passenger_url = "https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs"                # 获取乘客信息
check_order_url = "https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo"                # 检查订单信息
confirm_url = "https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue"             # 确认排队
# query_order_wait_time_url = "https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime"  # 查询排队并等待
# query_order_url = "https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForDcQueue"         # 查询订单结果


class Client:
    SEAT_TYPE_MAP = {
        "商务座": "9",
        "一等座": "M",
        "二等座": "O",
        "软卧": "4",
        "硬卧": "3",
        "硬座": "1",
        "无座": "1",
    }
    ID_TYPE_MAP = {
        "身份证": "1",
        "港澳通行证": "C",
        "台湾通行证": "G",
        "护照": "B",
    }

    def __init__(self, cookies_file=None, config_file=None):
        self.headers = self._build_dynamics_headers()
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.cookies_file = cookies_file
        self._login_file(cookies_file)
        self.config = self._get_config(config_file)
        self.station_info = self._get_station_info()
        self.tickets_filter = TicketFilter(config_file)


    @staticmethod
    def _get_station_info():
        with open(os.path.join(ROOT_DIR, "data", "station_name_map.json"), "r", encoding="utf-8") as f:
            station_info = json.load(f)
        return station_info

    @staticmethod
    def _get_config(config_file=None):
        if config_file and os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        else:
            with open(os.path.join(ROOT_DIR, "config", "config.yaml"), "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

    @staticmethod
    def _build_dynamics_headers(referer_url=None):
        ua = UserAgent()
        user_agent = ua.random
        ua_parts = user_agent.split(' ')
        brand_parts = [part for part in ua_parts if
                       '/' in part and 'like' not in part and 'Gecko' not in part and 'AppleWebKit' not in part and 'Mozilla' not in part]
        sec_ch_ua = ", ".join([f'"{p.split("/")[0]}";v="{p.split("/")[1].split(".")[0]}"' for p in brand_parts])
        sec_ch_ua = sec_ch_ua.replace('Edg', '"Microsoft Edge"')

        headers = {
            "Host": "kyfw.12306.cn",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua": sec_ch_ua,
            "sec-ch-ua-mobile": "?0",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "*/*",
            "If-Modified-Since": "0",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }

        if referer_url:
            headers.update(referer_url)
        return headers

    def get(self, url, data=None):
        try:
            ret = self.session.get(url, data=data)
            return ret
        except:
            print(f"get url: {url} --> error!")

    def post(self, url, data=None):
        try:
            ret = self.session.post(url, data=data)
            return ret
        except:
            print(f"post url {url} --> error!")

    def _login_file(self, cookies_file=None):
        if cookies_file and os.path.exists(cookies_file):
            with open(cookies_file, "r") as f:
                cookies = json.load(f)
        else:
            with open(os.path.join(ROOT_DIR, "cookies", "cookies.json"), "r") as f:
                cookies = json.load(f)
        # cookie_str = '; '.join([f'{k}={v}' for k, v in cookies.items()])
        # self.headers["Cookie"] = cookie_str
        for c in cookies:
            self.session.cookies.set(c['name'], c['value'], domain=c['domain'], path=c['path'])
        check = self.session.post(check_login_url, data={'_json_att': ''}).json()
        if check['data']['flag']:
            print('>>> login success!')
        else:
            print('>>> login failed! please update the file `cookies.json`...')

    def _update_query_cookies(self, from_station, to_station, train_date, back_train_date):
        self.session.cookies.set("_jc_save_wfdc_flag", "dc", domain="kyfw.12306.cn", path="/") # 单程票
        self.session.cookies.set("_jc_save_toStation", to_station, domain="kyfw.12306.cn", path="/")
        self.session.cookies.set("_jc_save_toDate", back_train_date, domain="kyfw.12306.cn", path="/")
        self.session.cookies.set("_jc_save_showIns", "true", domain="kyfw.12306.cn", path="/")   ####
        self.session.cookies.set("_jc_save_fromDate", train_date, domain="kyfw.12306.cn", path="/")
        self.session.cookies.set("_jc_save_fromStation", from_station, domain="kyfw.12306.cn", path="/")

        # from_station_decoded = urllib.parse.unquote(from_station.split(',')[0])
        # to_station_decoded = urllib.parse.unquote(to_station.split(',')[0])

    def query_tickets(self, query_date):
        self.headers["Referer"] = "https://kyfw.12306.cn/otn/leftTicket/init"

        ticket_config = self.config.get("ticket_info", {})
        from_station = ticket_config.get("from_station")
        to_station = ticket_config.get("to_station")
        back_train_date = date.today().strftime("%Y-%m-%d")        # 返程时间，设定为今天，不影响查询票

        from_station_code, to_station_code = self.station_info.get(from_station, ""), self.station_info.get(to_station, "")
        from_cookie_val = f"{urllib.parse.quote(from_station)},{from_station_code}"
        to_cookie_val = f"{urllib.parse.quote(to_station)},{to_station_code}"

        self._update_query_cookies(from_cookie_val, to_cookie_val, query_date, back_train_date)

        params = {
            "leftTicketDTO.train_date": query_date,
            "leftTicketDTO.from_station": from_station_code,
            "leftTicketDTO.to_station": to_station_code,
            "purpose_codes": "ADULT"
        }

        referer_url = (f"https://kyfw.12306.cn/otn/leftTicket/init?"
                       f"linktypeid=dc&fs={from_cookie_val}&ts={to_cookie_val}&date={query_date}&flag=N,N,Y")
        self.headers["Referer"] = referer_url
        self.session.headers.update(self.headers)

        last_error = None
        for attempt in range(1, 4):
            try:
                print(f">>> Querying tickets from {from_station} to {to_station} on {query_date}...")
                ret = self.session.get(query_url, params=params, headers=self.headers, timeout=15)
                print(f">>> status code for querying: {ret.status_code}")
                if 'html' in ret.headers.get('Content-Type', '') or ret.text.startswith('<!DOCTYPE html'):
                    print(">>> Login failed, please log in again!")
                    return None
                elif ret.status_code == 403:
                    print(">>> Access denied by the server, the IP may be restricted.")
                    return None
                elif ret.status_code == 503:
                    print(">>> The server is temporarily unavailable, possibly due to excessive access.")
                    last_error = f"HTTP {ret.status_code}"
                    time.sleep(1.5)
                    continue
                ret.raise_for_status()

                result = ret.json()
                if result.get("status"):
                    print(">>> Querying success!")
                    return self._parse_ticket_data(result.get("data", {}))
                print(f">>> Querying failed: {result.get('messages')}")
                return None
            except requests.exceptions.Timeout as e:
                last_error = e
                print(f">>> Query timeout ({attempt}/3) for {query_date}: {e}")
                time.sleep(1.5)
            except Exception as e:
                print(f">>> An error occurred while requesting the ticket check interface: {e}")
                return None
        print(f">>> Query for {query_date} failed after retries: {last_error}")
        return None

    @staticmethod
    def _parse_ticket_data(raw_data):
        print(">>> Querying Tickets:")
        # print(raw_data)
        result_list = raw_data.get('result', [])
        if not result_list:
            print(">>> No train that meet the criteria were found...")
            return []
        print(f">>> A total of {len(result_list)} trains were queried...")
        return result_list

    def _valid_user_login(self):
        try:
            check = self.session.post(check_login_url, data={'_json_att': ''})   # Second verification
            check.raise_for_status()
            result = check.json()
            if result['data']['flag']:
                print('>>> Identity verification successful!')
                return True
            else:
                print('>>> Authentication failed...')
                return False
        except Exception as e:
            print(f">>> Identity verification request exception: {e}")
            return False

    def _cookies_clean(self):
        cookies_dir = os.path.join(ROOT_DIR, "cookies")
        for file in os.listdir(cookies_dir):
            if file.endswith(".json"):
                file_path = os.path.join(cookies_dir, file)
                try:
                    os.remove(file_path)
                    print(f">>> Deleted: {file_path}")
                except Exception as e:
                    print(f">>> Failed to delete: {file_path},\n    Error: {e}")

    def _login(self, i):
        login_py = os.path.join(ROOT_DIR, "utils", "login.py")
        result = subprocess.run([sys.executable, login_py], cwd=ROOT_DIR)
        if result.returncode == 0:
            print(f">>> The {i}-th login was successful!")
            return True
        print(f">>> The {i}-th login Failed...")
        return False

    def valid_cookies(self):
        _is_valid = self._valid_user_login()
        if _is_valid:
            print(">>> Ticket purchase begins...")
        else:
            max_times = 3
            for i in range(max_times):
                print(">>> Login expired, please log in again...")
                if not self._login(i):
                    print(">>> Re-login failed. Existing cookies were kept.")
                    continue
                self._update_cookies()
                _is_valid = self._valid_user_login()
                if _is_valid:
                    print(">>> Ticket purchase begins...")
                    break
        return _is_valid

    def _cookie_file_path(self):
        if self.cookies_file and os.path.exists(self.cookies_file):
            return self.cookies_file
        return os.path.join(ROOT_DIR, "cookies", "cookies.json")

    def _read_cookies_file(self):
        path = self._cookie_file_path()
        if not os.path.exists(path):
            print(f">>> Cookie file missing: {path}. Please log in again.")
            sys.exit(1)
        with open(path, "r") as f:
            return json.load(f)

    def _update_cookies(self, is_test=True):
        cookies = self._read_cookies_file()
        for c in cookies:
            self.session.cookies.set(c['name'], c['value'], domain=c['domain'], path=c['path'])

        ticket_config = self.config.get("ticket_info", {})
        from_station = ticket_config.get("from_station")
        to_station = ticket_config.get("to_station")
        if is_test:
            train_date = ticket_config.get("train_date_test")
        else:
            train_date = ticket_config.get("train_date")
        back_train_date = date.today().strftime("%Y-%m-%d")  # 返程时间，设定为今天，不影响查询票

        from_station_code, to_station_code = self.station_info.get(from_station, ""), self.station_info.get(to_station, "")
        from_cookie_val = f"{urllib.parse.quote(from_station)},{from_station_code}"
        to_cookie_val = f"{urllib.parse.quote(to_station)},{to_station_code}"

        self._update_query_cookies(from_cookie_val, to_cookie_val, train_date, back_train_date)

    def _get_latest_cookie_str(self):
        cookies = self._read_cookies_file()
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
        cookie_str = '; '.join([f'{k}={v}' for k, v in cookies_dict.items()])
        return cookie_str

    def _submit_order(self, ticket_info):
        secret_str = ticket_info["secret_str"]
        train_date = ticket_info["train_date"]
        back_train_date = ticket_info["back_train_date"]
        from_station = ticket_info["from_station"]
        to_station = ticket_info["to_station"]
        bed_level_info = ticket_info["bed_level_info"]
        purpose_codes = "ADULT"

        data = {
            "secretStr": secret_str,
            "train_date": train_date,
            "back_train_date": back_train_date,
            "tour_flag": "dc",
            "purpose_codes": purpose_codes,
            "query_from_station_name": from_station,
            "query_to_station_name": to_station,
            "bed_level_info": bed_level_info,
            "seat_discount_info": "",
            "undefined": ""
        }

        headers = OrderedDict([
            ("Host", "kyfw.12306.cn"),
            ("Connection", "keep-alive"),
            ("sec-ch-ua-platform", "\"Windows\""),
            ("X-Requested-With", "XMLHttpRequest"),
            ("User-Agent",
             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"),
            ("Accept", "*/*"),
            ("sec-ch-ua", "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Microsoft Edge\";v=\"138\""),
            ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
            ("sec-ch-ua-mobile", "?0"),
            ("Origin", "https://kyfw.12306.cn"),
            ("Sec-Fetch-Site", "same-origin"),
            ("Sec-Fetch-Mode", "cors"),
            ("Sec-Fetch-Dest", "empty"),
            ("Referer", "https://kyfw.12306.cn/otn/leftTicket/init"),
            ("Accept-Encoding", "gzip, deflate, br, zstd"),
            ("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"),
        ])

        try:
            ret = self.session.post(
                submit_order_url, headers=headers, data=data, timeout=15, allow_redirects=False
            )
            if ret.status_code in (301, 302, 303, 307, 308):
                print(f"Abnormal submission of ticket purchase request: HTTP {ret.status_code} -> {ret.headers.get('Location')}")
                return "302"
            ret.raise_for_status()
            result = ret.json()
            if result.get("status"):
                print(">>> Successfully submitted ticket purchase request!")
                return True
            print(f">>> Failed to submit ticket purchase request: {result.get('messages')}")
            return "203"
        except Exception as e:
            print(f"Abnormal submission of ticket purchase request: {e}")
            if "302" in str(e):
                return "302"
            return False

    @staticmethod
    def _init_dc(cookie_str):
        # cookies = ticket_info["cookies"]
        headers = OrderedDict([
            ("Host", "kyfw.12306.cn"),
            ("Connection", "keep-alive"),
            ("Content-Length", "10"),
            ("Cache-Control", "max-age=0"),
            ("sec-ch-ua", "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Microsoft Edge\";v=\"138\""),
            ("sec-ch-ua-mobile", "?0"),
            ("sec-ch-ua-platform", "\"Windows\""),
            ("Origin", "https://kyfw.12306.cn"),
            ("Content-Type", "application/x-www-form-urlencoded"),
            ("Upgrade-Insecure-Requests", "1"),
            ("User-Agent",
             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"),
            ("Accept",
             "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"),
            ("Sec-Fetch-Site", "same-origin"),
            ("Sec-Fetch-Mode", "navigate"),
            ("Sec-Fetch-User", "?1"),
            ("Sec-Fetch-Dest", "document"),
            ("Referer",
             "https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc&fs=%E9%83%91%E5%B7%9E%E4%B8%9C,ZAF&ts=%E8%A5%BF%E5%AE%89,XAY&date=2025-08-01&flag=N,N,Y"),
            ("Accept-Encoding", "gzip, deflate, br, zstd"),
            ("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"),
            ("Cookie", cookie_str)
        ])
        data = {"_json_att": ""}
        try:
            with httpx.Client(http1=True) as client:
                ret = client.post(init_dc_url, headers=headers, data=data)
                ret.raise_for_status()
                content_type = ret.headers.get("content-type", "")
                if "text/html" in content_type:    # HTML
                    print(">>> Order confirmation page initialized successfully!")
                    return ret.text
                elif "application/json" in content_type:
                    result = ret.json()
                    if result.get("status"):
                        print(">>> Order confirmation page initialized successfully!")
                        return result
                    else:
                        print(f">>> Order confirmation page initialization failed: {result.get('messages')}")
                        return None
                else:
                    print(f"The order confirmation page returned an unknown error: {content_type}")
                    return ret.text
        except Exception as e:
            if "302" in str(e):
                print(">>> Login again...")
            return False

    @staticmethod
    def _html_parse(html_text):
        repeat_submit_token = re.search(r"globalRepeatSubmitToken\s*=\s*'(.+?)'", html_text)      # REPEAT_SUBMIT_TOKEN
        key_check_isChange = re.search(r"'key_check_isChange'\s*:\s*'(.+?)'", html_text)          # key_check_isChange
        train_location = re.search(r"'train_location'\s*:\s*'(.+?)'}", html_text)                 # train_location, in general, it is H1
        ticketStr = re.search(r"'leftTicketStr':'(.*?)'", html_text)                              # TicketStr
        train_no = re.search(r"'train_no':'(.*?)'", html_text)                                    # train_no

        repeat_submit_token = repeat_submit_token.group(1) if repeat_submit_token else ""
        key_check_isChange = key_check_isChange.group(1) if key_check_isChange else ""
        train_location = train_location.group(1) if train_location else ""
        ticketStr = ticketStr.group(1) if ticketStr else ""
        train_no = train_no.group(1) if train_no else ""

        return repeat_submit_token, key_check_isChange, train_location, ticketStr, train_no

    def _extract_params(self, cookie_str):
        dc_html_json = self._init_dc(cookie_str)
        dc_html = json.dumps(dc_html_json)
        return self._html_parse(dc_html)

    def _get_passenger_info(self, repeat_submit_token, cookie_str):
        headers = OrderedDict([
            ("Host", "kyfw.12306.cn"),
            ("Connection", "keep-alive"),
            ("sec-ch-ua-platform", "\"Windows\""),
            ("X-Requested-With", "XMLHttpRequest"),
            ("User-Agent",
             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"),
            ("Accept", "*/*"),
            ("sec-ch-ua", "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Microsoft Edge\";v=\"138\""),
            ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
            ("sec-ch-ua-mobile", "?0"),
            ("Origin", "https://kyfw.12306.cn"),
            ("Sec-Fetch-Site", "same-origin"),
            ("Sec-Fetch-Mode", "cors"),
            ("Sec-Fetch-Dest", "empty"),
            ("Referer", "https://kyfw.12306.cn/otn/confirmPassenger/initDc"),
            ("Accept-Encoding", "gzip, deflate, br, zstd"),
            ("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"),
            ("Cookie", cookie_str)
        ])
        data = {"_json_att": "", "REPEAT_SUBMIT_TOKEN": repeat_submit_token}
        try:
            with httpx.Client(http1=True) as client:
                ret = client.post(passenger_url, headers=headers, data=data)
                ret.raise_for_status()
                result = ret.json()
                if result.get("status"):
                    print(">>> Passenger information retrieved successfully!")
                    return result
                else:
                    print(f">>> Failed to obtain passenger information: {result.get('messages')}")
                    return False
        except Exception as e:
            print(f">>> An exception occurred while retrieving passenger information.: {e}")
            return False

    def _get_passenger_strings(self, config, response_info):
        passengers = config.get("passengers", {}).get("name", "")
        seat_type = self.SEAT_TYPE_MAP[config.get("ticket_info", {}).get('seat_priority')[0]]
        all_passengers_info = response_info["data"]["normal_passengers"]
        for passenger_info in all_passengers_info:
            if passenger_info['passenger_name'] == passengers:
                Ticket_type = "0"                                                  # 票类型 0 成人 1 儿童 2 学生 3 军人
                passenger_type = passenger_info["passenger_type"]                  # 乘客类型 1 成人
                passenger_name = passenger_info["passenger_name"]                  # 乘客姓名
                passenger_id_type_code = passenger_info["passenger_id_type_code"]  # 证件类型 1
                passenger_id_no = passenger_info["passenger_id_no"]                # 证件号码 411
                mobile_no = passenger_info["mobile_no"]                            # 手机号
                mysticalparameter = "N"                                            # 不知名参数 默认为N
                allEncStr = passenger_info["allEncStr"]                            # 加密字符串
                passengerTicketStr = f"{seat_type},{Ticket_type},{passenger_type},{passenger_name},{passenger_id_type_code},{passenger_id_no},{mobile_no},{mysticalparameter},{allEncStr}"
                oldPassengerStr = f"{passenger_name},{passenger_id_type_code},{passenger_id_no},1_"
                print(">>> Verification of pre-filled passenger information successful!")
                return passengerTicketStr, oldPassengerStr
            else:
                print(">>> Verify the pre-filled passenger information...")
        print(">>> Passenger information not filled out...")
        print(">>> Clear cookies and exit...")
        self._cookies_clean()
        exit()

    def _check_order_info(self, passengerTicketStr, oldPassengerStr, repeat_submit_token, cookie_str):
        headers = OrderedDict([
            ("Host", "kyfw.12306.cn"),
            ("Connection", "keep-alive"),
            ("sec-ch-ua-platform", "\"Windows\""),
            ("X-Requested-With", "XMLHttpRequest"),
            ("User-Agent",
             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"),
            ("Accept", "application/json, text/javascript, */*; q=0.01"),
            ("sec-ch-ua", "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Microsoft Edge\";v=\"138\""),
            ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
            ("sec-ch-ua-mobile", "?0"),
            ("Origin", "https://kyfw.12306.cn"),
            ("Sec-Fetch-Site", "same-origin"),
            ("Sec-Fetch-Mode", "cors"),
            ("Sec-Fetch-Dest", "empty"),
            ("Referer", "https://kyfw.12306.cn/otn/confirmPassenger/initDc"),
            ("Accept-Encoding", "gzip, deflate, br, zstd"),
            ("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"),
            ("Cookie", cookie_str)
        ])
        data = {
            "cancel_flag": "2",
            "bed_level_order_num": "000000000000000000000000000000",
            "passengerTicketStr": passengerTicketStr,
            "oldPassengerStr": oldPassengerStr,
            "tour_flag": "dc",
            "whatsSelect": "1",
            "sessionId": "",
            "sig": "",
            "scene": "nc_login",
            "_json_att": "",
            "REPEAT_SUBMIT_TOKEN": repeat_submit_token
        }
        try:
            ret = self.session.post(check_order_url, data=data, headers=headers, timeout=10)
            ret.raise_for_status()
            result = ret.json()
            if result.get("status"):
                print(">>> Order information check passed!")
                return True
            else:
                print(f">>> Order information check failed: {result.get('messages')}")
                return False
        except Exception as e:
            print(f">>> Exception in the order information check: {e}")
            return False

    def _get_true_cookies(self, ticket_config):
        cookies = self._read_cookies_file()
        if self.cookies_file and os.path.exists(self.cookies_file):
            cookies_fixed = os.path.basename(self.cookies_file).rstrip(".json") + "_true.json"
        else:
            cookies_fixed = "cookies_ture.json"
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
        train_date = ticket_config.get("train_date")
        from_station = ticket_config.get("from_station")
        to_station = ticket_config.get("to_station")
        back_train_date = date.today().strftime("%Y-%m-%d")

        from_station_code, to_station_code = self.station_info.get(from_station, ""), self.station_info.get(to_station, "")
        from_cookie_val = f"{urllib.parse.quote(from_station)},{from_station_code}"
        to_cookie_val = f"{urllib.parse.quote(to_station)},{to_station_code}"

        cookies_dict["_jc_save_fromDate"] = train_date
        cookies_dict["_jc_save_fromStation"] = from_cookie_val
        cookies_dict["_jc_save_toStation"] = to_cookie_val
        cookies_dict["_jc_save_toDate"] = back_train_date
        cookies_dict["_jc_save_wfdc_flag"] = "dc"
        cookies_dict["_jc_save_showIns"] = "true"

        cookie_str = '; '.join([f'{k}={v}' for k, v in cookies_dict.items()])
        with open(os.path.join(ROOT_DIR, "cookies", cookies_fixed), "w") as f:
            json.dump(cookie_str, f)
        return cookie_str

    def _confirm_queue(self, passengerTicketStr, oldPassengerStr, repeat_submit_token, key_check_isChange, train_location, ticketStr, cookies_str):
        headers = OrderedDict([
            ("Host", "kyfw.12306.cn"),
            ("Connection", "keep-alive"),
            ("sec-ch-ua-platform", "\"Windows\""),
            ("X-Requested-With", "XMLHttpRequest"),
            ("User-Agent",
             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0"),
            ("Accept", "application/json, text/javascript, */*; q=0.01"),
            ("Sec-Ch-Ua", "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"140\", \"Microsoft Edge\";v=\"140\""),
            ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
            ("Content-Length", "682"),
            ("sec-ch-ua-mobile", "?0"),
            ("Origin", "https://kyfw.12306.cn"),
            ("Sec-Fetch-Site", "same-origin"),
            ("Sec-Fetch-Mode", "cors"),
            ("Sec-Fetch-Dest", "empty"),
            ("Referer", "https://kyfw.12306.cn/otn/confirmPassenger/initDc"),
            ("Accept-Encoding", "gzip, deflate, br, zstd"),
            ("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"),
            ("Cookie", cookies_str)
        ])
        data = {
            "passengerTicketStr": passengerTicketStr,
            "oldPassengerStr": oldPassengerStr,
            "purpose_codes": "00",
            "key_check_isChange": key_check_isChange,
            "leftTicketStr": ticketStr,
            "train_location": train_location,
            "choose_seats": "",
            "seatDetailType": "000",
            "is_jy": "N",
            "is_cj": "Y",
            "encryptedData": "",
            "whatsSelect": "1",
            "roomType": "00",
            "dwAll": "N",
            "_json_att": "",
            "REPEAT_SUBMIT_TOKEN": repeat_submit_token
        }

        try:
            ret = self.session.post(confirm_url, data=data, headers=headers, timeout=10)
            ret_data = ret.json().get("data", {})                # 解析返回 JSON
            submit_status = ret_data.get("submitStatus", None)
            if submit_status:
                print(">>> Successfully queued for ticket purchase!")
                return True
            else:
                print(">>> Failed to queue for ticket purchase...")
                return False
        except Exception as e:
            print(f"An exception occurred while purchasing tickets: {e}")
            return False

    def purchase(self, tickets):
        if not tickets:
            print(">>> No train_date tickets to purchase, exit...")
            exit()
        ticket_config = self.config.get("ticket_info", {})
        from_station = ticket_config.get("from_station")
        to_station = ticket_config.get("to_station")
        train_date = ticket_config.get("train_date")
        back_train_date = date.today().strftime("%Y-%m-%d")

        self._update_cookies(is_test=False)
        cookies_str = self._get_true_cookies(ticket_config)

        for ticket in [tickets[0]]:
            ticket_info = {
                "secret_str": ticket["secretStr"],
                "train_date": train_date,
                "back_train_date": back_train_date,
                "from_station": from_station,
                "to_station": to_station,
                "bed_level_info": ticket['bed_level_info'],
                "cookies": cookies_str
            }

            start_time = time.time()
            i = 0
            while True:
                submit_status = self._submit_order(ticket_info)
                if submit_status == "302":
                    print(f">>> {i}-th: Identity information expired, please log in again...")
                    if not self._login(i):
                        print(">>> Re-login failed. Existing cookies were kept. Exit...")
                        sys.exit(1)
                    self._update_cookies(is_test=False)
                    _is_valid = self._valid_user_login()
                    if not _is_valid:
                        print(">>> Login failed, exit")
                        sys.exit(1)
                    cookies_str = self._get_true_cookies(ticket_config)
                    ticket_info["cookies"] = cookies_str
                elif submit_status == "203":
                    print(f">>> {i}-th: Order request failed, restart order request")
                else:
                    print(f">>> {i}-th: Order request success!")
                    break
                i += 1

            repeat_submit_token, key_check_isChange, train_location, ticketStr, train_no = self._extract_params(cookies_str)

            response_info = self._get_passenger_info(repeat_submit_token, cookies_str)
            passengerTicketStr, oldPassengerStr = self._get_passenger_strings(self.config, response_info)

            _is_valid = self._check_order_info(passengerTicketStr, oldPassengerStr, repeat_submit_token, cookies_str)
            if not _is_valid:
                exit()

            max_times = 5
            _is_success = False
            for i in range(max_times):
                print(f">>> Processing the {i}-th purchase...")
                _is_success = self._confirm_queue(passengerTicketStr, oldPassengerStr, repeat_submit_token, key_check_isChange, train_location, ticketStr, cookies_str)
                if _is_success:
                    print(">>> Purchase successful, please check your order and make the payment!!!")
                    break
            if not _is_success:
                print(f">>> Purchase failed {max_times} times, exiting...")

            end_time = time.time()
            print(f">>> Duration: {end_time - start_time:.5f} seconds.")
            print(">>> Exit!")
            break

    def run(self, buy=False):
        ticket_config = self.config.get("ticket_info", {})
        test_date = ticket_config.get("train_date_test")
        train_date = ticket_config.get("train_date")
        train_time_str = ticket_config.get("train_time", "00:00:00")
        release_time = datetime.strptime(train_time_str, "%H:%M:%S").time()
        plan = plan_run(buy, train_date, date.today(), datetime.now().time(), release_time)

        if plan["query_test_date"]:
            tickets = self.query_tickets(test_date)
            if tickets is None:
                print(f">>> Query failed for test date {test_date}, exit...")
                sys.exit(1)
            if not tickets:
                print(f">>> No tickets for test date {test_date}, exit...")
                sys.exit(1)
            filtered_tickets = self.tickets_filter.filter(tickets)
            print(f">>> Test-date {test_date} qualified tickets:", [t["train_code"] for t in filtered_tickets])
            if not plan["query_train_date"]:
                print(f">>> {train_date} is not on sale yet. dry-run stops here (no submit).")
                return

        if plan["wait_for_release"]:
            print(f">>> Release Time: {release_time}, waiting...")
            while datetime.now().time() < release_time:
                time.sleep(0.05)
            print(f">>> Arrived at the scheduled time: {datetime.now().time()}, start...")

        if plan["query_train_date"]:
            time.sleep(1.2)
            real_tickets = self.query_tickets(train_date)
            if real_tickets is None:
                print(f">>> Query failed for {train_date} (timeout/network). Will not use test-date secretStr. Exit...")
                sys.exit(1)
            if not real_tickets:
                print(f">>> No tickets for {train_date}. Will not use test-date secretStr. Exit...")
                sys.exit(1)
            filtered_real = self.tickets_filter.filter(real_tickets)
            print(f">>> train_date {train_date} qualified tickets:", [t["train_code"] for t in filtered_real])
        else:
            filtered_real = None

        if not plan["purchase"]:
            print(">>> dry-run: stop before submit. Pass --buy to purchase.")
            return

        _is_valid = self.valid_cookies()
        if not _is_valid:
            print(">>> Verification failed, exit...")
            sys.exit(1)
        self.purchase(filtered_real)


@click.command()
@click.option("-c", "--cookies", type=str, default="cookes")
@click.option("--buy", is_flag=True, default=False, help="Actually submit/confirm. Default is dry-run.")
def main(cookies, buy):
    cookies_file_name = cookies
    cookies_file = os.path.join(ROOT_DIR, "cookies", f"{cookies_file_name}.json")
    client = Client(cookies_file)
    client.run(buy=buy)


if __name__ == "__main__":

    main()
