# i12306
用于12306抢票，登录使用`selenium`进行手动登录保存`cookies`，随后使用`requests`发出请求

# Install
```bash
conda create -n xxx python=3.10.8
pip install -r requirement.txt
```

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
  train_date_test: "2025-09-21"      # 有票且相同车次的一天，用于提前得到车票列车信息        日期格式：YYYY-MM-DD

  train_date: "2025-09-22"           # 真正要购买票的日期 也就是要抢的那一天的票

  train_time: "09:30:00"       # 开售时间

  from_station: "上海虹桥"       # 出发地

  to_station: "温州南"           # 目的地

  preferred_trains:
    - G7461                     # 车次号
#  candidate_trains:
#    - G7591
  seat_priority:
    - 二等座                     # 期望的座位类型， [商务座, 一等座, 二等座, 硬卧, 软卧, 无座, 硬座]

```

# Reference
- [https://github.com/WizardHeHeJun/12306_go](https://github.com/WizardHeHeJun/12306_go)
- [https://github.com/mipha777/12306](https://github.com/mipha777/12306)
