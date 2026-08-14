import json
import urllib.parse
import yaml
import os

CURRENT_PATH = os.path.abspath(__file__)
PARENT_DIR = os.path.dirname(CURRENT_PATH)
ROOT_DIR = os.path.dirname(PARENT_DIR)


class TicketFilter:
    def __init__(self, config_file=None):
        self.config = self._get_config(config_file)
        self.ticket_info = self.config.get("ticket_info", {})
        self.station_info = self._get_station_info()

    @staticmethod
    def _get_config(config_file=None):
        if config_file and os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        else:
            with open(os.path.join(ROOT_DIR, "config", "config.yaml"), "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

    @staticmethod
    def _get_station_info():
        with open(os.path.join(ROOT_DIR, "data", "station_name_map.json"), "r", encoding="utf-8") as f:
            station_info = json.load(f)
        return station_info

    def filter(self, tickets):
        if not tickets:
            print(">>> No tickets to filter.")
            exit()
        preferred_trains = self.ticket_info.get("preferred_trains", [])
        seat_priority = self.ticket_info.get("seat_priority", [])
        # window_seat = self.ticket_info.get("window_seat", True)

        from_station = self.ticket_info.get("from_station")
        from_station_code = self.station_info.get(from_station, "")

        if preferred_trains:
            preferred_trains_set = set(preferred_trains)
            tickets = [t for t in tickets if any(trains in t for trains in preferred_trains_set) and from_station_code in t]
        tickets = self.process(tickets)

        filtered_tickets = [t for t in tickets if self._meet_seat_priority(t, seat_priority)]

        if not len(filtered_tickets):
            print(f"There is no suitable train number available for your configure.")
            exit()
        return filtered_tickets

    @staticmethod
    def _meet_seat_priority(ticket, seat_priority):
        if not seat_priority:
            return True
        for seat in seat_priority:
            val = ticket.get(seat, "-")
            if val not in ["-", "", None]:
                return True
        return False

    @staticmethod
    def process(tickets):
        """
        ['Yhup4L7WMkkY322kLW8wl1OdsYymhbChImsyDVttWbcfy81%2FIfi8uerDG3DLRbzHdBC0LjqZnEVU%0APmEqW2Z1J8LUI33dZVGk8ZvKhUduNrEWjrrZCZJMiOpq3lzAfG4uKhvw72SXsaGWYwz7j6TcH6s%0AnEIul9b5Vjb24ENTi8sygql7jBRX0xOI1HrqJ4MkBUcMb15bfmckXwTBw%2BLntEjCVjZjR9zkGYpu%0A0pr%2FENUOuP9%2BP%2FX1VUoGxXI77zFdnh7xJ8cAKGZVAO74QgPrLVdPqRehed304i94u7j2WDB80H5o%0AC2gUA2HVlSWHTQ3L15CmwVPQGt5IPYoJhXWAa3LhnaGXAR2x8CRJmPOsR%2FY%3D',
        '预订',
        '5l000G733101',
        'G7331',
        'AOH', 'RAH', 'AOH','VRH',
        '06:14', '09:29', '03:15',
        'Y',
        'Wl1f51I8qdlKKaWkM2i1AkzlaPXbtg9ahG%2FP4gNu%2FE4PNLDwn%2FTWdCBITKA%3D',
        '20250910',
        '3', 'HZ', '01', '07', '1', '0', '', '', '', '', '', '', '无', '', '', '', '有', '11', '4', '', '90M0O0W0', '9MOO', '1', '0', '', '9064300004M031250011O018950021O018953000', '0', '', '', '', '', '1', '0#0#0#0#z#0#z#z', '', '', 'CHN,CHN', '', '', 'N#N#', '', '90081M0082O0080W0080', '202508271345', '']
        """
        tickets_info = []
        for ticket in tickets:
            items = ticket.split("|")
            train_info = {
                "secretStr": urllib.parse.unquote(items[0]),
                "train_no": items[2],
                "train_code": items[3],
                "origin_station_code": items[4],
                "terminal_station_code": items[5],
                "from_station_code": items[6],
                "to_station_code": items[7],
                "start_time": items[8],
                "arrive_time": items[9],
                "duration": items[10],
                "is_bookable" : items[11],
                "软卧": items[23] or "-",
                "无座": items[26] or "-",
                "硬卧": items[28] or "-",
                "硬座": items[29] or "-",
                "二等座": items[30] or "-",
                "一等座": items[31] or "-",
                "商务座": items[32] or "-",
                "bed_level_info": items[53],
            }
            tickets_info.append(train_info)
        return tickets_info


if __name__ == "__main__":
    pass

