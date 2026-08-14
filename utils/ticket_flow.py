from datetime import date, datetime, timedelta


PRESALE_INCLUSIVE_DAYS = 14  # 15-day window including today: today .. today+14


def in_sale_window(train_date_str, today=None):
    today = today or date.today()
    train_date = datetime.strptime(train_date_str, "%Y-%m-%d").date()
    return today <= train_date <= today + timedelta(days=PRESALE_INCLUSIVE_DAYS)


def plan_run(buy, train_date, today, now_time, release_time):
    """Decide query/wait/purchase. Never purchase with test-date tickets."""
    buy = bool(buy)
    on_sale = in_sale_window(train_date, today)
    if buy:
        return {
            "query_test_date": False,
            "wait_for_release": now_time < release_time,
            "query_train_date": True,
            "purchase": True,
        }
    return {
        "query_test_date": True,
        "wait_for_release": False,
        "query_train_date": on_sale,
        "purchase": False,
    }
