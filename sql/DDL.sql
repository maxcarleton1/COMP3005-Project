CREATE TABLE UserAccount (
	user_id			INT GENERATED ALWAYS AS IDENTITY,
	email			VARCHAR(255) NOT NULL UNIQUE,
	password		VARCHAR(255) NOT NULL,
	role_type		TEXT NOT NULL,
	is_active		BOOLEAN NOT NULL DEFAULT TRUE,
	PRIMARY KEY		(user_id),
	CHECK			(role_type IN ('MEMBER', 'TRAINER', 'ADMIN'))
);

CREATE TABLE Member (
	member_id		INT GENERATED ALWAYS AS IDENTITY,
	user_id			INT NOT NULL UNIQUE,
	name			VARCHAR(255) NOT NULL,
	dob			    DATE,
	gender			TEXT,
	phone			VARCHAR(30),
	address			VARCHAR(255),
	registration_date	DATE NOT NULL DEFAULT CURRENT_DATE,
	PRIMARY KEY		(member_id),
	FOREIGN KEY		(user_id) REFERENCES UserAccount(user_id)
);

CREATE TABLE Trainer (
	trainer_id		INT GENERATED ALWAYS AS IDENTITY,
	user_id			INT NOT NULL UNIQUE,
	name			VARCHAR(255) NOT NULL,
	start_time		TIMESTAMP NOT NULL,
	end_time		TIMESTAMP NOT NULL,
	created_at		TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY		(trainer_id),
	FOREIGN KEY		(user_id) REFERENCES UserAccount(user_id),
	CHECK			(end_time > start_time)
);

CREATE TABLE FitnessGoal (
	goal_id			INT GENERATED ALWAYS AS IDENTITY,
	member_id		INT NOT NULL,
	goal_type		VARCHAR(255),
	target_value	NUMERIC,
	start_date		DATE NOT NULL,
	end_date		DATE NOT NULL,
	PRIMARY KEY		(goal_id),
	FOREIGN KEY		(member_id) REFERENCES Member(member_id)
);

CREATE TABLE HealthMetric (
	measured_at		TIMESTAMP NOT NULL,
	member_id		INT NOT NULL,
	height			NUMERIC,
	weight			NUMERIC,
	bfp			    NUMERIC,
	heart_rate		INT,
	PRIMARY KEY		(member_id, measured_at),
	FOREIGN KEY		(member_id) REFERENCES Member(member_id)
);

CREATE TABLE Room (
	room_id			INT GENERATED ALWAYS AS IDENTITY,
	name			VARCHAR(255) NOT NULL,
	capacity		INT NOT NULL,
	location		VARCHAR(255) NOT NULL,
	PRIMARY KEY		(room_id)
);

CREATE TABLE Equipment (
	room_id			INT NOT NULL,
	equipment_no	INT NOT NULL,
	name			VARCHAR(255) NOT NULL,
	type			VARCHAR(255) NOT NULL,
	PRIMARY KEY		(room_id, equipment_no),
	FOREIGN KEY		(room_id) REFERENCES Room(room_id)
);

CREATE TABLE MaintenanceTicket (
	ticket_id		INT GENERATED ALWAYS AS IDENTITY,
	room_id			INT,
	equipment_no	INT,
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
	scheduled_at	TIMESTAMP NOT NULL,
	capacity		INT NOT NULL,
	duration_minutes	INT NOT NULL,
	PRIMARY KEY		(class_id),
	FOREIGN KEY		(trainer_id) REFERENCES Trainer(trainer_id),
	FOREIGN KEY		(room_id) REFERENCES Room(room_id)
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

CREATE TABLE ClassRegistration (
	registration_id	INT GENERATED ALWAYS AS IDENTITY,
	class_id		INT NOT NULL,
	member_id		INT NOT NULL,
	PRIMARY KEY		(registration_id),
	FOREIGN KEY		(class_id) REFERENCES GroupClass(class_id),
	FOREIGN KEY		(member_id) REFERENCES Member(member_id),
	UNIQUE			(class_id, member_id)
);

CREATE TABLE TrainerMemberAssignment (
	assignment_id	INT GENERATED ALWAYS AS IDENTITY,
	trainer_id		INT NOT NULL,
	member_id		INT NOT NULL,
	start_date		DATE NOT NULL,
	end_date		DATE,
	PRIMARY KEY		(assignment_id),
	FOREIGN KEY		(trainer_id) REFERENCES Trainer(trainer_id),
	FOREIGN KEY		(member_id) REFERENCES Member(member_id)
);
