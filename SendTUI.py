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
    subprocess.Popen(["notify-send", message])
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
            if time.time() - start_time > 20:
                break
        return response

    def send_and_wait(self, command: str) -> str:
        start = time.time()
        self.send(command)
        response = self.wait_for_ok()
        elapsed = time.time() - start

        if elapsed > 20:
            console.log(
                f"[yellow]Warning: Command '{command.strip()}' took {elapsed:.2f} seconds.[/yellow]"
            )
        return response

    def close(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()


def list_serial_ports():
    return glob.glob("/dev/ttyUSB*")


def run_gcode_once(serial_comm: SerialCommunicator, file_path: str):
    file_start = time.time()

    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        console.print(f"[red]Failed to open file: {e}[/red]")
        return False, 0

    total_lines = len(lines)
    console.print(f"[green]Uploading {total_lines} G-code commands from {file_path}[/green]")
    time.sleep(1)

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        TimeRemainingColumn(),
        transient=True,
    ) as progress:

        task = progress.add_task("[green]Uploading G-code...", total=total_lines)

        for line in lines:
            response = serial_comm.send_and_wait(line)
            if len(response) > 5:
                console.log(f"[blue]Response:[/blue] {response.strip()}")
            progress.advance(task)

    elapsed = time.time() - file_start
    console.print(f"[bold green]Run finished in {elapsed:.2f} seconds.[/bold green]")

    return True, elapsed


def run_gcode_batch(serial_comm: SerialCommunicator, file_list):
    batch_start = time.time()
    file_times = []

    for idx, file_path in enumerate(file_list, start=1):
        console.print(
            f"\n[bold magenta]=== File {idx}/{len(file_list)}: {file_path} ===[/bold magenta]"
        )

        ok, elapsed = run_gcode_once(serial_comm, file_path)
        send_notification(f"{file_path} finished")

        if not ok:
            console.print("[red]Error during batch. Stopping remaining files.[/red]")
            return False, 0, []

        file_times.append((file_path, elapsed))

    batch_elapsed = time.time() - batch_start

    console.print(
        f"\n[bold green]Batch finished successfully in {batch_elapsed:.2f} seconds.[/bold green]"
    )

    table = Table(title="Batch Timing Summary")
    table.add_column("File", style="cyan")
    table.add_column("Time (s)", style="magenta")

    for file_path, elapsed in file_times:
        table.add_row(file_path, f"{elapsed:.2f}")

    table.add_row("[bold]Batch Total[/bold]", f"[bold]{batch_elapsed:.2f}[/bold]")

    console.print(table)

    return True, batch_elapsed, file_times


def repeat_controller(
    serial_comm: SerialCommunicator,
    file_list,
    repeat: bool,
    repeat_count: int,
    wait_enter: bool,
    wait_seconds: float,
):
    run_number = 1
    overall_start = time.time()
    all_batch_times = []

    while True:
        console.print(f"\n[cyan]Starting batch run {run_number}[/cyan]")

        ok, batch_time, _ = run_gcode_batch(serial_comm, file_list)
        send_notification(f"Batch run {run_number} finished")

        if not ok:
            console.print("[red]Error during batch. Aborting repeats.[/red]")
            break

        all_batch_times.append(batch_time)

        if not repeat:
            break

        if repeat_count > 0 and run_number >= repeat_count:
            break

        if wait_enter:
            console.print("Press Enter to begin next batch...")
            input()
        else:
            console.print(
                f"Waiting {wait_seconds} seconds before next batch..."
            )
            time.sleep(wait_seconds)

        run_number += 1

    overall_elapsed = time.time() - overall_start

    console.print("\n[bold cyan]==== Overall Timing Summary ==== [/bold cyan]")

    table = Table(title="All Runs Summary")
    table.add_column("Run #", style="cyan")
    table.add_column("Batch Time (s)", style="magenta")

    for i, t in enumerate(all_batch_times, start=1):
        table.add_row(str(i), f"{t:.2f}")

    table.add_row("[bold]Grand Total[/bold]", f"[bold]{overall_elapsed:.2f}[/bold]")

    console.print(table)


def interactive_mode(serial_comm: SerialCommunicator):
    console.print(
        "[bold cyan]Entering interactive mode. Type 'exit' or 'quit' to leave.[/bold cyan]"
    )

    while True:
        command = Prompt.ask("Enter G-code command")
        if command.lower() in ("exit", "quit"):
            break
        response = serial_comm.send_and_wait(command)
        console.print(f"[blue]Response:[/blue] {response.strip()}")


def main():
    parser = argparse.ArgumentParser(
        description="G-code Plotter CLI Utility with repeat support"
    )

    parser.add_argument("--port", type=str)
    parser.add_argument("--file", nargs="+")
    parser.add_argument("positional_files", nargs="*")

    parser.add_argument("--repeat", action="store_true")
    parser.add_argument("--repeat-count", type=int, default=0)

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--wait-enter", action="store_true")
    mode_group.add_argument("--wait-seconds", type=float)

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
        file_list = []

        if args.file:
            file_list.extend(args.file)

        if args.positional_files:
            file_list.extend(args.positional_files)

        if file_list:
            repeat = args.repeat or args.repeat_count > 0
            wait_enter = args.wait_enter or (args.wait_seconds is None)
            wait_seconds = args.wait_seconds if args.wait_seconds is not None else 0

            repeat_controller(
                serial_comm,
                file_list,
                repeat,
                args.repeat_count,
                wait_enter,
                wait_seconds,
            )
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