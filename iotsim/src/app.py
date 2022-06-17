import iotContainer as iot
import signal
import time

def main():
    container = iot.IOTContainer()
    signal.signal(signal.SIGTERM, container.signal_handler)
    signal.signal(signal.SIGINT, container.signal_handler)
    
    try:
        container.run()
    
        while True:
            time.sleep(0.5)

    except iot.ProgramKilled:
        container.shutdown()


if __name__== "__main__":
    main()

