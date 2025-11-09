import cfg
import sys

log = cfg.set_logger()


def main() -> int:
    

    

    return 0

if __name__ == "__main__":
    rc = cfg.run_and_capture(main, cfg.NUM_LOG_FILES)
    sys.exit(rc)