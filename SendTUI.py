#!/usr/bin/env python3
import sys
import time
import serial
import glob
import argparse
import subprocess

from rich.console import Console
from rich.progress import Progress, BarColumn, TimeRemainingColumn
from rich.prompt import Prompt
from rich.table import Table

console = Console()
FINISHED_RESPONSE = "ok"

def send_notification(message):
    subprocess.Popen(['notify-send', message])
    return

class SerialCommunicator:
    def __init__(self, port, baudrate=115200, timeout=1):
        try:
            self.serial_port = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(1)
            self.serial_port.reset_input_buffer()
        except Exception as e:
            console.print(f"[red]Error opening port {port}: {e}[/red]")
            sys.exit(1)

    def send(self, command: str):
        self.serial_port.reset_output_buffer()
        self.serial_port.reset_input_buffer()
        if not command.endswith("\n"):
            command += "\n"
        self.serial_port.write(command.encode())

    def read_line(self) -> str:
        try:
            return self.serial_port.readline().decode(errors="ignore")
        except Exception:
            return ""

    def wait_for_ok(self) -> str:
        response = ""
        start_time = time.time()
        while True:
            response_line = self.read_line()
            response += response_line
            if FINISHED_RESPONSE in response:
                break
            if time.time() - start_time > 10:
                break
        return response

    def send_and_wait(self, command: str) -> str:
        start = time.time()
        self.send(command)
        response = self.wait_for_ok()
        elapsed = time.time() - start
        if elapsed > 8:
            console.log(f"[yellow]Warning: Command '{command.strip()}' took {elapsed:.2f} seconds to execute.[/yellow]")
        return response

    def close(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

def list_serial_ports():
    return glob.glob('/dev/ttyUSB*')

def run_gcode_once(serial_comm: SerialCommunicator, file_path: str):
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        console.print(f"[red]Failed to open file: {e}[/red]")
        return False

    total_lines = len(lines)
    console.print(f"[green]Uploading {total_lines} G-code commands from {file_path}[/green]")
    time.sleep(1)

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        TimeRemainingColumn(),
        transient=True
    ) as progress:
        task = progress.add_task("[green]Uploading G-code...", total=total_lines)
        for line in lines:
            response = serial_comm.send_and_wait(line)
            if len(response) > 5:
                console.log(f"[blue]Response:[/blue] {response.strip()}")
            progress.advance(task)

    console.print("[bold green]Run finished.[/bold green]")
    return True

def repeat_controller(serial_comm: SerialCommunicator, file_path: str, repeat: bool, repeat_count: int, wait_enter: bool, wait_seconds: float):
    run_number = 1

    while True:
        console.print(f"[cyan]Starting run {run_number}[/cyan]")
        ok = run_gcode_once(serial_comm, file_path)
        send_notification(f"Run {run_number} finished")

        if not ok:
            console.print("[red]Error during run. Aborting repeats.[/red]")
            return

        if not repeat:
            return

        if repeat_count > 0 and run_number >= repeat_count:
            return

        if wait_enter:
            console.print("Press Enter to begin next run...")
            input()
        else:
            console.print(f"Waiting {wait_seconds} seconds before next run...")
            time.sleep(wait_seconds)

        run_number += 1

def interactive_mode(serial_comm: SerialCommunicator):
    console.print("[bold cyan]Entering interactive mode. Type 'exit' or 'quit' to leave.[/bold cyan]")
    while True:
        command = Prompt.ask("Enter G-code command")
        if command.lower() in ("exit", "quit"):
            break
        response = serial_comm.send_and_wait(command)
        console.print(f"[blue]Response:[/blue] {response.strip()}")

def main():
    parser = argparse.ArgumentParser(description="G-code Plotter CLI Utility with repeat support")

    parser.add_argument("--port", type=str)
    parser.add_argument("--file", type=str)

    parser.add_argument("--repeat", action="store_true", help="Repeat indefinitely until stopped")
    parser.add_argument("--repeat-count", type=int, default=0, help="Repeat a fixed number of times")

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--wait-enter", action="store_true", help="Require pressing Enter between runs")
    mode_group.add_argument("--wait-seconds", type=float, help="Wait N seconds between runs instead of prompting")

    args = parser.parse_args()

    if args.port:
        selected_port = args.port
    else:
        ports = list_serial_ports()
        if not ports:
            console.print("[red]No serial ports found.[/red]")
            sys.exit(1)
        if len(ports) == 1:
            selected_port = ports[0]
        else:
            table = Table(title="Available Serial Ports")
            table.add_column("Index", style="cyan", no_wrap=True)
            table.add_column("Port", style="magenta")
            for i, port in enumerate(ports):
                table.add_row(str(i), port)
            console.print(table)
            index = Prompt.ask("Select port index", default="0")
            try:
                selected_port = ports[int(index)]
            except Exception:
                console.print("[red]Invalid selection.[/red]")
                sys.exit(1)

    serial_comm = SerialCommunicator(selected_port)
    console.print(f"[green]Connected to {selected_port}[/green]")

    try:
        if args.file:
            repeat = args.repeat or args.repeat_count > 0
            wait_enter = args.wait_enter or (args.wait_seconds is None)
            wait_seconds = args.wait_seconds if args.wait_seconds is not None else 0

            repeat_controller(serial_comm, args.file, repeat, args.repeat_count, wait_enter, wait_seconds)
        else:
            interactive_mode(serial_comm)
    except KeyboardInterrupt:
        console.print("[red]Interrupted by user.[/red]")
    finally:
        serial_comm.close()
        send_notification("Job finished")
        console.print("[yellow]Serial connection closed.[/yellow]")

if __name__ == "__main__":
    main()
