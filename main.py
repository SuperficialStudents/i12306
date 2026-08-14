import subprocess
import click
import os
import sys

CURRENT_PATH = os.path.abspath(__file__)
ROOT_DIR = os.path.dirname(CURRENT_PATH)


@click.command()
@click.option("-c", "--cookies", type=str, default=None)
@click.option("--buy", is_flag=True, default=False, help="Actually submit/confirm. Default is dry-run.")
def main(cookies, buy):
    print(">>> Start the program...")
    if buy:
        print(">>> --buy enabled: will submit after querying train_date")
    else:
        print(">>> dry-run: will not submit or queue")
    cookies_file = os.path.join(ROOT_DIR, "cookies", f"{cookies}.json")
    if cookies and os.path.exists(cookies_file):
        # 不需要login
        pass
    elif cookies is None and os.path.exists(os.path.join(ROOT_DIR, "cookies", "cookies.json")):
        pass
    else:
        result = subprocess.run([sys.executable, os.path.join(ROOT_DIR, "utils", "login.py")])
        if result.returncode == 0:
            print(">>> Login successfully!")
        else:
            print(">>> Failed to login...")
            exit()
    cmd = [sys.executable, os.path.join(ROOT_DIR, "utils", "requests_utils.py")]
    if cookies:
        cmd.extend(["--cookies", cookies])
    if buy:
        cmd.append("--buy")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(">>> Run Program Successfully!")
    else:
        print(">>> Filed to run...")
        exit()


if __name__ == "__main__":
    main()
