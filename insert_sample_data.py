import sqlite3
from datetime import date

conn = sqlite3.connect('blooddb.sqlite')
cur = conn.cursor()

# --- Donor Table ---
donors = [
    ('Riya Sharma','F','1996-05-12','A+','+91-9876501234','riya@example.com',22.5726,88.3639,'Kolkata','2025-06-01'),
    ('Amit Singh','M','1990-02-20','O+','+91-9123405678','amit@example.com',28.7041,77.1025,'Delhi','2025-08-15'),
    ('Sunita Patel','F','1987-09-08','B+','+91-9988776655','sunita@example.com',19.0760,72.8777,'Mumbai','2025-03-12'),
    ('Rahul Verma','M','1995-11-02','O-','+91-9874523456','rahul@example.com',26.9124,75.7873,'Jaipur','2025-07-22'),
    ('Neha Gupta','F','1998-07-19','AB+','+91-9554412345','neha@example.com',22.5726,88.3639,'Kolkata','2024-12-30'),
    ('Vijay Kumar','M','1985-01-11','A-','+91-9012345678','vijay@example.com',12.9716,77.5946,'Bengaluru','2025-05-05'),
    ('Preeti Rao','F','1992-04-04','B-','+91-9986001234','preeti@example.com',13.0827,80.2707,'Chennai','2025-09-01'),
    ('Karan Mehta','M','1989-10-30','O+','+91-9460001122','karan@example.com',23.2599,77.4126,'Bhopal','2025-01-10'),
    ('Sana Khan','F','1994-03-15','A+','+91-9900112233','sana@example.com',21.1458,79.0882,'Nagpur','2025-04-20'),
    ('Deepak Joshi','M','1988-12-25','B+','+91-9812340099','deepak@example.com',26.4499,80.3319,'Lucknow','2025-07-01')
]

cur.executemany("""
    INSERT INTO Donor (Name, Gender, DOB, BloodGroup, Phone, Email, Latitude, Longitude, City, LastDonationDate)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", donors)


# --- BloodBank Table ---
banks = [
    ('City Blood Bank Kolkata','Park Street, Kolkata','+91-33-40001234',22.5411,88.3525,'Kolkata'),
    ('Central Blood Bank Delhi','Connaught Place, Delhi','+91-11-30004567',28.6324,77.2197,'Delhi'),
    ('Mumbai General Blood Bank','Fort, Mumbai','+91-22-30006789',18.9402,72.8356,'Mumbai'),
    ('Jaipur Blood Center','Civil Lines, Jaipur','+91-141-30007890',26.9197,75.7870,'Jaipur'),
    ('Bengaluru Blood Hub','MG Road, Bengaluru','+91-80-30009900',12.9719,77.5980,'Bengaluru'),
    ('Nagpur Blood Bank','Sitabuldi, Nagpur','+91-712-3000111',21.1455,79.0800,'Nagpur')
]

cur.executemany("""
    INSERT INTO BloodBank (Name, Address, Phone, Latitude, Longitude, City)
    VALUES (?, ?, ?, ?, ?, ?)""", banks)


# --- Inventory Table ---
inventory = [
    (1,'A+',10,'2025-10-01'),
    (1,'O+',8,'2025-10-02'),
    (2,'O+',15,'2025-09-25'),
    (2,'B+',4,'2025-09-30'),
    (3,'B+',12,'2025-09-20'),
    (3,'A+',5,'2025-10-03'),
    (4,'O-',2,'2025-09-28'),
    (5,'A-',6,'2025-10-04'),
    (5,'O+',7,'2025-10-04'),
    (6,'AB+',3,'2025-09-29'),
    (6,'A+',4,'2025-10-05')
]

cur.executemany("""
    INSERT INTO Inventory (BankID, BloodGroup, UnitsAvailable, LastUpdated)
    VALUES (?, ?, ?, ?)""", inventory)


# --- Donation Table ---
donations = [
    (1,1,'2025-06-01',1,13.5),
    (2,2,'2025-08-15',1,14.1),
    (3,3,'2025-03-12',1,12.8),
    (4,4,'2025-07-22',1,15.0),
    (5,1,'2024-12-30',1,13.0),
    (6,5,'2025-05-05',1,14.2),
    (7,3,'2025-09-01',1,12.5),
    (8,2,'2025-01-10',1,13.9),
    (9,6,'2025-04-20',1,12.7),
    (10,4,'2025-07-01',1,13.3)
]

cur.executemany("""
    INSERT INTO Donation (DonorID, BankID, Date, Units, Hemoglobin)
    VALUES (?, ?, ?, ?, ?)""", donations)


# --- Request Table ---
requests = [
    ('Mr. Roy','A+',2,'Kolkata',22.5726,88.3639,'2025-10-10','Pending'),
    ('Mrs. Bedi','O+',3,'Delhi',28.7041,77.1025,'2025-09-25','Assigned'),
    ('Baby Arjun','B+',1,'Mumbai',19.0760,72.8777,'2025-10-05','Pending'),
    ('Ms. Sharma','O-',2,'Jaipur',26.9124,75.7873,'2025-10-01','Pending'),
    ('Mr. Khan','AB+',1,'Nagpur',21.1458,79.0882,'2025-09-30','Fulfilled'),
    ('Mrs. Reddy','A-',2,'Bengaluru',12.9716,77.5946,'2025-10-03','Pending'),
    ('Mr. Singh','O+',2,'Bhopal',23.2599,77.4126,'2025-10-08','Pending'),
    ('Ms. Roy','A+',1,'Kolkata',22.5726,88.3639,'2025-10-11','Pending'),
    ('Mr. Das','B+',2,'Lucknow',26.4499,80.3319,'2025-09-28','Assigned'),
    ('Mrs. Kapoor','O+',1,'Mumbai',19.0760,72.8777,'2025-10-12','Pending')
]

cur.executemany("""
    INSERT INTO Request (PatientName, RequiredBloodGroup, UnitsRequired, City, Latitude, Longitude, RequestDate, Status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", requests)


conn.commit()
conn.close()

print("Sample data inserted successfully!")
