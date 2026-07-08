import sys

class JARVISKernel:
    def __init__(self):
        self.running = True

    def start(self):
        print("JARVIS: Система запущена")
        print("Напиши 'помощь'")

        while self.running:
            cmd = input(">>> ").lower()

            if cmd == "помощь":
                print("JARVIS: команды: помощь, выход")

            elif cmd == "выход":
                print("JARVIS: выключение")
                self.running = False
                sys.exit()

            else:
                print("JARVIS: неизвестная команда")


if __name__ == "__main__":
    jarvis = JARVISKernel()
    jarvis.start()