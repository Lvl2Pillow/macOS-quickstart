#!/usr/bin/env python3
"""macOS Quickstart Setup TUI"""

import curses
import json
import os
import subprocess
import textwrap

# ── Script path ───────────────────────────────────────────

SCRIPT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
CHECK_SCRIPT = os.path.join(SCRIPT_DIRECTORY, "check_installed.sh")
INSTALL_SCRIPT = os.path.join(SCRIPT_DIRECTORY, "installer.sh")

# ── Data model ────────────────────────────────────────────


class Group:
    def __init__(
        self, name, description, components, required=False, dependencies=None
    ):
        self.name = name
        self.description = description
        self.components = components
        self.required = required
        self.dependencies = dependencies or []
        self.enabled = required
        self.status = {}

    def apply_status(self, full_status):
        for component in self.components:
            self.status[component] = full_status.get(component, False)

    @property
    def installed(self):
        return all(self.status.get(component, False) for component in self.components)


def build_groups():
    return [
        Group(
            "Xcode CLT",
            "Installs Xcode Command Line Tools\n(compilers, git, core utilities).",
            ["xcode"],
            required=True,
        ),
        Group(
            "Homebrew",
            "Installs Homebrew, the macOS package manager.",
            ["brew"],
            required=True,
            dependencies=["Xcode CLT"],
        ),
        Group(
            "Opencode",
            "Installs the Opencode AI coding assistant.",
            ["opencode"],
            dependencies=["Homebrew"],
        ),
        Group(
            "Playwright",
            "Installs playwright-cli for browser automation.",
            ["playwright"],
            dependencies=["Homebrew"],
        ),
        Group(
            "Private Local AI",
            "Sets up local AI models, optimized for Apple Silicon:\n"
            "  \u2022 OMLX \u2014 LLM inference server\n"
            "  \u2022 HuggingFace \u2014 model hub CLI\n"
            "  \u2022 Downloads Qwen3.5-9B-4bit model to ~/models/",
            ["omlx", "hf", "model"],
            dependencies=["Homebrew"],
        ),
        Group(
            "Hermes",
            "Installs the Hermes AI agent runtime.",
            ["hermes"],
            dependencies=["Homebrew"],
        ),
        Group(
            "GitHub",
            "Generates SSH key and copies it to your clipboard for easy GitHub setup.",
            ["ssh"],
            dependencies=[],
        ),
    ]


# ── Shell interface ────────────────────────────────────────


def get_installation_status():
    """Run check_installed.sh and return dict of component→bool."""
    result = subprocess.run([CHECK_SCRIPT], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"check_installed.sh failed (exit {result.returncode}):\n"
            + (result.stderr.strip() or result.stdout.strip() or "unknown error")
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"check_installed.sh returned invalid JSON:\n{e}\n\nOutput:\n{result.stdout.strip()}"
        )


# ── TUI ────────────────────────────────────────────────────

MAX_WIDTH = 80
LEFT_PANEL_WIDTH = 36
MIN_HEIGHT = 10
COMPONENT_LABELS = {
    "omlx": "omlx",
    "hf": "huggingface-cli",
    "model": "download model",
}


def initialize_colors():
    if not curses.has_colors():
        return
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)  # installed
    curses.init_pair(3, curses.COLOR_CYAN, -1)  # header
    curses.init_pair(4, curses.COLOR_YELLOW, -1)  # required tag
    curses.init_pair(5, curses.COLOR_YELLOW, -1)  # instructions accent


def draw_screen(screen, groups, cursor_index, scroll_offset):
    try:
        terminal_height, terminal_width = screen.getmaxyx()
    except curses.error:
        return scroll_offset

    box_width = min(MAX_WIDTH, terminal_width)
    x_offset = (terminal_width - box_width) // 2
    divider_column = x_offset + LEFT_PANEL_WIDTH
    right_panel_width = box_width - LEFT_PANEL_WIDTH - 2

    # Not enough room — skip draw, poll will retry
    if right_panel_width < 1:
        return scroll_offset

    screen.clear()

    # ── Header ──
    screen.attron(curses.color_pair(3) | curses.A_BOLD)
    header = " macOS Quickstart Setup "
    screen.addstr(0, x_offset, header.ljust(box_width))
    screen.attroff(curses.color_pair(3) | curses.A_BOLD)

    # ── Instructions ──
    screen.attron(curses.color_pair(5) | curses.A_BOLD)
    instructions = " Space = toggle \u2022 Enter = run"
    screen.addstr(1, x_offset, instructions.ljust(box_width))
    screen.attroff(curses.color_pair(5) | curses.A_BOLD)

    # ── Build display rows ──
    rows = []
    for group_index, group in enumerate(groups):
        rows.append(("group", group_index))
        if len(group.components) > 1:
            for component in group.components:
                rows.append(("sub", group_index, component))

    total_rows = len(rows)
    list_first_row = 3  # header(0) + instructions(1) + spacer(2)
    status_row = list_first_row + total_rows  # one past last list row
    content_height = status_row  # no separate status bar
    last_list_row = status_row - 1

    cursor_index = max(0, min(cursor_index, len(groups) - 1))

    cursor_row = 0
    for row_index, row in enumerate(rows):
        if row[0] == "group" and row[1] == cursor_index:
            cursor_row = row_index
            break

    if terminal_height >= content_height:
        list_available = total_rows
        scroll_offset = 0
    else:
        list_available = max(1, terminal_height - list_first_row)
        if cursor_row < scroll_offset:
            scroll_offset = cursor_row
        elif cursor_row >= scroll_offset + list_available:
            scroll_offset = cursor_row - list_available + 1
        scroll_offset = max(0, min(scroll_offset, max(0, total_rows - list_available)))

    # ── Divider line ──
    divider_top = 1  # instruction row
    for row in range(divider_top, last_list_row + 1):
        if row >= terminal_height:
            break
        screen.addstr(row, divider_column, "\u2502")

    # ── Draw left panel ──
    current_row = list_first_row
    for row_index in range(
        scroll_offset, min(scroll_offset + list_available, total_rows)
    ):
        if current_row >= terminal_height:
            break
        row = rows[row_index]
        row_type, group_index = row[0], row[1]
        group = groups[group_index]
        is_cursor = group_index == cursor_index
        checkmark_column = x_offset + LEFT_PANEL_WIDTH - 2

        if row_type == "group":
            icon = "\u25cf" if group.enabled else "\u25cb"
            line = f" {icon} {group.name}"

            if is_cursor:
                screen.attron(curses.A_REVERSE)
            screen.addstr(current_row, x_offset + 1, line)
            current_column = x_offset + 1 + len(line)

            if group.required:
                screen.attron(curses.color_pair(4) | curses.A_BOLD)
                tag = " [required]"
                screen.addstr(current_row, current_column, tag)
                screen.attroff(curses.color_pair(4) | curses.A_BOLD)
                current_column += len(tag)

            if is_cursor:
                screen.attroff(curses.A_REVERSE)

            if group.installed:
                screen.attron(curses.color_pair(1))
                screen.addstr(current_row, checkmark_column, "\u2713")
                screen.attroff(curses.color_pair(1))
            elif not group.enabled:
                screen.addstr(current_row, checkmark_column, "-")
            current_row += 1

        else:
            component = row[2]
            is_installed = group.status.get(component, False)
            display_name = COMPONENT_LABELS.get(component, component)

            if is_cursor:
                screen.attron(curses.A_REVERSE)
            sub_icon = "\u2022" if group.enabled else "\u25e6"
            screen.addstr(current_row, x_offset + 3, f"{sub_icon} {display_name}")
            if is_cursor:
                screen.attroff(curses.A_REVERSE)

            if is_installed:
                screen.attron(curses.color_pair(1))
                screen.addstr(current_row, checkmark_column, "\u2713")
                screen.attroff(curses.color_pair(1))
            current_row += 1

    # ── Right panel — description of selected group ──
    group = groups[cursor_index]
    description_segments = group.description.split("\n")
    wrapped_lines = []
    for segment in description_segments:
        if len(segment) > right_panel_width:
            wrapped_lines.extend(textwrap.wrap(segment, width=right_panel_width))
        else:
            wrapped_lines.append(segment)

    right_column = divider_column + 2
    screen.attron(curses.A_BOLD)
    screen.addstr(1, right_column, group.name[:right_panel_width])
    screen.attroff(curses.A_BOLD)

    max_desc_rows = last_list_row - 3
    for line_index, line in enumerate(wrapped_lines[:max_desc_rows]):
        row = 3 + line_index
        if row > last_list_row:
            break
        screen.addstr(row, right_column, line[:right_panel_width])

    screen.refresh()
    return scroll_offset


def is_group_ready(group, groups):
    if group.installed or not group.enabled:
        return False
    for dependency_name in group.dependencies:
        dependency = next((g for g in groups if g.name == dependency_name), None)
        if dependency and not dependency.installed:
            return False
    return True


def run_interface(screen):
    curses.curs_set(0)
    screen.keypad(True)
    curses.mousemask(0)
    curses.set_escdelay(25)

    initialize_colors()

    groups = build_groups()
    try:
        status = get_installation_status()
    except RuntimeError as e:
        curses.endwin()
        print("\033[1mQuickstart Setup Error\033[0m")
        print(str(e))
        print("\nFix the issue above, then run again.")
        return
    for group in groups:
        group.apply_status(status)

    cursor_index = 0
    scroll_offset = 0

    while True:
        try:
            terminal_height, terminal_width = screen.getmaxyx()
        except curses.error:
            break
        if terminal_width < MAX_WIDTH or terminal_height < MIN_HEIGHT:
            screen.clear()
            message = "Terminal too small"
            x = max(0, (terminal_width - len(message)) // 2)
            screen.addstr(0, x, message)
            screen.refresh()
            key = screen.getch()
            if key == ord("q"):
                break
            continue

        scroll_offset = draw_screen(screen, groups, cursor_index, scroll_offset)
        key = screen.getch()

        if key in (ord("q"), ord("Q"), 27):
            break

        elif key == curses.KEY_DOWN:
            if cursor_index < len(groups) - 1:
                cursor_index += 1

        elif key == curses.KEY_UP:
            if cursor_index > 0:
                cursor_index -= 1

        elif key == ord(" "):
            group = groups[cursor_index]
            if not group.required:
                group.enabled = not group.enabled
                if group.enabled:
                    for dependency_name in group.dependencies:
                        dependency = next(
                            (g for g in groups if g.name == dependency_name),
                            None,
                        )
                        if (
                            dependency
                            and not dependency.installed
                            and not dependency.enabled
                        ):
                            dependency.enabled = True

        elif key in (curses.KEY_ENTER, 10, 13):
            ready_groups = [g for g in groups if is_group_ready(g, groups)]
            if not ready_groups:
                break  # everything already installed — exit cleanly

            # Gather components to install (skip already-installed within ready groups)
            components = []
            for g in ready_groups:
                for c in g.components:
                    if not g.status.get(c):
                        components.append(c)

            curses.endwin()
            result = subprocess.run([INSTALL_SCRIPT, "install"] + components)
            if result.returncode != 0:
                print("\n\033[1m\u2717 Installation failed (see output above)\033[0m")
                print("  Fix the issue and run the quickstart again.")
                return

            if "ssh" in components:
                key_path = os.path.expanduser("~/.ssh/id_ed25519.pub")
                if os.path.isfile(key_path):
                    with open(key_path) as f:
                        public_key = f.read().strip()
                    subprocess.run(["pbcopy"], input=public_key, text=True)
                    print("\n\033[1m\u26a0  SSH key copied to clipboard\033[0m")
                    print("     Add it to https://github.com/settings/keys")
                    print("     " + public_key)
            return

        elif key == curses.KEY_RESIZE:
            continue


def main(screen):
    try:
        run_interface(screen)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    curses.wrapper(main)
