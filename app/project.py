import psycopg2
from datetime import datetime, timedelta

DB_CONFIG = {
    "host": "localhost",
    "database": "a1_database",
    "user": "postgres",
    "password": "postgres",
    "port": "5432"
}

TIME_FORMAT = "%Y-%m-%d %H:%M"


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# ---------- SMALL HELPERS ----------

def get_member_id(user_id):
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT member_id FROM Member WHERE member_id = %s;", (user_id,))
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
        cur.execute("SELECT trainer_id FROM Trainer WHERE trainer_id = %s;", (user_id,))
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
            "INSERT INTO Member (member_id, name, dob, gender, phone, address) "
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

    print("\nSet initial availability window.")
    print(f"Format: YYYY-MM-DD HH:MM  (e.g. 2025-01-01 09:00)")
    start_str = input("Availability start: ").strip()
    end_str = input("Availability end: ").strip()

    try:
        start_time = datetime.strptime(start_str, TIME_FORMAT)
        end_time = datetime.strptime(end_str, TIME_FORMAT)
    except ValueError:
        print("Invalid date/time format for availability.")
        return

    if start_time >= end_time:
        print("Availability start time must be before end time.")
        return

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
            "INSERT INTO Trainer (trainer_id, name, start_time, end_time) "
            "VALUES (%s, %s, %s, %s);",
            (user_id, name, start_time, end_time)
        )

        con.commit()
        cur.close()
        con.close()
        print("Trainer registered with availability set.")
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
            "SELECT start_time, end_time "
            "FROM Trainer WHERE trainer_id = %s;",
            (trainer_id,)
        )
        row = cur.fetchone()
        if not row:
            print("Trainer not found.")
            cur.close()
            con.close()
            return

        old_start, old_end = row

        print("Current availability:")
        print("  Start:", old_start)
        print("  End:  ", old_end)

        print("\nEnter new availability window.")
        print(f"Format: {TIME_FORMAT}")
        start_str = input("New start time: ").strip()
        end_str = input("New end time: ").strip()

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
            "SET start_time = %s, end_time = %s "
            "WHERE trainer_id = %s;",
            (new_start, new_end, trainer_id)
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
    start_date = input("Start date (YYYY-MM-DD): ").strip()
    end_date = input("End date (YYYY-MM-DD): ").strip()

    if not start_date or not end_date:
        print("Start date and end date are required.")
        return

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

    # Final check
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
    
    try:
        con = get_connection()
        cur = con.cursor()

        # 1. List upcoming group classes with their capacity and current registrations
        cur.execute(
            """
            SELECT gc.class_id,
                   gc.class_name,
                   gc.scheduled_at,
                   gc.duration_minutes,
                   gc.room_id,
                   gc.trainer_id,
                   gc.capacity
            FROM GroupClass gc
            WHERE gc.scheduled_at >= NOW()
            ORDER BY gc.scheduled_at;
            """
        )
        classes = cur.fetchall()

        if not classes:
            print("No upcoming group classes available.")
            cur.close()
            con.close()
            return
        
        class_ids = [row[0] for row in classes]
        cur.execute(
            "SELECT class_id, COUNT(*) FROM ClassRegistration "
            "WHERE class_id = ANY(%s) GROUP BY class_id;",
            (class_ids,)
        )
        reg_counts_rows = cur.fetchall()
        reg_counts = {r[0]: r[1] for r in reg_counts_rows}

        print("\nUpcoming classes:")
        for cls in classes:
            cid, cname, sched, dur, room_id, trainer_id, cap = cls
            reg_count = reg_counts.get(cid, 0)
            spots_left = cap - reg_count
            print(
                f"  ID {cid}: {cname} at {sched} ({dur} min), room {room_id}, "
                f"trainer {trainer_id} -> {reg_count}/{cap} registered, {spots_left} spots left"
            )

        class_id_str = input("Enter class ID to register (or press Enter to cancel): ").strip()
        if not class_id_str:
            print("Registration cancelled.")
            cur.close()
            con.close()
            return
        
        if not class_id_str.isdigit():
            print("Invalid class ID. Registration cancelled.")
            cur.close()
            con.close()
            return
        
        class_id = int(class_id_str)

        # 2. Get selected class details
        cur.execute(
            """
            SELECT class_id, class_name, scheduled_at, duration_minutes,
                   room_id, trainer_id, capacity
            FROM GroupClass WHERE class_id = %s;
            """,
            (class_id,)
        )
        row = cur.fetchone()
        if not row:
            print("Class not found. Registration cancelled.")
            cur.close()
            con.close()
            return
        
        cid, cname, scheduled_at, duration_minutes, room_id, trainer_id, class_capacity = row

        cur.execute("SELECT NOW();")
        now = cur.fetchone()[0]
        if scheduled_at < now:
            print("Cannot register: class has already started or is in the past.")
            cur.close()
            con.close()
            return
        
        # Check if member already registered
        cur.execute(
            "SELECT 1 FROM ClassRegistration WHERE member_id = %s AND class_id = %s;",
            (member_id, class_id)
        )
        if cur.fetchone():
            print("You are already registered for this class.")
            cur.close()
            con.close()
            return
        
        cur.execute(
            "SELECT COUNT(*) FROM ClassRegistration WHERE class_id = %s;",
            (class_id,)
        )
        reg_count = cur.fetchone()[0]

        if reg_count >= class_capacity:
            print("Class is full. Cannot register.")
            cur.close()
            con.close()
            return
        
        new_start = scheduled_at
        new_end = scheduled_at + timedelta(minutes=duration_minutes)

        cur.execute(
            "SELECT class_id, scheduled_at, duration_minutes "
            "FROM GroupClass WHERE room_id = %s AND class_id != %s;",
            (room_id, class_id)
        )
        other_classes = cur.fetchall()
        for oc_id, oc_start, oc_dur in other_classes:
            oc_end = oc_start + timedelta(minutes=oc_dur)
            if times_overlap(new_start, new_end, oc_start, oc_end):
                print(
                    f"Conflict: another group class (ID {oc_id}) is scheduled in "
                    f"room {room_id} and overlaps this class."
                )
                cur.close()
                con.close()
                return
        
        cur.execute(
            "SELECT session_at, duration_minutes FROM PTSession WHERE room_id = %s;",
            (room_id,)
        )
        pt_in_room = cur.fetchall()
        for s_at, s_dur in pt_in_room:
            s_end = s_at + timedelta(minutes=s_dur)
            if times_overlap(new_start, new_end, s_at, s_end):
                print(
                    f"Conflict: a PT session is scheduled in room {room_id} "
                    f"that overlaps this class."
                )
                cur.close()
                con.close()
                return
        
        cur.execute(
            "SELECT session_at, duration_minutes FROM PTSession WHERE member_id = %s;",
            (member_id,)
        )
        member_pt = cur.fetchall()
        for s_at, s_dur in member_pt:
            s_end = s_at + timedelta(minutes=s_dur)
            if times_overlap(new_start, new_end, s_at, s_end):
                print("Cannot register: you have a PT session that overlaps this class.")
                cur.close()
                con.close()
                return
            
        cur.execute(
            """
            SELECT gc.class_id, gc.scheduled_at, gc.duration_minutes
            FROM ClassRegistration cr
            JOIN GroupClass gc ON cr.class_id = gc.class_id
            WHERE cr.member_id = %s;
            """,
            (member_id,)
        )
        member_classes = cur.fetchall()
        for m_cid, m_start, m_dur in member_classes:
            m_end = m_start + timedelta(minutes=m_dur)
            if times_overlap(new_start, new_end, m_start, m_end):
                print(
                    f"Cannot register: you are already registered for class ID {m_cid} "
                    "which overlaps this class."
                )
                cur.close()
                con.close()
                return

        try:
            cur.execute(
                "INSERT INTO ClassRegistration (class_id, member_id) "
                "VALUES (%s, %s) RETURNING registration_id;",
                (class_id, member_id)
            )
            res = cur.fetchone()
            if res:
                con.commit()
                print("Successfully registered for the class.")
            else:
                con.rollback()
                print("Could not register for the class.")
        except psycopg2.IntegrityError:
            con.rollback()
            print("Registration failed: you may already be registered or constraint violated.")

        cur.close()
        con.close()

    except Exception as e:
        try:
            con.rollback()
        except:
            pass
        print("Error registering for class:", e)


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


#----------ADMIN-EQUIPMENT MAINTENANCE MENU------------

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

        # Insert ticket
        cur.execute(
            """
            INSERT INTO MaintenanceTicket (room_id, equipment_no, issue, priority, status)
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
                FROM MaintenanceTicket
                WHERE status = %s
                ORDER BY ticket_id;
                """,
                (status_filter,)
            )
        else:
            cur.execute(
                """
                SELECT ticket_id, room_id, equipment_no, issue, priority, status
                FROM MaintenanceTicket
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
            "SELECT status FROM MaintenanceTicket WHERE ticket_id = %s;",
            (ticket_id,)
        )
        row = cur.fetchone()
        if not row:
            print("Ticket not found.")
            cur.close()
            con.close()
            return

        cur.execute(
            "UPDATE MaintenanceTicket SET status = %s WHERE ticket_id = %s;",
            (new_status, ticket_id)
        )

        con.commit()
        cur.close()
        con.close()
        print("Ticket status updated.")
    except Exception as e:
        print("Error updating ticket:", e)


#----------ADMIN-ROOM BOOKING------------

def admin_book_room(user):
    while True:
        print("\n=== Admin: Book Room ===")
        print("1. Assign room to existing PT session")
        print("2. Assign room to existing Group class")
        print("3. Back")
        choice = input("Choose: ").strip()

        if choice == "3":
            break
        if choice not in ("1", "2"):
            print("Invalid choice.")
            continue

        try:
            con = get_connection()
            cur = con.cursor()

            if choice == "1":  # Update PT session
                session_id_str = input("Enter PT session_id: ").strip()
                if not session_id_str.isdigit():
                    print("Invalid session id.")
                    cur.close()
                    con.close()
                    continue
                session_id = int(session_id_str)

                cur.execute(
                    "SELECT session_at, duration_minutes, room_id "
                    "FROM PTSession WHERE session_id = %s;",
                    (session_id,)
                )
                row = cur.fetchone()
                if not row:
                    print("PT session not found.")
                    cur.close()
                    con.close()
                    continue

                session_at, duration_minutes, current_room = row
                available_rooms = get_available_rooms(session_at, duration_minutes)

                if current_room is not None and current_room not in available_rooms:
                    available_rooms.append(current_room)

                if not available_rooms:
                    print("No rooms available for that PT session time.")
                    cur.close()
                    con.close()
                    continue

                print("Available rooms (room_id):", ", ".join(str(r) for r in available_rooms))
                room_id_str = input("Select room_id to assign: ").strip()
                if not room_id_str.isdigit():
                    print("Invalid room id.")
                    cur.close()
                    con.close()
                    continue
                room_id = int(room_id_str)

                if room_id not in available_rooms:
                    print("Selected room is not available.")
                    cur.close()
                    con.close()
                    continue

                cur.execute("SELECT 1 FROM Room WHERE room_id = %s;", (room_id,))
                if not cur.fetchone():
                    print("Room not found.")
                    cur.close()
                    con.close()
                    continue

                cur.execute(
                    "UPDATE PTSession SET room_id = %s WHERE session_id = %s;",
                    (room_id, session_id)
                )
                con.commit()
                print(f"PT session {session_id} assigned to room {room_id}.")

            else:  # Update group class
                class_id_str = input("Enter Group class_id: ").strip()
                if not class_id_str.isdigit():
                    print("Invalid class id.")
                    cur.close()
                    con.close()
                    continue
                class_id = int(class_id_str)

                cur.execute(
                    "SELECT scheduled_at, duration_minutes, room_id "
                    "FROM GroupClass WHERE class_id = %s;",
                    (class_id,)
                )
                row = cur.fetchone()
                if not row:
                    print("Group class not found.")
                    cur.close()
                    con.close()
                    continue

                scheduled_at, duration_minutes, current_room = row
                available_rooms = get_available_rooms(scheduled_at, duration_minutes)

                # Allow keeping current room even if helper filters it out
                if current_room is not None and current_room not in available_rooms:
                    available_rooms.append(current_room)

                if not available_rooms:
                    print("No rooms available for that class time.")
                    cur.close()
                    con.close()
                    continue

                print("Available rooms (room_id):", ", ".join(str(r) for r in available_rooms))
                room_id_str = input("Select room_id to assign: ").strip()
                if not room_id_str.isdigit():
                    print("Invalid room id.")
                    cur.close()
                    con.close()
                    continue
                room_id = int(room_id_str)

                if room_id not in available_rooms:
                    print("Selected room is not available.")
                    cur.close()
                    con.close()
                    continue

                cur.execute("SELECT 1 FROM Room WHERE room_id = %s;", (room_id,))
                if not cur.fetchone():
                    print("Room not found.")
                    cur.close()
                    con.close()
                    continue

                cur.execute(
                    "UPDATE GroupClass SET room_id = %s WHERE class_id = %s;",
                    (room_id, class_id)
                )
                con.commit()
                print(f"Group class {class_id} assigned to room {room_id}.")

            cur.close()
            con.close()

        except Exception as e:
            print("Error booking room:", e)
            try:
                cur.close()
            except:
                pass
            try:
                con.close()
            except:
                pass


#----------ADMIN-CLASS MANAGEMENT------------

def admin_manage_classes(user):
    print("\n=== Manage Group Classes ===")

    def room_exists(cur, room_id):
        cur.execute("SELECT 1 FROM Room WHERE room_id = %s;", (room_id,))
        return cur.fetchone() is not None

    def trainer_exists(cur, trainer_id):
        cur.execute("SELECT 1 FROM Trainer WHERE trainer_id = %s;", (trainer_id,))
        return cur.fetchone() is not None

    def check_room_available_excluding_class(cur, room_id, new_start, duration_minutes, exclude_class_id=None):
        new_end = new_start + timedelta(minutes=duration_minutes)

        cur.execute("SELECT capacity FROM Room WHERE room_id = %s;", (room_id,))
        row = cur.fetchone()
        if not row:
            return False
        capacity = row[0]

        # Count overlapping PT sessions in this room
        cur.execute("SELECT session_at, duration_minutes FROM PTSession WHERE room_id = %s;", (room_id,))
        pt_sessions = cur.fetchall()
        concurrent_pt = 0
        for s_at, dur in pt_sessions:
            s_end = s_at + timedelta(minutes=dur)
            if times_overlap(new_start, new_end, s_at, s_end):
                concurrent_pt += 1

        if concurrent_pt >= capacity:
            return False

        # Check group classes in the room
        if exclude_class_id is None:
            cur.execute(
                "SELECT scheduled_at, duration_minutes FROM GroupClass WHERE room_id = %s;",
                (room_id,)
            )
        else:
            cur.execute(
                "SELECT scheduled_at, duration_minutes FROM GroupClass "
                "WHERE room_id = %s AND class_id != %s;",
                (room_id, exclude_class_id)
            )
        gc_list = cur.fetchall()
        for gc_start, gc_dur in gc_list:
            gc_end = gc_start + timedelta(minutes=gc_dur)
            if times_overlap(new_start, new_end, gc_start, gc_end):
                return False

        return True

    def check_trainer_available_excluding_class(cur, trainer_id, new_start, duration_minutes, exclude_class_id=None):
        new_end = new_start + timedelta(minutes=duration_minutes)

        cur.execute("SELECT start_time, end_time FROM Trainer WHERE trainer_id = %s;", (trainer_id,))
        row = cur.fetchone()
        if not row:
            return False
        avail_start, avail_end = row
        if avail_start and avail_end:
            if not (new_start.time() >= avail_start.time() and new_end.time() <= avail_end.time()):
                return False

        # Check trainer's PT sessions
        cur.execute("SELECT session_at, duration_minutes FROM PTSession WHERE trainer_id = %s;", (trainer_id,))
        pt_sessions = cur.fetchall()
        for s_at, dur in pt_sessions:
            s_end = s_at + timedelta(minutes=dur)
            if times_overlap(new_start, new_end, s_at, s_end):
                return False

        # Check trainer's group classes (exclude provided class id)
        if exclude_class_id is None:
            cur.execute("SELECT scheduled_at, duration_minutes FROM GroupClass WHERE trainer_id = %s;", (trainer_id,))
        else:
            cur.execute(
                "SELECT scheduled_at, duration_minutes FROM GroupClass "
                "WHERE trainer_id = %s AND class_id != %s;",
                (trainer_id, exclude_class_id)
            )
        gc_list = cur.fetchall()
        for gc_start, gc_dur in gc_list:
            gc_end = gc_start + timedelta(minutes=gc_dur)
            if times_overlap(new_start, new_end, gc_start, gc_end):
                return False

        return True

    while True:
        print("\n--- Class Management ---")
        print("1. Create new class")
        print("2. Update existing class")
        print("3. View classes")
        print("4. Back")
        choice = input("Choose: ").strip()

        if choice == "1":
            class_name = input("Class name: ").strip()
            if not class_name:
                print("Class name required.")
                continue

            trainer_id_str = input("Trainer ID: ").strip()
            room_id_str = input("Room ID: ").strip()
            sched_str = input(f"Scheduled at ({TIME_FORMAT}): ").strip()
            capacity_str = input("Capacity (int): ").strip()
            duration_str = input("Duration minutes (int): ").strip()

            try:
                trainer_id = int(trainer_id_str)
                room_id = int(room_id_str)
                scheduled_at = datetime.strptime(sched_str, TIME_FORMAT)
                capacity = int(capacity_str)
                duration_minutes = int(duration_str)
            except Exception:
                print("Invalid input for trainer/room/time/capacity/duration.")
                continue

            if capacity <= 0:
                print("Capacity must be a positive integer.")
                continue

            try:
                con = get_connection()
                cur = con.cursor()

                if not trainer_exists(cur, trainer_id):
                    print("Trainer not found.")
                    cur.close()
                    con.close()
                    continue
                if not room_exists(cur, room_id):
                    print("Room not found.")
                    cur.close()
                    con.close()
                    continue

                # Check availability using helper functions
                available_rooms = get_available_rooms(scheduled_at, duration_minutes)
                available_trainers = get_available_trainers(scheduled_at, duration_minutes)
                if room_id not in available_rooms:
                    print("Room not available at that time.")
                    cur.close()
                    con.close()
                    continue
                if trainer_id not in available_trainers:
                    print("Trainer not available at that time.")
                    cur.close()
                    con.close()
                    continue

                cur.execute(
                    "INSERT INTO GroupClass (class_name, trainer_id, room_id, scheduled_at, capacity, duration_minutes) "
                    "VALUES (%s, %s, %s, %s, %s, %s);",
                    (class_name, trainer_id, room_id, scheduled_at, capacity, duration_minutes)
                )
                con.commit()
                cur.close()
                con.close()
                print("Group class created.")
            except Exception as e:
                print("Error creating class:", e)

        elif choice == "2":
            class_id_str = input("Enter class ID to update: ").strip()
            if not class_id_str.isdigit():
                print("Invalid class id.")
                continue
            class_id = int(class_id_str)

            try:
                con = get_connection()
                cur = con.cursor()

                cur.execute(
                    "SELECT class_name, trainer_id, room_id, scheduled_at, capacity, duration_minutes "
                    "FROM GroupClass WHERE class_id = %s;",
                    (class_id,)
                )
                row = cur.fetchone()
                if not row:
                    print("Class not found.")
                    cur.close()
                    con.close()
                    continue

                old_name, old_trainer_id, old_room_id, old_scheduled_at, old_capacity, old_duration = row
                print("Current values (press Enter to keep):")
                print("Name:", old_name)
                print("Trainer ID:", old_trainer_id)
                print("Room ID:", old_room_id)
                print("Scheduled at:", old_scheduled_at)
                print("Capacity:", old_capacity)
                print("Duration (min):", old_duration)

                name = input("New name: ").strip() or old_name
                trainer_id_in = input("New trainer ID: ").strip()
                room_id_in = input("New room ID: ").strip()
                sched_in = input(f"New scheduled at ({TIME_FORMAT}): ").strip()
                capacity_in = input("New capacity: ").strip()
                duration_in = input("New duration minutes: ").strip()

                try:
                    trainer_id = int(trainer_id_in) if trainer_id_in != "" else old_trainer_id
                except ValueError:
                    print("Invalid trainer id.")
                    cur.close()
                    con.close()
                    continue

                try:
                    room_id = int(room_id_in) if room_id_in != "" else old_room_id
                except ValueError:
                    print("Invalid room id.")
                    cur.close()
                    con.close()
                    continue

                if sched_in == "":
                    scheduled_at = old_scheduled_at
                else:
                    try:
                        scheduled_at = datetime.strptime(sched_in, TIME_FORMAT)
                    except ValueError:
                        print("Invalid scheduled time format.")
                        cur.close()
                        con.close()
                        continue

                try:
                    capacity = int(capacity_in) if capacity_in != "" else old_capacity
                except ValueError:
                    print("Invalid capacity.")
                    cur.close()
                    con.close()
                    continue

                try:
                    duration_minutes = int(duration_in) if duration_in != "" else old_duration
                except ValueError:
                    print("Invalid duration.")
                    cur.close()
                    con.close()
                    continue

                if capacity <= 0:
                    print("Capacity must be a positive integer.")
                    cur.close()
                    con.close()
                    continue

                if not trainer_exists(cur, trainer_id):
                    print("Trainer not found.")
                    cur.close()
                    con.close()
                    continue
                if not room_exists(cur, room_id):
                    print("Room not found.")
                    cur.close()
                    con.close()
                    continue

                # Ensure new capacity is not less than current registrations
                cur.execute(
                    "SELECT COUNT(*) FROM ClassRegistration WHERE class_id = %s;",
                    (class_id,)
                )
                current_reg = cur.fetchone()[0]
                if capacity < current_reg:
                    print(
                        f"Cannot set capacity to {capacity}: there are already "
                        f"{current_reg} members registered."
                    )
                    cur.close()
                    con.close()
                    continue

                room_ok = check_room_available_excluding_class(
                    cur, room_id, scheduled_at, duration_minutes, exclude_class_id=class_id
                )
                trainer_ok = check_trainer_available_excluding_class(
                    cur, trainer_id, scheduled_at, duration_minutes, exclude_class_id=class_id
                )
                if not room_ok:
                    print("Room not available at the requested time (conflict detected).")
                    cur.close()
                    con.close()
                    continue
                if not trainer_ok:
                    print("Trainer not available at the requested time (conflict detected).")
                    cur.close()
                    con.close()
                    continue

                cur.execute(
                    "UPDATE GroupClass "
                    "SET class_name = %s, trainer_id = %s, room_id = %s, "
                    "scheduled_at = %s, capacity = %s, duration_minutes = %s "
                    "WHERE class_id = %s;",
                    (name, trainer_id, room_id, scheduled_at, capacity, duration_minutes, class_id)
                )
                con.commit()
                cur.close()
                con.close()
                print("Class updated.")
            except Exception as e:
                print("Error updating class:", e)

        elif choice == "3":  # View classes
            print("\nView classes options:")
            print("1. All classes")
            print("2. Upcoming classes")
            print("3. By trainer")
            print("4. By room")
            sub = input("Choose: ").strip()

            try:
                con = get_connection()
                cur = con.cursor()

                if sub == "1":
                    cur.execute(
                        "SELECT class_id, class_name, trainer_id, room_id, scheduled_at, capacity, duration_minutes "
                        "FROM GroupClass ORDER BY scheduled_at;"
                    )
                    rows = cur.fetchall()
                elif sub == "2":
                    cur.execute(
                        "SELECT class_id, class_name, trainer_id, room_id, scheduled_at, capacity, duration_minutes "
                        "FROM GroupClass WHERE scheduled_at >= NOW() ORDER BY scheduled_at;"
                    )
                    rows = cur.fetchall()
                elif sub == "3":
                    t_str = input("Trainer ID: ").strip()
                    if not t_str.isdigit():
                        print("Invalid trainer id.")
                        cur.close()
                        con.close()
                        continue
                    t_id = int(t_str)
                    cur.execute(
                        "SELECT class_id, class_name, trainer_id, room_id, scheduled_at, capacity, duration_minutes "
                        "FROM GroupClass WHERE trainer_id = %s ORDER BY scheduled_at;",
                        (t_id,)
                    )
                    rows = cur.fetchall()
                elif sub == "4":
                    r_str = input("Room ID: ").strip()
                    if not r_str.isdigit():
                        print("Invalid room id.")
                        cur.close()
                        con.close()
                        continue
                    r_id = int(r_str)
                    cur.execute(
                        "SELECT class_id, class_name, trainer_id, room_id, scheduled_at, capacity, duration_minutes "
                        "FROM GroupClass WHERE room_id = %s ORDER BY scheduled_at;",
                        (r_id,)
                    )
                    rows = cur.fetchall()
                else:
                    print("Invalid choice.")
                    cur.close()
                    con.close()
                    continue

                if not rows:
                    print("No classes found.")
                else:
                    for cid, cname, tid, rid, sched, cap, dur in rows:
                        print(f"[{cid}] {cname} — trainer {tid}, room {rid}, at {sched}, cap {cap}, {dur} min")

                cur.close()
                con.close()
            except Exception as e:
                print("Error loading classes:", e)

        elif choice == "4":
            break
        else:
            print("Invalid choice.")


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
        print("2. Book room")
        print("3. Manage group classes")
        print("4. Logout")
        choice = input("Choose: ").strip()
        if choice == "1":
            admin_equipment_maintenance(user)
        elif choice == "2":
            admin_book_room(user)
        elif choice == "3":
            admin_manage_classes(user)
        elif choice == "4":
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
            print("Exiting...")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
