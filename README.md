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
https://drive.google.com/file/d/1UgdDdpix8EWRKyEt_MBaV45jToNgF7y-/view?usp=sharing
It was difficult to fit all the application functionality in a short video, so we glossed over some of the finer error checking details.  
We also sped it up a little to try and reduce the runtime, so if I sound a little goofy, that's why.  
Joey Villeneuve in the discussion forums specified that videos "up to 25 minutes" were allowed, so we tried to fit it in that window.

### Notes
The project document says to submit a "complete project that includes the implementation, report, SQL files (if applicable), and a demonstration video",
but later in the discussion forums, Joey Villeneuve stated that we "should submit a small text file containing a both a link to your GitHub and the video, not a .zip file",
so we submitted the text file.