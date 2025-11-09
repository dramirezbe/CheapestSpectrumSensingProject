import cfg
import sys


log = cfg.set_logger()

def main():
    log.warning("Module init_system running...")

    #Here code after a reboot

    log.warning("Module init_system finished...")
    return 0 

if __name__ == "__main__":
    rc = cfg.run_and_capture(main, cfg.NUM_LOG_FILES)
    sys.exit(rc)    