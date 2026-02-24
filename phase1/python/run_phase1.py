import argparse
import time

from signal_watcher import run_once


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="../config/config.json")
    parser.add_argument("--loop", action="store_true", help="Run every 60 seconds")
    args = parser.parse_args()

    if args.loop:
        while True:
            try:
                run_once(args.config)
            except Exception as e:
                print(f"[ERROR] {e}")
            time.sleep(60)
    else:
        run_once(args.config)


if __name__ == "__main__":
    main()
