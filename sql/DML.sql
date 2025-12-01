INSERT INTO UserAccount (email, password, role_type, is_active) VALUES
('alice@example.com', 'password1', 'MEMBER', TRUE),
('dave@example.com', 'password2', 'MEMBER', TRUE),
('bill@example.com', 'password3', 'MEMBER', TRUE),
('bob@example.com', 'password4', 'TRAINER', TRUE),
('john@example.com', 'password5', 'TRAINER', TRUE),
('phil@example.com', 'password6', 'TRAINER', TRUE),
('carol@example.com', 'password7', 'ADMIN', TRUE);

INSERT INTO Member (member_id, name, dob, gender, phone, address, registration_date) VALUES
(1, 'Alice Johnson', '1990-01-01', 'Female', '555-0001', '123 Maple St', '2025-01-01'),
(2, 'Dave Smith', '1990-02-02', 'Male', '555-0002', '456 Oak St', '2025-02-02'),
(3, 'Bill Williams', '1990-03-03', 'Male', '555-0003', '789 Pine St', '2025-03-03');

INSERT INTO Trainer (trainer_id, name, start_time, end_time) VALUES
(4, 'Bob Michaels', '2025-11-01 09:00:00', '2025-11-01 17:00:00'),
(5, 'John Cena', '2025-11-02 10:00:00', '2025-11-02 19:00:00'),
(6, 'Phil Gains', '2025-12-01 08:00:00', '2025-12-08 16:00:00');

INSERT INTO FitnessGoal (member_id, goal_type, target_value, start_date, end_date) VALUES
(1, 'Weight Loss', 15.0, '2025-12-01', '2025-12-30'),
(2, 'Muscle Gain', 10.0, '2026-01-01', '2026-03-01'),
(3, 'Sprint Time', 25.0, '2025-12-01', '2025-12-10');

INSERT INTO HealthMetric (member_id, measured_at, height, weight, bfp, heart_rate) VALUES
(1, '2025-12-02 08:00:00', 165, 75, 22.5, 72),
(1, '2025-12-05 09:00:00', 165, 78, 18.0, 78),
(1, '2025-12-09 10:00:00', 165, 76, 20.0, 70),
(2, '2025-11-01 14:00:00', 180, 85, 22.0, 90);

INSERT INTO Room (name, capacity) VALUES
('Room A', 20),
('Room B', 10),
('Room C', 4),
('Room D', 30);

INSERT INTO Equipment (room_id, equipment_no, name, type) VALUES
(1, 1, 'Treadmill', 'Cardio'),
(1, 2, 'Exercise Bike', 'Cardio'),
(2, 1, 'Dumbbells', 'Strength'),
(3, 1, 'Resistance Bands', 'Strength');

INSERT INTO MaintenanceTicket (room_id, equipment_no, issue, priority, status) VALUES
(1, 1, 'Treadmill belt is slipping', 'High', 'OPEN'),
(1, 2, 'Exercise bike makes noise', 'Medium', 'OPEN'),
(3, NULL, 'AC is not working', 'Low', 'OPEN');

INSERT INTO GroupClass (class_name, trainer_id, room_id, scheduled_at, capacity, duration_minutes) VALUES
('Yoga Basics', 4, 1, '2025-11-30 10:00:00', 10, 60),
('Pushup Competition', 5, 2, '2025-11-30 14:00:00', 15, 45),
('Pilates', 6, 4, '2025-12-03 08:30:00', 25, 60);

INSERT INTO ClassRegistration (class_id, member_id) VALUES
(1, 1),
(2, 2),
(3, 3);

INSERT INTO PTSession (member_id, trainer_id, room_id, session_at, duration_minutes) VALUES
(1, 4, 1, '2025-12-05 11:00:00', 60),
(2, 5, 2, '2025-12-17 15:00:00', 45),
(3, 6, 3, '2025-12-11 09:00:00', 60);