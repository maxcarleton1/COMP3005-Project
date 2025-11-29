# COMP3005-Project
## Health and Fitness Club Management System
### Team:
Max Sobota, 101307952  
Jyoti Parkash Sethi, 101253551

### Application
The application comes with premade data for each table, stored in the DML.sql file.

### Installation and running
This project relies on the psycopg2 library to interface with PostgreSQL, which can be downloaded using:  
`pip install psycopg2`

To interface with the database, psycopg2 creates a connection using some login parameters.  
We set the parameters to the defaults for our systems, but if your PostgreSQL is different, you may have to change the database name, host name, password, etc. in project.py.

The application can be run with:
`python project.py`

### Video
Link here

### Notes
The project document says to submit a "complete project that includes the implementation, report, SQL files (if applicable), and a demonstration video",
but later in the discussion forums, Joey Villeneuve stated that we "should submit a small text file containing a both a link to your GitHub and the video, not a .zip file",
so we submitted the text file.

TO DO:  
Add premade tables to DML.sql  
Make sure tables are built and populated on startup (do in code? idk)  
Change repository to public  
Add video to google drive  
Submit with a .txt file (github and video link)  

NOTES:  
admin_book_room kinda doesn't make much sense since rooms are assigned in schedule_pt_session and admin_manage_classes, I just made it update existing PTSessions or GroupClasses.  
admin_manage_classes has a view classes feature, but it's probably not necessary