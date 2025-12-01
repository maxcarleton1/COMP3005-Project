# COMP3005-Project
## Health and Fitness Club Management System
### Team:
Max Sobota, 101307952  
Jyoti Parkash Sethi, 101253551

### Application
The schema is inside the DDL.sql file.  
The application comes with premade data for each table, stored in the DML.sql file.  
It's not explicitly stated in the project document, so we are assuming that the queries in DDL.sql and DML.sql will be run before project.py.

### Installation and running
This project relies on the psycopg2 library to interface with PostgreSQL, which can be downloaded using:  
`pip install psycopg2`

To interface with the database, psycopg2 creates a connection using some login parameters.  
We set the parameters to the defaults for our systems, but if your PostgreSQL is different, you may have to change the database name, host name, password, etc. at the top of project.py.

The application can be run with:  
`python project.py`

### Video
Link here

### Notes
The project document says to submit a "complete project that includes the implementation, report, SQL files (if applicable), and a demonstration video",
but later in the discussion forums, Joey Villeneuve stated that we "should submit a small text file containing a both a link to your GitHub and the video, not a .zip file",
so we submitted the text file.

TO DO:  
Add video to google drive  

For video:
Show registering each user and updated tables with:
SELECT * FROM UserAccount;
SELECT * FROM Member;
SELECT * FROM Trainer;

Show login authentication

For member, show:
1. View dashboard 
SELECT * FROM HealthMetric;
SELECT * FROM FitnessGoal;
SELECT * FROM PTSession;
SELECT * FROM ClassRegistration;
2. Update profile
SELECT * FROM Member;
3. Set fitness goal
SELECT * FROM FitnessGoal;
4. Add health metric
SELECT * FROM HealthMetric;
5. Schedule PT session
SELECT * FROM PTSession;
6. Reschedule PT session
SELECT * FROM PTSession;
7. Register for group class
SELECT * FROM ClassRegistration;

For trainer, show:
1. View schedule
SELECT * FROM PTSession;
SELECT * FROM GroupClass;
2. Set availability
SELECT * FROM Trainer;

For admin, show:
1. Equipment maintenance
    1. Log new issue
    SELECT * FROM Equipment;
    SELECT * FROM MaintenanceTicket;
    2. View tickets
    SELECT * FROM MaintenanceTicket;
    3. Update ticket status
    SELECT * FROM MaintenanceTicket;
2. Book room
    1. Assign room to existing PT session
    SELECT * FROM PTSession;
    2. Assign room to existing Group class
    SELECT * FROM GroupClass;
3. Manage group classes
    1. Create new class
    SELECT * FROM GroupClass;
    2. Update existing class
    SELECT * FROM GroupClass;
    3. View classes
    SELECT * FROM GroupClass;

DROP TABLE UserAccount CASCADE;
DROP TABLE Member CASCADE;
DROP TABLE Trainer CASCADE;
DROP TABLE FitnessGoal CASCADE;
DROP TABLE HealthMetric CASCADE;
DROP TABLE Room CASCADE;
DROP TABLE Equipment CASCADE;
DROP TABLE MaintenanceTicket CASCADE;
DROP TABLE GroupClass CASCADE;
DROP TABLE ClassRegistration CASCADE;
DROP TABLE PTSession CASCADE;

SELECT * FROM UserAccount;
SELECT * FROM Member;
SELECT * FROM Trainer;
SELECT * FROM FitnessGoal;
SELECT * FROM HealthMetric;
SELECT * FROM Room;
SELECT * FROM Equipment;
SELECT * FROM MaintenanceTicket;
SELECT * FROM GroupClass;
SELECT * FROM ClassRegistration;
SELECT * FROM PTSession;