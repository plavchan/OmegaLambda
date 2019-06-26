import logging
import time


def CameraLogging(self):
    ch = logging.Camera(time.strftime("log-%Y-%m-%d.log"))
    ch.logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)-10s %(processName)s %(name)s %(message)s')
    # filename should not be "w" because it will rewrite every time and lose previous logs
    logging.addHandler(ch)

    logging.debug("debug")
    logging.info("info")
    logging.warning("warning")
    logging.error("error")
    logging.critical("critical")
