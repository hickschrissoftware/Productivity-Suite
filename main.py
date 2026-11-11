import os
import sys
import threading
import time

def print_header(title):
    """Prints a clean, styled header for the console interface."""
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


# ==========================================
# GLOBAL STATE FOR BACKGROUND TASKS & TASKS
# ==========================================
active_stopwatch = {
    "running": False,
    "elapsed": 0.0,
    "start_time": None,
}

active_countdown = {
    "running": False,
    "remaining": 0,  # in seconds
    "initial": 0,
}

tasks = []
next_task_id = 1


# ==========================================
# BACKGROUND WORKER THREADS
# ==========================================
def stopwatch_worker():
    while active_stopwatch["running"]:
        active_stopwatch["elapsed"] = time.time() - active_stopwatch["start_time"]
        time.sleep(0.1)


def countdown_worker():
    while active_countdown["running"] and active_countdown["remaining"] > 0:
        time.sleep(1)
        if active_countdown["running"]:
            active_countdown["remaining"] -= 1

    if active_countdown["remaining"] <= 0 and active_countdown["running"]:
        active_countdown["running"] = False


# ==========================================
# COMPACT, ZERO-BLINK SIDE-BY-SIDE DISPLAY
# ==========================================
def display_side_by_side_raw(menu_lines, current_input_buffer=""):
    """Renders the UI using ANSI cursor repositioning with a tight, fitted status box."""
    sys.stdout.write("\033[H")
    
    print("=" * 75)
    print("                       PRODUCTIVITY SUITE")
    print("=" * 75)

    # Format Stopwatch Status
    if active_stopwatch["running"]:
        el = time.time() - active_stopwatch["start_time"]
        m, s = divmod(int(el), 60)
        sw_display = f"RUNNING ({m:02d}:{s:02d})"
    elif active_stopwatch["elapsed"] > 0:
        m, s = divmod(int(active_stopwatch["elapsed"]), 60)
        sw_display = f"PAUSED  ({m:02d}:{s:02d})"
    else:
        sw_display = "OFF (00:00)"

    # Format Countdown Status
    if active_countdown["running"]:
        m, s = divmod(active_countdown["remaining"], 60)
        cd_display = f"RUNNING ({m:02d}:{s:02d})"
    elif active_countdown["remaining"] > 0:
        m, s = divmod(active_countdown["remaining"], 60)
        cd_display = f"PAUSED  ({m:02d}:{s:02d})"
    else:
        cd_display = "OFF (00:00)"

    # Calculate waiting task counts by category
    waiting_discussion = sum(1 for t in tasks if not t["completed"] and t["category"] == "Discussion Post")
    waiting_assignment = sum(1 for t in tasks if not t["completed"] and t["category"] == "Assignment")
    waiting_projects = sum(1 for t in tasks if not t["completed"] and t["category"] == "Projects")

    # Tight, optimized box layout matching exact content width
    right_panel = [
        " ┌──────────────────────────────┐",
        f" │ LIVE STATUS & PENDING        │",
        f" │ Stopwatch: {sw_display:<17} │",
        f" │ Countdown: {cd_display:<17} │",
        " ├──────────────────────────────┤",
        f" │ WAITING TASKS BY CATEGORY:   │",
        f" │ • Discussion Posts: {waiting_discussion:<8} │",
        f" │ • Assignments:      {waiting_assignment:<8} │",
        f" │ • Projects:         {waiting_projects:<8} │",
        " └──────────────────────────────┘"
    ]

    max_rows = max(len(menu_lines), len(right_panel))
    for i in range(max_rows):
        left_line = menu_lines[i] if i < len(menu_lines) else ""
        right_line = right_panel[i] if i < len(right_panel) else ""
        # Minimized left column width (38 chars) to pull status box closer to menu
        print(f"{left_line:<38} {right_line}".ljust(75))

    print("-" * 75)
    sys.stdout.flush()


def get_input_realtime(menu_lines, prompt):
    """Refreshes screen smoothly every second without blinking while waiting for input."""
    os.system('cls' if os.name == 'nt' else 'clear')
    display_side_by_side_raw(menu_lines, "")
    sys.stdout.write(prompt)
    sys.stdout.flush()

    if os.name == 'nt':
        import msvcrt
        line_chars = []
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getch()
                if char in (b'\r', b'\n'):
                    print()
                    return "".join(line_chars).strip()
                elif char in (b'\x08', b'\x7f'):
                    if line_chars:
                        line_chars.pop()
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                else:
                    try:
                        decoded = char.decode('utf-8', errors='ignore')
                        line_chars.append(decoded)
                        sys.stdout.write(decoded)
                        sys.stdout.flush()
                    except:
                        pass
            else:
                time.sleep(1)
                display_side_by_side_raw(menu_lines, "")
                sys.stdout.write(prompt + "".join(line_chars))
                sys.stdout.flush()
    else:
        import select
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        line_chars = []
        try:
            tty.setcbreak(fd)
            while True:
                rlist, _, _ = select.select([sys.stdin], [], [], 1.0)
                if rlist:
                    char = sys.stdin.read(1)
                    if char in ('\n', '\r'):
                        print()
                        return "".join(line_chars).strip()
                    elif char in ('\x7f', '\b'):
                        if line_chars:
                            line_chars.pop()
                            sys.stdout.write('\b \b')
                            sys.stdout.flush()
                    else:
                        line_chars.append(char)
                        sys.stdout.write(char)
                        sys.stdout.flush()
                else:
                    display_side_by_side_raw(menu_lines, "")
                    sys.stdout.write(prompt + "".join(line_chars))
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSDSET, old_settings)


# ==========================================
# MODULE 1: LIVE STOPWATCH CONTROLS
# ==========================================
def manage_stopwatch():
    while True:
        current_elapsed = active_stopwatch["elapsed"]
        if active_stopwatch["running"]:
            current_elapsed = time.time() - active_stopwatch["start_time"]

        m, s = divmod(int(current_elapsed), 60)
        
        menu = [
            " [ BACKGROUND STOPWATCH ]",
            f" Current Time: {m:02d}:{s:02d}",
            ""
        ]
        
        if active_stopwatch["running"]:
            menu.append("1. Stop Stopwatch")
            menu.append("2. Return to Dashboard")
        else:
            if active_stopwatch["elapsed"] == 0.0:
                menu.append("1. Start Stopwatch")
            else:
                menu.append("1. Resume Stopwatch")
            menu.append("2. Reset to 0")
            menu.append("3. Return to Dashboard")

        choice = get_input_realtime(menu, "Select option: ")

        if active_stopwatch["running"]:
            if choice == "1":
                active_stopwatch["running"] = False
                active_stopwatch["elapsed"] = time.time() - active_stopwatch["start_time"]
            elif choice == "2":
                return
        else:
            if choice == "1":
                active_stopwatch["start_time"] = time.time() - active_stopwatch["elapsed"]
                active_stopwatch["running"] = True
                threading.Thread(target=stopwatch_worker, daemon=True).start()
            elif choice == "2":
                active_stopwatch["running"] = False
                active_stopwatch["elapsed"] = 0.0
                active_stopwatch["start_time"] = None
            elif choice == "3":
                return


# ==========================================
# MODULE 2: COUNTDOWN TIMER CONTROLS
# ==========================================
def manage_countdown():
    while True:
        m, s = divmod(active_countdown["remaining"], 60)
        
        menu = [
            " [ BACKGROUND COUNTDOWN ]",
            f" Time Remaining: {m:02d}:{s:02d}",
            ""
        ]

        if active_countdown["running"]:
            menu.append("1. Stop Countdown")
            menu.append("2. Return to Dashboard")
        else:
            if active_countdown["remaining"] == 0:
                menu.append("1. Start New Timer")
            else:
                menu.append("1. Resume Countdown")
            menu.append("2. Reset to 0")
            menu.append("3. Return to Dashboard")

        choice = get_input_realtime(menu, "Select option: ")

        if active_countdown["running"]:
            if choice == "1":
                active_countdown["running"] = False
            elif choice == "2":
                return
        else:
            if choice == "1":
                if active_countdown["remaining"] == 0:
                    os.system('cls' if os.name == 'nt' else 'clear')
                    try:
                        mins_input = float(input("Enter duration in minutes (max 60): "))
                        if mins_input <= 0 or mins_input > 60:
                            print("[!] Error: Must be between 1 and 60 minutes.")
                            input("\nPress Enter to continue...")
                            continue
                        total_secs = int(mins_input * 60)
                        active_countdown["initial"] = total_secs
                        active_countdown["remaining"] = total_secs
                    except ValueError:
                        print("[!] Invalid input.")
                        input("\nPress Enter to continue...")
                        continue

                active_countdown["running"] = True
                threading.Thread(target=countdown_worker, daemon=True).start()
            elif choice == "2":
                active_countdown["running"] = False
                active_countdown["remaining"] = 0
                active_countdown["initial"] = 0
            elif choice == "3":
                return


# ==========================================
# MODULE 3: TO-DO LIST
# ==========================================
def run_task_manager():
    global next_task_id
    while True:
        menu = [
            " [ TO-DO LIST ]",
            "1. View by Category",
            "2. Add New Task",
            "3. Mark Task Complete",
            "4. Return to Dashboard"
        ]
        choice = get_input_realtime(menu, "Select option: ")

        if choice == "1":
            os.system('cls' if os.name == 'nt' else 'clear')
            print_header("VIEW TASKS BY CATEGORY")
            print("1. Discussion Post")
            print("2. Assignment")
            print("3. Projects")
            cat_choice = input("\nSelect category to view (1-3): ").strip()
            category_map = {"1": "Discussion Post", "2": "Assignment", "3": "Projects"}
            selected_cat = category_map.get(cat_choice)

            if not selected_cat:
                print("\n[!] Invalid category selection.")
            else:
                print(f"\n--- Tasks in [{selected_cat}] ---")
                filtered_tasks = [t for t in tasks if t["category"] == selected_cat]
                if not filtered_tasks:
                    print(f"No tasks found in {selected_cat}.")
                else:
                    for t in filtered_tasks:
                        status = "✓ [COMPLETED]" if t["completed"] else "⏳ [WAITING]"
                        print(f"• {t['title']} | Status: {status}")
            input("\nPress Enter to continue...")

        elif choice == "2":
            os.system('cls' if os.name == 'nt' else 'clear')
            print_header("ADD NEW TASK")
            title = input("Enter task description: ").strip()
            if not title:
                print("[!] Error: Task title cannot be empty.")
            else:
                print("\nSelect Category:")
                print("1. Discussion Post")
                print("2. Assignment")
                print("3. Projects")
                cat_choice = input("Select category (1-3): ").strip()
                
                category_map = {"1": "Discussion Post", "2": "Assignment", "3": "Projects"}
                category = category_map.get(cat_choice, "Assignment")

                tasks.append({
                    "id": next_task_id,
                    "title": title,
                    "category": category,
                    "completed": False
                })
                print(f"[+] Task '{title}' added successfully under [{category}]!")
                next_task_id += 1
            input("\nPress Enter to continue...")

        elif choice == "3":
            os.system('cls' if os.name == 'nt' else 'clear')
            print_header("MARK TASK COMPLETE")
            print("Select Category to find task:")
            print("1. Discussion Post")
            print("2. Assignment")
            print("3. Projects")
            cat_choice = input("Select category (1-3): ").strip()
            category_map = {"1": "Discussion Post", "2": "Assignment", "3": "Projects"}
            selected_cat = category_map.get(cat_choice)

            if not selected_cat:
                print("\n[!] Invalid category.")
            else:
                pending_tasks = [t for t in tasks if t["category"] == selected_cat and not t["completed"]]
                if not pending_tasks:
                    print(f"\n[i] No pending tasks found in {selected_cat}.")
                else:
                    print(f"\n--- Pending Tasks in [{selected_cat}] ---")
                    for idx, t in enumerate(pending_tasks, 1):
                        print(f"{idx}. {t['title']}")
                    
                    try:
                        t_idx = int(input("\nEnter the number of the task to mark complete: ")) - 1
                        if 0 <= t_idx < len(pending_tasks):
                            target = pending_tasks[t_idx]
                            target["completed"] = True
                            print(f"\n[🎉 SUCCESS] Task '{target['title']}' marked as complete!")
                        else:
                            print("\n[!] Invalid selection number.")
                    except ValueError:
                        print("\n[!] Invalid numerical input.")
            input("\nPress Enter to continue...")

        elif choice == "4":
            break


# ==========================================
# MAIN APPLICATION DASHBOARD
# ==========================================
def main():
    while True:
        menu = [
            " [ MAIN DASHBOARD ]",
            "1. Manage Stopwatch",
            "2. Manage Countdown Timer",
            "3. To-do List",
            "4. Exit Application"
        ]
        choice = get_input_realtime(menu, "Select option: ")

        if choice == "1":
            manage_stopwatch()
        elif choice == "2":
            manage_countdown()
        elif choice == "3":
            run_task_manager()
        elif choice == "4":
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\nSaving session... Goodbye!")
            sys.exit(0)


if __name__ == "__main__":
    main()