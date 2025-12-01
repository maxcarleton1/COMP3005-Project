CREATE TABLE UserAccount (
    user_id      INT GENERATED ALWAYS AS IDENTITY,
    email        VARCHAR(255) NOT NULL UNIQUE,
    password     VARCHAR(255) NOT NULL,
    role_type    TEXT NOT NULL,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (user_id),
    CHECK (role_type IN ('MEMBER', 'TRAINER', 'ADMIN'))
);

CREATE TABLE Member (
    member_id          INT PRIMARY KEY,
    name               VARCHAR(255) NOT NULL,
    dob                DATE,
    gender             TEXT,
    phone              VARCHAR(30),
    address            VARCHAR(255),
    registration_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    FOREIGN KEY (member_id) REFERENCES UserAccount(user_id)
);

CREATE INDEX idx_member_member_id ON Member(member_id);

CREATE TABLE Trainer (
    trainer_id   INT PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    start_time   TIMESTAMP NOT NULL,
    end_time     TIMESTAMP NOT NULL,
    FOREIGN KEY (trainer_id) REFERENCES UserAccount(user_id),
    CHECK (end_time > start_time)
);

CREATE TABLE FitnessGoal (
	goal_id			INT GENERATED ALWAYS AS IDENTITY,
	member_id		INT NOT NULL,
	goal_type		VARCHAR(255),
	target_value		NUMERIC,
	start_date		DATE NOT NULL,
	end_date		DATE NOT NULL,
	PRIMARY KEY		(goal_id),
	FOREIGN KEY		(member_id) REFERENCES Member(member_id)
);

CREATE TABLE HealthMetric (
	measured_at		TIMESTAMP NOT NULL DEFAULT NOW(),
	member_id		INT NOT NULL,
	height			NUMERIC,
	weight			NUMERIC,
	bfp			NUMERIC,
	heart_rate		INT,
	PRIMARY KEY		(member_id, measured_at),
	FOREIGN KEY		(member_id) REFERENCES Member(member_id)
);

CREATE TABLE Room (
	room_id			INT GENERATED ALWAYS AS IDENTITY,
	name			VARCHAR(255) NOT NULL,
	capacity		INT NOT NULL,
	PRIMARY KEY		(room_id)
);

CREATE TABLE Equipment (
	room_id			INT NOT NULL,
	equipment_no		INT NOT NULL,
	name			VARCHAR(255) NOT NULL,
	type			VARCHAR(255) NOT NULL,
	PRIMARY KEY		(room_id, equipment_no),
	FOREIGN KEY		(room_id) REFERENCES Room(room_id)
);

CREATE TABLE MaintenanceTicket (
	ticket_id		INT GENERATED ALWAYS AS IDENTITY,
	room_id			INT,
	equipment_no		INT,
	issue			VARCHAR(255) NOT NULL,
	priority		VARCHAR(50) NOT NULL,
	status			VARCHAR(50) NOT NULL DEFAULT 'OPEN',
	PRIMARY KEY		(ticket_id),
	FOREIGN KEY		(room_id) REFERENCES Room(room_id),
	FOREIGN KEY		(room_id, equipment_no) REFERENCES Equipment(room_id, equipment_no),
	CHECK (
		(room_id IS NOT NULL AND equipment_no IS NULL)
		OR
		(room_id IS NOT NULL AND equipment_no IS NOT NULL)
	)
);

CREATE TABLE GroupClass (
	class_id		INT GENERATED ALWAYS AS IDENTITY,
	class_name		VARCHAR(255) NOT NULL,
	trainer_id		INT NOT NULL,
	room_id			INT NOT NULL,
	scheduled_at		TIMESTAMP NOT NULL,
	capacity		INT NOT NULL,
	duration_minutes	INT NOT NULL,
	PRIMARY KEY		(class_id),
	FOREIGN KEY		(trainer_id) REFERENCES Trainer(trainer_id),
	FOREIGN KEY		(room_id) REFERENCES Room(room_id)
);

CREATE TABLE ClassRegistration (
	registration_id		INT GENERATED ALWAYS AS IDENTITY,
	class_id		INT NOT NULL,
	member_id		INT NOT NULL,
	PRIMARY KEY		(registration_id),
	FOREIGN KEY		(class_id) REFERENCES GroupClass(class_id),
	FOREIGN KEY		(member_id) REFERENCES Member(member_id),
	UNIQUE			(class_id, member_id)
);

CREATE TABLE PTSession (
	session_id		INT GENERATED ALWAYS AS IDENTITY,
	member_id		INT NOT NULL,
	trainer_id		INT NOT NULL,
	room_id			INT NOT NULL,
	session_at		TIMESTAMP NOT NULL,
	duration_minutes	INT NOT NULL,
	PRIMARY KEY		(session_id),
	FOREIGN KEY		(member_id) REFERENCES Member(member_id),
	FOREIGN KEY		(trainer_id) REFERENCES Trainer(trainer_id),
	FOREIGN KEY		(room_id) REFERENCES Room(room_id)
);

--View for complete Member schedule (group classes + PT sessions)
CREATE VIEW MemberFullScheduleView AS
SELECT
    'PT'::text AS schedule_type,
    p.member_id,
    p.session_at AS start_time,
    p.session_at
        + (p.duration_minutes * INTERVAL '1 minute') AS end_time,
    p.trainer_id,
    t.name AS trainer_name,
    p.room_id,
    r.name AS room_name,
    NULL::int  AS class_id,
    NULL::text AS class_name
FROM PTSession p
JOIN Trainer t ON t.trainer_id = p.trainer_id
JOIN Room    r ON r.room_id = p.room_id

UNION ALL

SELECT
    'CLASS'::text AS schedule_type,
    cr.member_id,
    g.scheduled_at AS start_time,
    g.scheduled_at
        + (g.duration_minutes * INTERVAL '1 minute') AS end_time,
    g.trainer_id,
    t.name AS trainer_name,
    g.room_id,
    r.name AS room_name,
    g.class_id,
    g.class_name
FROM ClassRegistration cr
JOIN GroupClass g ON g.class_id = cr.class_id
JOIN Trainer   t ON t.trainer_id = g.trainer_id
JOIN Room      r ON r.room_id   = g.room_id;

--Trigger function to enforce group class capacity
CREATE OR REPLACE FUNCTION check_class_capacity()
RETURNS TRIGGER
LANGUAGE plpgsql
AS
$$
DECLARE
    v_capacity   INT;
    v_count      INT;
BEGIN
    SELECT capacity
    INTO v_capacity
    FROM GroupClass
    WHERE class_id = NEW.class_id
    FOR UPDATE;

    IF v_capacity IS NULL THEN
        RAISE EXCEPTION 'Class % not found or has NULL capacity', NEW.class_id;
    END IF;
    SELECT COUNT(*)
    INTO v_count
    FROM ClassRegistration
    WHERE class_id = NEW.class_id;
    v_count := v_count + 1;

    IF v_count > v_capacity THEN
        RAISE EXCEPTION
            'Class % is full. Capacity=%, registrations_with_new=%',
            NEW.class_id, v_capacity, v_count;
    END IF;

    RETURN NEW;
END;
$$;

--Trigger
CREATE TRIGGER trg_check_class_capacity
BEFORE INSERT
ON ClassRegistration
FOR EACH ROW
EXECUTE PROCEDURE
check_class_capacity();

