# i12306
Learning for Webspider...

用于12306抢票，登录使用`selenium`进行手动登录保存`cookies`，随后使用`requests`发出请求

# Install
```bash
conda create -n xxx python=3.10
pip install -r requirement.txt
```

# Run
```bash
python main.py --buy
```
`--buy` 参数用于决定是否确认订单购买，若不加该参数，则仅用于查询

# File
`main.py` 程序入口 \
`utils` 下保存主要工具脚本
- `login.py` 用于登录，可单独执行
- `requests_utils.py` 用于抢票，发起请求

`cookies` 保存用户cookies文件 \
`config/config.yaml` 需要提前配置 \
`data/station_name_map.json` 保存12306高铁站的编码映射

# Config
根据个人账号信息修改`config/config.yaml`文件内容, 仅适用于成人票（学生票等暂未实现）

```bash
passengers:
  name: "张三"

ticket_info:
  train_date_test: "2026-08-30"      # 有票且相同车次的一天，用于提前得到车票列车信息        日期格式：YYYY-MM-DD

  train_date: "2026-08-31"           # 真正要购买票的日期 也就是要抢的那一天的票

  train_time: "20:00:00"       # 开售时间

  from_station: "上海虹桥"       # 出发地

  to_station: "温州南"           # 目的地

  preferred_trains:
    - G7461                     # 车次号
#  candidate_trains:
#    - G7591
  seat_priority:
    - 二等座                     # 期望的座位类型， [商务座, 一等座, 二等座, 硬卧, 软卧, 无座, 硬座]
```

# Case
```bash
>>> Start the program...
>>> --buy enabled: will submit after querying train_date
>>> login success!
>>> Release Time: 20:00:00, waiting...
>>> Arrived at the scheduled time: 20:00:00.015709, start...
>>> Querying tickets from 上海虹桥 to 温州南 on 2026-08-31...
>>> status code for querying: 200
>>> Querying success!
>>> Querying Tickets:
>>> A total of 97 trains were queried...
>>> train_date 2026-08-31 qualified tickets: ['G7349']
>>> Identity verification successful!
>>> Ticket purchase begins...
>>> Successfully submitted ticket purchase request!
>>> 0‑th: Order request success!
>>> Order confirmation page initialized successfully!
>>> Passenger information retrieved successfully!
>>> Verification of pre‑filled passenger information successful!
>>> Order information check passed!
>>> Processing the 0‑th purchase...
>>> Successfully queued for ticket purchase!
>>> Purchase successful, please check your order and make the payment!!!!
>>> Duration: 0.93243 seconds.
>>> Exit!
>>> Run Program Successfully!
```
运行成功如上所示...

# Reference
- [https://github.com/WizardHeHeJun/12306_go](https://github.com/WizardHeHeJun/12306_go)
- [https://github.com/mipha777/12306](https://github.com/mipha777/12306)
