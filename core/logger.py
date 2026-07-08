class Logger:
    def _write(self, level, message):
        print(f"[{level}] {message}")

    def info(self, message):
        self._write("INFO", message)

    def warning(self, message):
        self._write("WARNING", message)

    def error(self, message):
        self._write("ERROR", message)
