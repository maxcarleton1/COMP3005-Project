import psycopg2
from datetime import datetime, timedelta

DB_CONFIG = {
    "host": "localhost",
    "database": "a1_database",
    "user": "postgres",
    "password": "postgres",
    "port": "5432"
}

TIME_FORMAT = "%Y-%m-%d %H:%M"  # e.g., 2025-01-31 14:30


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# ---------- SMALL HELPERS ----------

def get_member_id(user_id):
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT member_id FROM Member WHERE user_id = %s;", (user_id,))
        row = cur.fetchone()
        cur.close()
        con.close()
        if row:
            return row[0]
    except Exception as e:
        print("Error getting member id:", e)
    return None


def get_trainer_id(user_id):
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT trainer_id FROM Trainer WHERE user_id = %s;", (user_id,))
        row = cur.fetchone()
        cur.close()
        con.close()
        if row:
            return row[0]
    except Exception as e:
        print("Error getting trainer id:", e)
    return None


def times_overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1


def get_available_rooms(new_start, duration_minutes):
    """Return a list of room_ids available at that time.
       Room capacity is enforced only for PT sessions.
       Group classes block the room by time, but do NOT reduce capacity.
    """
    new_end = new_start + timedelta(minutes=duration_minutes)
    available = []

    try:
        con = get_connection()
        cur = con.cursor()

        # Get all rooms and their capacities
        cur.execute("SELECT room_id, capacity FROM Room;")
        rooms = cur.fetchall()

        for room_id, capacity in rooms:
            # Count overlapping PT sessions in this room
            cur.execute(
                "SELECT session_at, duration_minutes "
                "FROM PTSession WHERE room_id = %s;",
                (room_id,)
            )
            pt_sessions = cur.fetchall()

            concurrent_pt = 0
            for s_at, dur in pt_sessions:
                s_end = s_at + timedelta(minutes=dur)
                if times_overlap(new_start, new_end, s_at, s_end):
                    concurrent_pt += 1

            # If concurrent PT sessions already at capacity, room not available
            if concurrent_pt >= capacity:
                continue

            # Check group classes in the room (block the room if time overlaps)
            cur.execute(
                "SELECT scheduled_at, duration_minutes "
                "FROM GroupClass WHERE room_id = %s;",
                (room_id,)
            )
            gc_list = cur.fetchall()
            blocked_by_class = False
            for gc_start, gc_dur in gc_list:
                gc_end = gc_start + timedelta(minutes=gc_dur)
                if times_overlap(new_start, new_end, gc_start, gc_end):
                    blocked_by_class = True
                    break

            if blocked_by_class:
                continue

            available.append(room_id)

        cur.close()
        con.close()
    except Exception as e:
        print("Error getting available rooms:", e)

    return available


def get_available_trainers(new_start, duration_minutes):
    """Return a list of trainer_ids available at that time.
       Trainer availability (start_time/end_time), PT sessions, and group classes
       are checked for conflicts.
    """
    new_end = new_start + timedelta(minutes=duration_minutes)
    available = []

    try:
        con = get_connection()
        cur = con.cursor()

        cur.execute("SELECT trainer_id, start_time, end_time FROM Trainer;")
        trainers = cur.fetchall()

        for trainer_id, avail_start, avail_end in trainers:
            # Check trainer availability window (time of day)
            if avail_start and avail_end:
                if not (new_start.time() >= avail_start.time() and
                        new_end.time() <= avail_end.time()):
                    continue

            # Check trainer's PT sessions
            cur.execute(
                "SELECT session_at, duration_minutes "
                "FROM PTSession WHERE trainer_id = %s;",
                (trainer_id,)
            )
            pt_sessions = cur.fetchall()
            conflict = False
            for s_at, dur in pt_sessions:
                s_end = s_at + timedelta(minutes=dur)
                if times_overlap(new_start, new_end, s_at, s_end):
                    conflict = True
                    break

            if conflict:
                continue

            # Check trainer's group classes
            cur.execute(
                "SELECT scheduled_at, duration_minutes "
                "FROM GroupClass WHERE trainer_id = %s;",
                (trainer_id,)
            )
            gc_list = cur.fetchall()
            conflict = False
            for gc_start, gc_dur in gc_list:
                gc_end = gc_start + timedelta(minutes=gc_dur)
                if times_overlap(new_start, new_end, gc_start, gc_end):
                    conflict = True
                    break

            if conflict:
                continue

            available.append(trainer_id)

        cur.close()
        con.close()
    except Exception as e:
        print("Error getting available trainers:", e)

    return available


def check_trainer_and_room_availability(trainer_id, room_id, new_start, duration_minutes):
    """Simple wrapper that reuses the two helper lists."""
    rooms = get_available_rooms(new_start, duration_minutes)
    if room_id not in rooms:
        print("Selected room is no longer available.")
        return False

    trainers = get_available_trainers(new_start, duration_minutes)
    if trainer_id not in trainers:
        print("Selected trainer is no longer available.")
        return False

    return True


# ---------- REGISTRATION ----------

def register_member():
    print("\n=== Register Member ===")
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    name = input("Full name: ").strip()
    dob = input("Date of birth (YYYY-MM-DD, optional): ").strip() or None
    gender = input("Gender (optional): ").strip() or None
    phone = input("Phone (optional): ").strip() or None
    address = input("Address (optional): ").strip() or None

    try:
        con = get_connection()
        cur = con.cursor()

        cur.execute(
            "INSERT INTO UserAccount (email, password, role_type) "
            "VALUES (%s, %s, 'MEMBER') RETURNING user_id;",
            (email, password)
        )
        user_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO Member (user_id, name, dob, gender, phone, address) "
            "VALUES (%s, %s, %s, %s, %s, %s);",
            (user_id, name, dob, gender, phone, address)
        )

        con.commit()
        cur.close()
        con.close()
        print("Member registered.")
    except Exception as e:
        print("Error registering member:", e)


def register_trainer():
    print("\n=== Register Trainer ===")
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    name = input("Full name: ").strip()

    start_time = "2025-01-01 09:00:00"
    end_time = "2025-01-01 17:00:00"
    recurrence = "WEEKDAYS"

    try:
        con = get_connection()
        cur = con.cursor()

        cur.execute(
            "INSERT INTO UserAccount (email, password, role_type) "
            "VALUES (%s, %s, 'TRAINER') RETURNING user_id;",
            (email, password)
        )
        user_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO Trainer (user_id, name, start_time, end_time, recurrence) "
            "VALUES (%s, %s, %s, %s, %s);",
            (user_id, name, start_time, end_time, recurrence)
        )

        con.commit()
        cur.close()
        con.close()
        print("Trainer registered.")
    except Exception as e:
        print("Error registering trainer:", e)


def register_admin():
    print("\n=== Register Admin ===")
    email = input("Email: ").strip()
    password = input("Password: ").strip()

    try:
        con = get_connection()
        cur = con.cursor()

        cur.execute(
            "INSERT INTO UserAccount (email, password, role_type) "
            "VALUES (%s, %s, 'ADMIN');",
            (email, password)
        )

        con.commit()
        cur.close()
        con.close()
        print("Admin registered (placeholder).")
    except Exception as e:
        print("Error registering admin:", e)


# ---------- AUTHENTICATION ----------

def authenticate_user():
    print("\n=== Login ===")
    email = input("Email: ").strip()
    password = input("Password: ").strip()

    try:
        con = get_connection()
        cur = con.cursor()

        cur.execute(
            "SELECT user_id, role_type, is_active "
            "FROM UserAccount "
            "WHERE email = %s AND password = %s;",
            (email, password)
        )
        row = cur.fetchone()

        cur.close()
        con.close()
    except Exception as e:
        print("Error during login:", e)
        return None

    if row is None:
        print("Invalid email or password.")
        return None

    user_id, role_type, is_active = row
    if not is_active:
        print("Account inactive.")
        return None

    print("Logged in as", role_type)
    return {"user_id": user_id, "role_type": role_type}


# ---------- TRAINER: SET AVAILABILITY ----------

def set_trainer_availability(user):
    print("\n=== Set Trainer Availability ===")

    trainer_id = get_trainer_id(user["user_id"])
    if trainer_id is None:
        print("No trainer record found.")
        return

    try:
        con = get_connection()
        cur = con.cursor()

        cur.execute(
            "SELECT start_time, end_time, recurrence "
            "FROM Trainer WHERE trainer_id = %s;",
            (trainer_id,)
        )
        row = cur.fetchone()
        old_start, old_end, old_recurrence = row

        print("Current availability:")
        print("  Start:", old_start)
        print("  End:  ", old_end)
        print("  Recurrence:", old_recurrence)

        print("\nEnter new availability window.")
        print("Format: YYYY-MM-DD HH:MM")
        start_str = input("New start time: ").strip()
        end_str = input("New end time: ").strip()
        recurrence = input("Recurrence (e.g. WEEKDAYS): ").strip() or "WEEKDAYS"

        try:
            new_start = datetime.strptime(start_str, TIME_FORMAT)
            new_end = datetime.strptime(end_str, TIME_FORMAT)
        except ValueError:
            print("Invalid date/time format.")
            cur.close()
            con.close()
            return

        if new_start >= new_end:
            print("Start time must be before end time.")
            cur.close()
            con.close()
            return

        cur.execute(
            "UPDATE Trainer "
            "SET start_time = %s, end_time = %s, recurrence = %s "
            "WHERE trainer_id = %s;",
            (new_start, new_end, recurrence, trainer_id)
        )

        con.commit()
        cur.close()
        con.close()
        print("Availability updated.")
    except Exception as e:
        print("Error updating availability:", e)

# ---------- TRAINER: VIEW SCHEDULE ----------

def trainer_schedule_view(user):
    print("\n=== Trainer Schedule View ===")

    trainer_id = get_trainer_id(user["user_id"])
    if trainer_id is None:
        print("No trainer record found.")
        return

    try:
        con = get_connection()
        cur = con.cursor()

        # Upcoming PT sessions
        cur.execute(
            """
            SELECT session_at, duration_minutes, member_id, room_id
            FROM PTSession
            WHERE trainer_id = %s
              AND session_at >= NOW()
            ORDER BY session_at
            LIMIT 20;
            """,
            (trainer_id,)
        )
        pt_sessions = cur.fetchall()

        # Upcoming group classes
        cur.execute(
            """
            SELECT class_name, scheduled_at, room_id
            FROM GroupClass
            WHERE trainer_id = %s
              AND scheduled_at >= NOW()
            ORDER BY scheduled_at
            LIMIT 20;
            """,
            (trainer_id,)
        )
        classes = cur.fetchall()

        cur.close()
        con.close()

        print("\n--- Upcoming PT Sessions ---")
        if pt_sessions:
            for s_at, dur, member_id, room_id in pt_sessions:
                print(f"- {s_at}, {dur} min, member {member_id}, room {room_id}")
        else:
            print("No upcoming PT sessions.")

        print("\n--- Upcoming Group Classes ---")
        if classes:
            for cname, sched, room_id in classes:
                print(f"- {cname} at {sched}, room {room_id}")
        else:
            print("No upcoming classes.")

    except Exception as e:
        print("Error loading schedule:", e)


# ---------- MEMBER: PROFILE MANAGEMENT ----------

def update_member_profile(user):
    print("\n=== Update Member Profile ===")

    member_id = get_member_id(user["user_id"])
    if member_id is None:
        print("No member record found.")
        return

    try:
        con = get_connection()
        cur = con.cursor()

        cur.execute(
            "SELECT name, dob, gender, phone, address "
            "FROM Member WHERE member_id = %s;",
            (member_id,)
        )
        row = cur.fetchone()
        if not row:
            print("Member not found.")
            cur.close()
            con.close()
            return

        old_name, old_dob, old_gender, old_phone, old_address = row

        print("Current values (press Enter to keep):")
        print("Name:", old_name)
        print("DOB:", old_dob)
        print("Gender:", old_gender)
        print("Phone:", old_phone)
        print("Address:", old_address)

        name = input("New name: ").strip() or old_name
        dob = input("New DOB (YYYY-MM-DD): ").strip() or (old_dob.isoformat() if old_dob else None)
        gender = input("New gender: ").strip() or old_gender
        phone = input("New phone: ").strip() or old_phone
        address = input("New address: ").strip() or old_address

        cur.execute(
            "UPDATE Member "
            "SET name = %s, dob = %s, gender = %s, phone = %s, address = %s "
            "WHERE member_id = %s;",
            (name, dob, gender, phone, address, member_id)
        )

        con.commit()
        cur.close()
        con.close()
        print("Profile updated.")
    except Exception as e:
        print("Error updating profile:", e)


def set_fitness_goal(user):
    print("\n=== Set Fitness Goal ===")

    member_id = get_member_id(user["user_id"])
    if member_id is None:
        print("No member record found.")
        return

    goal_type = input("Goal type (e.g. WEIGHT_TARGET): ").strip() or "WEIGHT_TARGET"
    target_value = input("Target value (e.g. 70): ").strip() or None
    start_date = input("Start date (YYYY-MM-DD): ").strip() or None
    end_date = input("End date (YYYY-MM-DD): ").strip() or None

    try:
        con = get_connection()
        cur = con.cursor()

        cur.execute(
            "INSERT INTO FitnessGoal (member_id, goal_type, target_value, start_date, end_date) "
            "VALUES (%s, %s, %s, %s, %s);",
            (member_id, goal_type, target_value, start_date, end_date)
        )

        con.commit()
        cur.close()
        con.close()
        print("Fitness goal saved.")
    except Exception as e:
        print("Error saving fitness goal:", e)


def add_health_metric(user):
    print("\n=== Add Health Metric ===")

    member_id = get_member_id(user["user_id"])
    if member_id is None:
        print("No member record found.")
        return

    height = input("Height (optional): ").strip() or None
    weight = input("Weight (optional): ").strip() or None
    bfp = input("Body fat % (optional): ").strip() or None
    hr = input("Heart rate (optional): ").strip() or None

    try:
        con = get_connection()
        cur = con.cursor()

        # Assumes HealthMetric has a 'measured_at' TIMESTAMP column
        cur.execute(
            "INSERT INTO HealthMetric (member_id, height, weight, bfp, heart_rate, measured_at) "
            "VALUES (%s, %s, %s, %s, %s, NOW());",
            (member_id, height, weight, bfp, hr)
        )

        con.commit()
        cur.close()
        con.close()
        print("Health metric recorded.")
    except Exception as e:
        print("Error adding health metric:", e)


# ---------- MEMBER: PT SESSION SCHEDULING ----------

def schedule_pt_session(user):
    print("\n=== Schedule PT Session ===")

    member_id = get_member_id(user["user_id"])
    if member_id is None:
        print("No member record found.")
        return

    start_str = input(f"Desired session start time ({TIME_FORMAT}): ").strip()
    duration_str = input("Duration in minutes: ").strip()

    try:
        new_start = datetime.strptime(start_str, TIME_FORMAT)
    except ValueError:
        print("Invalid date/time format.")
        return

    try:
        duration = int(duration_str)
    except ValueError:
        print("Invalid duration.")
        return

    # Get available rooms and trainers
    available_rooms = get_available_rooms(new_start, duration)
    available_trainers = get_available_trainers(new_start, duration)

    if not available_rooms:
        print("No rooms available at that time.")
        return
    if not available_trainers:
        print("No trainers available at that time.")
        return

    print("Available rooms (room_id):", ", ".join(str(r) for r in available_rooms))
    print("Available trainers (trainer_id):", ", ".join(str(t) for t in available_trainers))

    room_id_str = input("Select room_id: ").strip()
    trainer_id_str = input("Select trainer_id: ").strip()

    try:
        room_id = int(room_id_str)
        trainer_id = int(trainer_id_str)
    except ValueError:
        print("Invalid room or trainer id.")
        return

    if room_id not in available_rooms:
        print("Selected room not in available list.")
        return
    if trainer_id not in available_trainers:
        print("Selected trainer not in available list.")
        return

    # Final check in case something changed
    if not check_trainer_and_room_availability(trainer_id, room_id, new_start, duration):
        print("No trainer/room available (conflict detected).")
        return

    try:
        con = get_connection()
        cur = con.cursor()

        cur.execute(
            "INSERT INTO PTSession (member_id, trainer_id, room_id, session_at, duration_minutes) "
            "VALUES (%s, %s, %s, %s, %s);",
            (member_id, trainer_id, room_id, new_start, duration)
        )

        con.commit()
        cur.close()
        con.close()
        print("PT session scheduled.")
    except Exception as e:
        print("Error scheduling PT session:", e)


def reschedule_pt_session(user):
    print("\n=== Reschedule PT Session ===")

    member_id = get_member_id(user["user_id"])
    if member_id is None:
        print("No member record found.")
        return

    try:
        con = get_connection()
        cur = con.cursor()

        cur.execute(
            "SELECT session_id, session_at, duration_minutes, trainer_id, room_id "
            "FROM PTSession WHERE member_id = %s ORDER BY session_at;",
            (member_id,)
        )
        sessions = cur.fetchall()

        if not sessions:
            print("No PT sessions found.")
            cur.close()
            con.close()
            return

        print("Your PT sessions:")
        for s_id, s_at, dur, t_id, r_id in sessions:
            print(f"  ID {s_id}: {s_at}, {dur} min, trainer {t_id}, room {r_id}")

        session_id_str = input("Enter session ID to reschedule: ").strip()
        start_str = input(f"New start time ({TIME_FORMAT}): ").strip()
        room_id_str = input("New room ID: ").strip()
        duration_str = input("New duration in minutes: ").strip()

        try:
            new_start = datetime.strptime(start_str, TIME_FORMAT)
            duration = int(duration_str)
        except ValueError:
            print("Invalid time or duration.")
            cur.close()
            con.close()
            return

        # Get trainer_id from that session
        cur.execute(
            "SELECT trainer_id FROM PTSession WHERE session_id = %s AND member_id = %s;",
            (session_id_str, member_id)
        )
        row = cur.fetchone()
        if not row:
            print("Session not found or does not belong to you.")
            cur.close()
            con.close()
            return

        trainer_id = row[0]

        try:
            room_id = int(room_id_str)
        except ValueError:
            print("Invalid room id.")
            cur.close()
            con.close()
            return

        # Check availability
        if not check_trainer_and_room_availability(trainer_id, room_id, new_start, duration):
            print("No trainer/room available (conflict detected).")
            cur.close()
            con.close()
            return

        cur.execute(
            "UPDATE PTSession "
            "SET session_at = %s, room_id = %s, duration_minutes = %s "
            "WHERE session_id = %s AND member_id = %s;",
            (new_start, room_id, duration, session_id_str, member_id)
        )

        con.commit()
        cur.close()
        con.close()
        print("PT session rescheduled.")
    except Exception as e:
        print("Error rescheduling PT session:", e)


# ---------- MEMBER: GROUP CLASS REGISTRATION ----------

def register_group_class(user):
    print("\n=== Register for Group Class ===")

    member_id = get_member_id(user["user_id"])
    if member_id is None:
        print("No member record found.")
        return

    print("To be added!!")

# ---------- MEMBER: DASHBOARD ----------
def member_dashboard(user):
    print("\n=== Member Dashboard ===")

    member_id = get_member_id(user["user_id"])
    if member_id is None:
        print("No member record found.")
        return

    try:
        con = get_connection()
        cur = con.cursor()

        # Latest health stats
        cur.execute(
            """
            SELECT height, weight, bfp, heart_rate, measured_at
            FROM HealthMetric
            WHERE member_id = %s
            ORDER BY measured_at DESC
            LIMIT 1;
            """,
            (member_id,)
        )
        health = cur.fetchone()

        # Active fitness goals (end_date in the future or today)
        cur.execute(
            """
            SELECT goal_type, target_value, start_date, end_date
            FROM FitnessGoal
            WHERE member_id = %s
              AND end_date >= CURRENT_DATE
            ORDER BY end_date;
            """,
            (member_id,)
        )
        goals = cur.fetchall()

        # Past class count
        cur.execute(
            """
            SELECT COUNT(*)
            FROM ClassRegistration cr
            JOIN GroupClass gc ON cr.class_id = gc.class_id
            WHERE cr.member_id = %s
              AND gc.scheduled_at < NOW();
            """,
            (member_id,)
        )
        past_class_count = cur.fetchone()[0]

        # Upcoming PT sessions
        cur.execute(
            """
            SELECT session_at, duration_minutes, trainer_id, room_id
            FROM PTSession
            WHERE member_id = %s
              AND session_at >= NOW()
            ORDER BY session_at
            LIMIT 5;
            """,
            (member_id,)
        )
        upcoming_pt = cur.fetchall()

        # Upcoming group classes
        cur.execute(
            """
            SELECT gc.class_name, gc.scheduled_at, gc.room_id, gc.trainer_id
            FROM ClassRegistration cr
            JOIN GroupClass gc ON cr.class_id = gc.class_id
            WHERE cr.member_id = %s
              AND gc.scheduled_at >= NOW()
            ORDER BY gc.scheduled_at
            LIMIT 5;
            """,
            (member_id,)
        )
        upcoming_classes = cur.fetchall()

        cur.close()
        con.close()

        # ---- Print section by section ----
        print("\n--- Latest Health Stats ---")
        if health:
            h_height, h_weight, h_bfp, h_hr, h_time = health
            print("Measured at:", h_time)
            print("Height:", h_height)
            print("Weight:", h_weight)
            print("Body fat %:", h_bfp)
            print("Heart rate:", h_hr)
        else:
            print("No health metrics recorded yet.")

        print("\n--- Active Fitness Goals ---")
        if goals:
            for g_type, g_target, g_start, g_end in goals:
                print(f"- {g_type}: target={g_target}, {g_start} to {g_end}")
        else:
            print("No active goals.")

        print("\n--- Past Group Classes Attended ---")
        print("Total past classes:", past_class_count)

        print("\n--- Upcoming PT Sessions ---")
        if upcoming_pt:
            for s_at, dur, t_id, r_id in upcoming_pt:
                print(f"- {s_at}, {dur} min, trainer {t_id}, room {r_id}")
        else:
            print("No upcoming PT sessions.")

        print("\n--- Upcoming Group Classes ---")
        if upcoming_classes:
            for cname, sched, room_id, trainer_id in upcoming_classes:
                print(f"- {cname} at {sched}, room {room_id}, trainer {trainer_id}")
        else:
            print("No upcoming group classes.")

    except Exception as e:
        print("Error loading dashboard:", e)

#----------ADMIN-EQUIPMENT MAINTAINENCE MENU------------
        
def admin_equipment_maintenance(user):
    while True:
        print("\n=== Equipment Maintenance ===")
        print("1. Log new issue")
        print("2. View tickets")
        print("3. Update ticket status")
        print("4. Back")
        choice = input("Choose: ").strip()

        if choice == "1":
            admin_log_maintenance_issue()
        elif choice == "2":
            admin_view_tickets()
        elif choice == "3":
            admin_update_ticket_status()
        elif choice == "4":
            break
        else:
            print("Invalid choice.")


#----------ADMIN-LOG NEW ISSUE------------

def admin_log_maintenance_issue():
    print("\n=== Log New Maintenance Issue ===")

    room_id_str = input("Room ID: ").strip()
    if not room_id_str.isdigit():
        print("Invalid room id.")
        return
    room_id = int(room_id_str)

    # Optionally associate with equipment
    has_equipment = input("Is this for specific equipment? (y/n): ").strip().lower()
    equipment_no = None

    try:
        con = get_connection()
        cur = con.cursor()

        # Basic check that room exists
        cur.execute("SELECT name FROM Room WHERE room_id = %s;", (room_id,))
        row = cur.fetchone()
        if not row:
            print("Room not found.")
            cur.close()
            con.close()
            return

        if has_equipment == "y":
            # Show equipment in this room
            cur.execute(
                "SELECT equipment_no, name, type FROM Equipment WHERE room_id = %s;",
                (room_id,)
            )
            equipment_list = cur.fetchall()
            if not equipment_list:
                print("No equipment found in this room.")
                cur.close()
                con.close()
                return

            print("Equipment in room", room_id)
            for eq_no, eq_name, eq_type in equipment_list:
                print(f"- equipment_no {eq_no}: {eq_name} ({eq_type})")

            eq_str = input("Enter equipment_no: ").strip()
            if not eq_str.isdigit():
                print("Invalid equipment number.")
                cur.close()
                con.close()
                return

            equipment_no = int(eq_str)

            # Basic check that equipment exists
            cur.execute(
                "SELECT 1 FROM Equipment WHERE room_id = %s AND equipment_no = %s;",
                (room_id, equipment_no)
            )
            if not cur.fetchone():
                print("Equipment not found for that room.")
                cur.close()
                con.close()
                return

        issue = input("Issue description: ").strip()
        priority = input("Priority (e.g. LOW/MEDIUM/HIGH): ").strip() or "MEDIUM"
        status = "OPEN"  # default for new tickets

        # Insert ticket (room_id must NOT be null; equipment_no may be null or not)
        cur.execute(
            """
            INSERT INTO MaintainenceTicket (room_id, equipment_no, issue, priority, status)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (room_id, equipment_no, issue, priority, status)
        )

        con.commit()
        cur.close()
        con.close()
        print("Maintenance ticket created.")
    except Exception as e:
        print("Error creating ticket:", e)

#----------ADMIN-VIEW TICKETS------------
        
def admin_view_tickets():
    print("\n=== View Maintenance Tickets ===")
    print("Filter by status? (press Enter to show all, or type e.g. OPEN/CLOSED)")
    status_filter = input("Status filter: ").strip().upper()

    try:
        con = get_connection()
        cur = con.cursor()

        if status_filter:
            cur.execute(
                """
                SELECT ticket_id, room_id, equipment_no, issue, priority, status
                FROM MaintainenceTicket
                WHERE status = %s
                ORDER BY ticket_id;
                """,
                (status_filter,)
            )
        else:
            cur.execute(
                """
                SELECT ticket_id, room_id, equipment_no, issue, priority, status
                FROM MaintainenceTicket
                ORDER BY ticket_id;
                """
            )

        rows = cur.fetchall()
        cur.close()
        con.close()

        if not rows:
            print("No tickets found.")
            return

        for t_id, room_id, eq_no, issue, priority, status in rows:
            eq_text = f"equipment {eq_no}" if eq_no is not None else "room only"
            print(f"[{t_id}] Room {room_id}, {eq_text}")
            print(f"     Priority: {priority}, Status: {status}")
            print(f"     Issue: {issue}")
    except Exception as e:
        print("Error viewing tickets:", e)

#----------ADMIN-UPDATE TICKETS------------
        
def admin_update_ticket_status():
    print("\n=== Update Ticket Status ===")

    ticket_id_str = input("Ticket ID: ").strip()
    if not ticket_id_str.isdigit():
        print("Invalid ticket id.")
        return
    ticket_id = int(ticket_id_str)

    new_status = input("New status (e.g. OPEN/IN_PROGRESS/CLOSED): ").strip().upper()
    if not new_status:
        print("Status cannot be empty.")
        return

    try:
        con = get_connection()
        cur = con.cursor()

        # Basic check that ticket exists
        cur.execute(
            "SELECT status FROM MaintainenceTicket WHERE ticket_id = %s;",
            (ticket_id,)
        )
        row = cur.fetchone()
        if not row:
            print("Ticket not found.")
            cur.close()
            con.close()
            return

        cur.execute(
            "UPDATE MaintainenceTicket SET status = %s WHERE ticket_id = %s;",
            (new_status, ticket_id)
        )

        con.commit()
        cur.close()
        con.close()
        print("Ticket status updated.")
    except Exception as e:
        print("Error updating ticket:", e)



# ---------- MENUS ----------

def member_menu(user):
    while True:
        print("\n=== Member Menu ===")
        print("1. View dashboard")
        print("2. Update profile")
        print("3. Set fitness goal")
        print("4. Add health metric")
        print("5. Schedule PT session")
        print("6. Reschedule PT session")
        print("7. Register for group class")
        print("8. Logout")
        choice = input("Choose: ").strip()

        if choice == "1":
            member_dashboard(user)
        elif choice == "2":
            update_member_profile(user)
        elif choice == "3":
            set_fitness_goal(user)
        elif choice == "4":
            add_health_metric(user)
        elif choice == "5":
            schedule_pt_session(user)
        elif choice == "6":
            reschedule_pt_session(user)
        elif choice == "7":
            register_group_class(user)
        elif choice == "8":
            break
        else:
            print("Invalid choice.")

def trainer_menu(user):
    while True:
        print("\n=== Trainer Menu ===")
        print("1. View schedule")
        print("2. Set availability")
        print("3. Logout")
        choice = input("Choose: ").strip()
        if choice == "1":
            trainer_schedule_view(user)
        elif choice == "2":
            set_trainer_availability(user)
        elif choice == "3":
            break
        else:
            print("Invalid choice.")



def admin_menu(user):
    while True:
        print("\n=== Admin Menu ===")
        print("1. Equipment maintenance")
        print("2. Logout")
        choice = input("Choose: ").strip()
        if choice == "1":
            admin_equipment_maintenance(user)
        elif choice == "2":
            break
        else:
            print("Invalid choice.")

# ---------- MAIN LOOP ----------

def main():
    while True:
        print("\n=== Fitness Club System ===")
        print("1. Register Member")
        print("2. Register Trainer")
        print("3. Register Admin")
        print("4. Login")
        print("5. Exit")
        choice = input("Choose: ").strip()

        if choice == "1":
            register_member()
        elif choice == "2":
            register_trainer()
        elif choice == "3":
            register_admin()
        elif choice == "4":
            user = authenticate_user()
            if user:
                if user["role_type"] == "MEMBER":
                    member_menu(user)
                elif user["role_type"] == "TRAINER":
                    trainer_menu(user)
                elif user["role_type"] == "ADMIN":
                    admin_menu(user)
        elif choice == "5":
            print("Bye.")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()
