"""Measures how long PicoOS takes to echo a typed character under CPU load."""

import os
import select
import statistics
import subprocess
import time


PROMPT = b"PicoOS> "
SAMPLES_PER_INTERVAL = 20
INTERVALS = [1000, 3000, 5000, 10000]


class PicoOS:
    """Starts PicoOS and exchanges bytes with its terminal."""

    def __init__(self):
        self.process = subprocess.Popen(
            ["reti_emulator", "-w", "0", "-r", "262144", "-O", "../kernel/kernel.reti"],
            cwd="binary",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.output = bytearray()

    def send(self, value):
        """Sends bytes to PicoOS immediately."""
        self.process.stdin.write(value)
        self.process.stdin.flush()

    def read_until(self, value, start, timeout=120):
        """Returns when output after start contains value."""
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            if self.output.find(value, start) >= 0:
                return
            readable, _, _ = select.select([self.process.stdout], [], [], 0.1)
            if readable:
                self.output.extend(os.read(self.process.stdout.fileno(), 4096))
        raise RuntimeError(f"Timed out waiting for {value!r}")

    def command(self, value):
        """Runs one shell command and waits for the next prompt."""
        start = len(self.output)
        self.send(value.encode("ascii") + b"\r")
        self.read_until(PROMPT, start)

    def close(self):
        """Stops the emulator process."""
        self.process.kill()
        self.process.wait()


def measure_interval(picoos, interval):
    """Returns the median echo delay for one timer interval."""
    picoos.command(f"timer-set.bin {interval}")
    picoos.command("timer-spin.bin &")
    samples = []

    for sample in range(SAMPLES_PER_INTERVAL):
        character = bytes([ord("a") + sample])
        output_start = len(picoos.output)
        started = time.perf_counter_ns()
        picoos.send(character)
        picoos.read_until(character, output_start)
        samples.append((time.perf_counter_ns() - started) / 1_000_000)

    picoos.command("kill.bin $!")
    return statistics.median(samples)


def main():
    """Prints one measured character delay for every candidate interval."""
    picoos = PicoOS()
    try:
        picoos.read_until(PROMPT, 0)
        for interval in INTERVALS:
            delay = measure_interval(picoos, interval)
            print(f"{interval} instructions: {delay:.1f} ms")
    finally:
        picoos.close()


if __name__ == "__main__":
    main()
