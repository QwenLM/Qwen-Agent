import signal
import subprocess

if __name__ == '__main__':
    process1 = subprocess.Popen(['python', 'main.py'])
    process2 = subprocess.Popen(['python', 'app.py'])
    process3 = subprocess.Popen(['python', 'app_in_browser.py'])

    def signal_handler(sig, frame):
        process1.terminate()
        process2.terminate()
        process3.terminate()

    signal.signal(signal.SIGINT, signal_handler)

    process1.wait()
    process2.wait()
    process3.wait()
