import sqlite3

# connect to the database
conn = sqlite3.connect('blooddb.sqlite')
cur = conn.cursor()

# Enable foreign key support
cur.execute("PRAGMA foreign_keys = ON;")

# 1. Donor table
cur.execute("""
CREATE TABLE IF NOT EXISTS Donor (
    DonorID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Gender TEXT CHECK(Gender IN ('M','F','Other')),
    DOB DATE,
    BloodGroup TEXT NOT NULL,
    Phone TEXT,
    Email TEXT,
    Latitude REAL,
    Longitude REAL,
    City TEXT,
    LastDonationDate DATE
);
""")

# 2. BloodBank table
cur.execute("""
CREATE TABLE IF NOT EXISTS BloodBank (
    BankID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Address TEXT,
    Phone TEXT,
    Latitude REAL,
    Longitude REAL,
    City TEXT
);
""")

# 3. Inventory table
cur.execute("""
CREATE TABLE IF NOT EXISTS Inventory (
    InventoryID INTEGER PRIMARY KEY AUTOINCREMENT,
    BankID INTEGER NOT NULL,
    BloodGroup TEXT NOT NULL,
    UnitsAvailable INTEGER DEFAULT 0,
    LastUpdated DATE,
    FOREIGN KEY (BankID) REFERENCES BloodBank(BankID) ON DELETE CASCADE
);
""")

# 4. Donation table
cur.execute("""
CREATE TABLE IF NOT EXISTS Donation (
    DonationID INTEGER PRIMARY KEY AUTOINCREMENT,
    DonorID INTEGER NOT NULL,
    BankID INTEGER,
    Date DATE NOT NULL,
    Units INTEGER NOT NULL,
    Hemoglobin REAL,
    FOREIGN KEY (DonorID) REFERENCES Donor(DonorID) ON DELETE CASCADE,
    FOREIGN KEY (BankID) REFERENCES BloodBank(BankID) ON DELETE SET NULL
);
""")

# 5. Request table
cur.execute("""
CREATE TABLE IF NOT EXISTS Request (
    RequestID INTEGER PRIMARY KEY AUTOINCREMENT,
    PatientName TEXT,
    RequiredBloodGroup TEXT NOT NULL,
    UnitsRequired INTEGER NOT NULL,
    City TEXT,
    Latitude REAL,
    Longitude REAL,
    RequestDate DATE NOT NULL,
    Status TEXT CHECK(Status IN ('Pending','Assigned','Fulfilled','Cancelled')) DEFAULT 'Pending',
    AssignedBankID INTEGER,
    AssignedDonorID INTEGER,
    FOREIGN KEY (AssignedBankID) REFERENCES BloodBank(BankID),
    FOREIGN KEY (AssignedDonorID) REFERENCES Donor(DonorID)
);
""")

conn.commit()
conn.close()

print("All tables created successfully!")
