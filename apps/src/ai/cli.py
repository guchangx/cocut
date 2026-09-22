import sys
from ai.session import Session, DEFAULT_IMAGE_USER_PROMPT
import time
import threading
from itertools import cycle


class Spinner: 
    def __init__(self, message: str = "thinking..."):
        self.message = message
        self._stop_event = threading.Event()
        self._thread = None

    def _spin(self):
        spinner = cycle(["⠏", "⠛", "⠹", "⢸", "⣰", "⣤", "⣆", "⡇"])
        while self._stop_event.is_set():
            sys.stdout.write(f"\r🤖 > \033[36m{next(spinner)} {self.message}\033[0m")
            sys.stdout.flush()
            time.sleep(0.1)

    def start(self):
        self._stop_event.set()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.clear()
        if self._thread:
            self._thread.join()
        sys.stdout.write("\r\033[K🤖 > ")
        sys.stdout.flush()

def run():

    try:
        session = Session()
    except ValueError as e:

        return

    while True:
        try:
            inputstr = input("\n👤 > ").strip()

            if not inputstr:
                continue

            if inputstr.lower() in ("exit", "quit", "bye", "/exit", "/quit", "/bye", "/q"):
                print("🤖 > Goodbye!")
                break
            elif inputstr == "/clear":
                session.clear()
                print("clear session done")
                continue
            elif inputstr.startswith("/img") or inputstr.startswith("/image"):
                parts = inputstr.split(maxsplit=2)
                if len(parts) < 2:
                    print("/image path message")
                    continue

                imgpath = parts[1]
                prompt = parts[2] if len(parts) > 2 else DEFAULT_IMAGE_USER_PROMPT + f"本地的图片路径： {imgpath}"
                stream = session.stream_with_image(prompt, imgpath)

            elif inputstr == "/tree":
                #TODO
                continue
            else:
                stream = session.stream(inputstr)

            spinner = Spinner()
            spinner.start()
            
            try:
                fchunk = next(stream)  
            except StopIteration:
                fchunk = ""
            finally:
                spinner.stop()

            print(fchunk, end="", flush=True)

            for chunk in stream:
                print(chunk, end="", flush=True)
            print()
            
        except KeyboardInterrupt:
            print("")
            break
        except Exception as e:
            print("have some problem!", e)