# app.py
import streamlit as st
import sqlite3
from datetime import date, datetime, timedelta
import re
import os
import random
import json
import smtplib
from email.message import EmailMessage

# ---------- CONFIG ----------
DB = "blood_donation.db"
ADMIN_PIN = "1234"                 # keep for destructive ops
INACTIVE_DAYS = 180
LOW_INVENTORY_THRESHOLD = 5

# OTP / email controls
SEND_EMAILS = True                 # True => send real emails via email_config.json
OTP_EXPIRY_MINUTES = 5
EMAIL_CONFIG_FILE = "email_config.json"  # create this in same folder as app.py

st.set_page_config(page_title="Blood Donation System", page_icon="🩸", layout="wide")
st.markdown("<h1 style='text-align:center; margin-bottom: 8px;'>🩸 Blood Donation & Emergency Help System</h1>", unsafe_allow_html=True)
st.markdown("---")

# ---------- DB Helpers & Schema ----------
def get_conn():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def ensure_schema():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Donor (
        DonorID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Gender TEXT,
        DOB TEXT,
        BloodGroup TEXT NOT NULL,
        Phone TEXT,
        Email TEXT,
        Latitude REAL,
        Longitude REAL,
        City TEXT,
        LastDonationDate TEXT
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS BloodBank (
        BankID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Address TEXT,
        Phone TEXT,
        Latitude REAL,
        Longitude REAL,
        City TEXT
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Inventory (
        InventoryID INTEGER PRIMARY KEY AUTOINCREMENT,
        BankID INTEGER NOT NULL,
        BloodGroup TEXT NOT NULL,
        UnitsAvailable INTEGER DEFAULT 0,
        LastUpdated TEXT,
        FOREIGN KEY (BankID) REFERENCES BloodBank(BankID) ON DELETE CASCADE
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Donation (
        DonationID INTEGER PRIMARY KEY AUTOINCREMENT,
        DonorID INTEGER NOT NULL,
        BankID INTEGER,
        Date TEXT NOT NULL,
        Units INTEGER NOT NULL,
        Hemoglobin REAL,
        FOREIGN KEY (DonorID) REFERENCES Donor(DonorID) ON DELETE CASCADE,
        FOREIGN KEY (BankID) REFERENCES BloodBank(BankID) ON DELETE SET NULL
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Request (
        RequestID INTEGER PRIMARY KEY AUTOINCREMENT,
        PatientName TEXT,
        RequiredBloodGroup TEXT NOT NULL,
        UnitsRequired INTEGER NOT NULL,
        City TEXT,
        Email TEXT,
        Latitude REAL,
        Longitude REAL,
        RequestDate TEXT NOT NULL,
        Status TEXT DEFAULT 'Pending',
        AssignedBankID INTEGER,
        AssignedDonorID INTEGER,
        FOREIGN KEY (AssignedBankID) REFERENCES BloodBank(BankID),
        FOREIGN KEY (AssignedDonorID) REFERENCES Donor(DonorID)
    );""")
    conn.commit()
    conn.close()
ensure_schema()

# ---------- Utility ----------
def run_write(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()

def fetch_all(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    return [dict(zip(cols, r)) for r in rows] if cols else []

def fetch_one(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    conn.close()
    return row

def iso(d):
    if isinstance(d, (date, datetime)):
        return d.isoformat()[:10]
    return str(d)

def valid_phone(p):
    return bool(re.match(r"^[0-9]{10}$", p))

def valid_email(e):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", e))

def days_since(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return (datetime.now() - dt).days
    except:
        return None

# ---------- Email sending ----------
def load_email_config():
    if not os.path.exists(EMAIL_CONFIG_FILE):
        return None
    with open(EMAIL_CONFIG_FILE, "r") as f:
        return json.load(f)

def send_email(recipient_email, subject, body):
    cfg = load_email_config()
    if SEND_EMAILS:
        if not cfg:
            return False, f"Missing {EMAIL_CONFIG_FILE}"
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            sender = cfg.get("email_address")
            msg["From"] = f"Blood Donation System <{sender}>"
            msg["To"] = recipient_email
            msg.set_content(body)
            host = cfg.get("email_host")
            port = cfg.get("email_port")
            password = cfg.get("email_password")
            use_tls = cfg.get("use_tls", True)
            if use_tls:
                server = smtplib.SMTP(host, port, timeout=10)
                server.starttls()
                server.login(sender, password)
                server.send_message(msg)
                server.quit()
            else:
                server = smtplib.SMTP_SSL(host, port, timeout=10)
                server.login(sender, password)
                server.send_message(msg)
                server.quit()
            return True, "Sent"
        except Exception as e:
            return False, str(e)
    else:
        return False, "Emails disabled (SEND_EMAILS=False)"

# ---------- OTP helpers ----------
def generate_otp():
    return f"{random.randint(0, 999999):06d}"

def set_otp_for(action_key, email):
    otp = generate_otp()
    expiry = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    st.session_state[action_key] = {"otp": otp, "expiry": expiry, "email": email}
    subject = "Blood Donation System — Your OTP"
    body = f"Your OTP for Blood Donation System is: {otp}\nThis code expires in {OTP_EXPIRY_MINUTES} minutes."
    ok, msg = send_email(email, subject, body)
    if ok:
        return True, "OTP sent to email"
    else:
        return False, f"Failed to send OTP: {msg}"

def verify_otp_for(action_key, code):
    info = st.session_state.get(action_key)
    if not info:
        return False, "No OTP requested for this action"
    if datetime.now() > info["expiry"]:
        st.session_state.pop(action_key, None)
        return False, "OTP expired"
    if code == info["otp"]:
        st.session_state.pop(action_key, None)
        return True, "OTP verified"
    return False, "Incorrect OTP"

# ---------- Dashboard ----------
def dashboard_view():
    st.header("Dashboard")
    total_donors = fetch_one("SELECT COUNT(*) FROM Donor;")[0]
    total_banks = fetch_one("SELECT COUNT(*) FROM BloodBank;")[0]
    units_row = fetch_one("SELECT SUM(UnitsAvailable) FROM Inventory;")
    total_units = units_row[0] if units_row and units_row[0] else 0
    pending_requests = fetch_one("SELECT COUNT(*) FROM Request WHERE Status='Pending';")[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Donors", total_donors)
    c2.metric("Total Blood Banks", total_banks)
    c3.metric("Total Units Available", total_units)
    c4.metric("Pending Requests", pending_requests)
    st.markdown("---")
    low = fetch_all("SELECT BloodBank.Name AS Bank, Inventory.BloodGroup, Inventory.UnitsAvailable FROM Inventory JOIN BloodBank ON Inventory.BankID=BloodBank.BankID WHERE Inventory.UnitsAvailable < ? ORDER BY Inventory.UnitsAvailable ASC", (LOW_INVENTORY_THRESHOLD,))
    if low:
        st.error("🔴 Low inventory items (units < {})".format(LOW_INVENTORY_THRESHOLD))
        st.table(low)
    else:
        st.success("No low inventory alerts.")
    donors = fetch_all("SELECT DonorID, Name, LastDonationDate FROM Donor")
    inactive = []
    for d in donors:
        ld = d.get('LastDonationDate')
        ds = days_since(ld) if ld else None
        if ds is None or ds > INACTIVE_DAYS:
            inactive.append({"DonorID": d['DonorID'], "Name": d['Name'], "LastDonationDate": ld, "DaysSince": ds})
    if inactive:
        st.warning(f"Donors inactive > {INACTIVE_DAYS} days (or never donated):")
        st.table(inactive)
    else:
        st.info("All donors active recently.")

# ---------- Donors CRUD with OTP on registration ----------
def donors_view():
    st.header("Donors — Add / Edit / Delete / Search")
    # Filters
    with st.expander("Search / Filter"):
        name_q = st.text_input("Name contains")
        city_list = [r['City'] for r in fetch_all("SELECT DISTINCT City FROM Donor WHERE City IS NOT NULL")]
        city_q = st.selectbox("City", ["All"] + city_list)
        bg_q = st.selectbox("Blood Group", ["All","A+","A-","B+","B-","O+","O-","AB+","AB-"])
    # Build query
    q = "SELECT * FROM Donor"
    conds = []; params = []
    if name_q:
        conds.append("Name LIKE ?"); params.append(f"%{name_q}%")
    if city_q and city_q != "All":
        conds.append("City = ?"); params.append(city_q)
    if bg_q and bg_q != "All":
        conds.append("BloodGroup = ?"); params.append(bg_q)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    donors = fetch_all(q, tuple(params))
    st.write(f"{len(donors)} donors found")
    coords = []
    for d in donors:
        if d.get('Latitude') is not None and d.get('Longitude') is not None:
            coords.append({"lat": d['Latitude'], "lon": d['Longitude']})
    if coords:
        st.map(coords)

    st.markdown("### Add new donor / Edit existing")
    opts = ["Add New"] + [f"{d['DonorID']} - {d['Name']}" for d in donors]
    sel = st.selectbox("Select", opts)
    if sel != "Add New":
        donor_id = int(sel.split(" - ")[0])
        r = fetch_one("SELECT * FROM Donor WHERE DonorID = ?", (donor_id,))
        _, name, gender, dob, blood, phone, email, lat, lon, city, lastdon = r
    else:
        donor_id = None
        name = gender = blood = phone = email = city = ""
        dob = lastdon = date.today()
        lat = lon = 0.0

    # prepare safe defaults
    if isinstance(dob, str):
        try:
            dob_parsed = datetime.strptime(dob, "%Y-%m-%d").date()
        except:
            dob_parsed = date(1990,1,1)
    else:
        dob_parsed = dob
    if dob_parsed < date(1950,1,1) or dob_parsed > date(2007,12,31):
        dob_parsed = date(1990,1,1)
    if isinstance(lastdon, str):
        try:
            lastdon_parsed = datetime.strptime(lastdon, "%Y-%m-%d").date()
        except:
            lastdon_parsed = date.today()
    else:
        lastdon_parsed = lastdon

    # --- OTP controls (OUTSIDE form) ---
    # Show OTP controls only when adding a new donor
    st.markdown("**Email verification (donor)**")
    # keep donor_otp_email in session so it persists
    if "donor_otp_email" not in st.session_state:
        st.session_state["donor_otp_email"] = email or ""
    st.session_state["donor_otp_email"] = st.text_input("Email to receive OTP (donor) — required for NEW donors", value=st.session_state["donor_otp_email"], key="donor_otp_email_global")
    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Send OTP to donor email", key="send_donor_otp"):
            e = st.session_state["donor_otp_email"].strip()
            if not valid_email(e):
                st.error("Enter a valid email for OTP")
            else:
                ok, msg = set_otp_for("donor_reg_otp", e)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
    with col2:
        donor_otp_entered = st.text_input("Enter OTP received (donor)", value="", key="donor_otp_enter")
        if st.button("Verify donor OTP", key="verify_donor_otp"):
            e = st.session_state.get("donor_otp_email", "").strip()
            if not e:
                st.error("Provide email first")
            else:
                ok, msg = verify_otp_for("donor_reg_otp", donor_otp_entered.strip())
                if ok:
                    # mark verified for this email
                    st.session_state["donor_reg_verified_email"] = e
                    st.success("OTP verified for " + e)
                else:
                    st.error(msg)

    # --- FORM: donor details (must NOT contain st.button) ---
    with st.form("donor_form"):
        name = st.text_input("Full Name *", value=name)
        gender = st.selectbox("Gender", ["M","F","Other"], index=["M","F","Other"].index(gender) if gender in ["M","F","Other"] else 0)
        dob = st.date_input("DOB *", value=dob_parsed, min_value=date(1950,1,1), max_value=date(2007,12,31))
        blood = st.selectbox("Blood Group *", ["A+","A-","B+","B-","O+","O-","AB+","AB-"], index=["A+","A-","B+","B-","O+","O-","AB+","AB-"].index(blood) if blood in ["A+","A-","B+","B-","O+","O-","AB+","AB-"] else 0)
        phone = st.text_input("Phone *", value=phone)
        email = st.text_input("Email *", value=st.session_state.get("donor_otp_email", email or ""))
        city = st.text_input("City *", value=city)
        lat = st.number_input("Latitude", value=lat if lat else 0.0, format="%.6f")
        lon = st.number_input("Longitude", value=lon if lon else 0.0, format="%.6f")
        lastdon = st.date_input("Last Donation Date", value=lastdon_parsed, min_value=date(1950,1,1), max_value=date.today())
        submitted = st.form_submit_button("Save Donor")

    if submitted:
        # if inserting new donor, OTP required
        if donor_id is None:
            verified_email = st.session_state.get("donor_reg_verified_email")
            if not verified_email or verified_email != st.session_state.get("donor_otp_email", "").strip():
                st.error("To add a new donor, you must verify the email with OTP. Send & verify OTP first.")
                st.stop()
        # validate fields
        if not name or not phone or not city:
            st.error("Please fill required fields")
        elif not valid_phone(phone):
            st.error("Phone must be 10 digits")
        elif not valid_email(email):
            st.error("Invalid email")
        else:
            dob_s = iso(dob)
            lastdon_s = iso(lastdon)
            if donor_id:
                run_write("""UPDATE Donor SET Name=?, Gender=?, DOB=?, BloodGroup=?, Phone=?, Email=?, Latitude=?, Longitude=?, City=?, LastDonationDate=? WHERE DonorID=?""",
                          (name, gender, dob_s, blood, phone, email, lat, lon, city, lastdon_s, donor_id))
                st.success("Donor updated")
            else:
                run_write("""INSERT INTO Donor (Name, Gender, DOB, BloodGroup, Phone, Email, Latitude, Longitude, City, LastDonationDate) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                          (name, gender, dob_s, blood, phone, email, lat, lon, city, lastdon_s))
                st.success("Donor added")
                # clean verified flag to avoid reuse
                if "donor_reg_verified_email" in st.session_state:
                    st.session_state.pop("donor_reg_verified_email", None)

    # delete donor (outside any form)
    st.markdown("#### Delete Donor (dangerous)")
    delid = st.number_input("DonorID to delete (0 skip)", min_value=0, step=1, key="del_donor")
    pin = st.text_input("Admin PIN", type="password", key="del_donor_pin")
    if st.button("Delete Donor", key="delete_donor_btn"):
        if delid > 0 and pin == ADMIN_PIN:
            run_write("DELETE FROM Donor WHERE DonorID = ?", (delid,))
            st.success(f"Deleted donor {delid}")
        else:
            st.error("Invalid ID or PIN")

# ---------- Banks CRUD ----------
def banks_view():
    st.header("Blood Banks — Add / Edit / Delete")
    banks = fetch_all("SELECT * FROM BloodBank")
    st.write(f"{len(banks)} banks")
    coords = []
    for b in banks:
        if b.get('Latitude') is not None and b.get('Longitude') is not None:
            coords.append({"lat": b['Latitude'], "lon": b['Longitude']})
    if coords:
        st.map(coords)
    st.markdown("### Add / Edit Bank")
    opts = ["Add New"] + [f"{b['BankID']} - {b['Name']}" for b in banks]
    sel = st.selectbox("Select bank", opts)
    if sel != "Add New":
        bid = int(sel.split(" - ")[0])
        r = fetch_one("SELECT * FROM BloodBank WHERE BankID = ?", (bid,))
        _, name, address, phone, lat, lon, city = r
    else:
        bid = None
        name = address = phone = city = ""
        lat = lon = 0.0
    with st.form("bank_form"):
        name = st.text_input("Name *", value=name)
        address = st.text_input("Address *", value=address)
        phone = st.text_input("Phone *", value=phone)
        city = st.text_input("City *", value=city)
        lat = st.number_input("Latitude", value=lat if lat else 0.0, format="%.6f")
        lon = st.number_input("Longitude", value=lon if lon else 0.0, format="%.6f")
        s = st.form_submit_button("Save")
    if s:
        if not name or not address or not phone or not city:
            st.error("Please fill required fields")
        else:
            if bid:
                run_write("UPDATE BloodBank SET Name=?, Address=?, Phone=?, Latitude=?, Longitude=?, City=? WHERE BankID=?",
                          (name, address, phone, lat, lon, city, bid))
                st.success("Bank updated")
            else:
                run_write("INSERT INTO BloodBank (Name, Address, Phone, Latitude, Longitude, City) VALUES (?,?,?,?,?,?)",
                          (name, address, phone, lat, lon, city))
                st.success("Bank added")
    st.markdown("#### Delete Bank (dangerous)")
    delid = st.number_input("BankID to delete (0 skip)", min_value=0, step=1, key="del_bank")
    pin = st.text_input("Admin PIN", type="password", key="del_bank_pin")
    if st.button("Delete Bank", key="delete_bank_btn"):
        if delid > 0 and pin == ADMIN_PIN:
            run_write("DELETE FROM BloodBank WHERE BankID = ?", (delid,))
            st.success(f"Deleted bank {delid}")
        else:
            st.error("Invalid ID or PIN")

# ---------- Donations CRUD / Inventory update ----------
def donations_view():
    st.header("Donations — Log / Delete / Recent")
    donors = fetch_all("SELECT DonorID, Name FROM Donor ORDER BY Name")
    banks = fetch_all("SELECT BankID, Name FROM BloodBank ORDER BY Name")
    if not donors or not banks:
        st.info("Add donors and banks first")
        return
    donor_opts = [f"{d['DonorID']} - {d['Name']}" for d in donors]
    bank_opts = [f"{b['BankID']} - {b['Name']}" for b in banks]
    with st.form("don_form"):
        donor_sel = st.selectbox("Donor *", donor_opts)
        bank_sel = st.selectbox("Bank *", bank_opts)
        ddate = st.date_input("Date *", value=date.today())
        units = st.number_input("Units (1-5)", min_value=1, max_value=5, value=1)
        hb = st.number_input("Hemoglobin", min_value=0.0, max_value=20.0, value=13.0)
        sub = st.form_submit_button("Log Donation")
    if sub:
        did = int(donor_sel.split(" - ")[0]); bid = int(bank_sel.split(" - ")[0])
        dstr = iso(ddate)
        run_write("INSERT INTO Donation (DonorID,BankID,Date,Units,Hemoglobin) VALUES (?,?,?,?,?)", (did,bid,dstr,units,hb))
        run_write("UPDATE Donor SET LastDonationDate = ? WHERE DonorID = ?", (dstr, did))
        bg = fetch_one("SELECT BloodGroup FROM Donor WHERE DonorID = ?", (did,))[0]
        row = fetch_one("SELECT UnitsAvailable FROM Inventory WHERE BankID = ? AND BloodGroup = ?", (bid, bg))
        if row:
            run_write("UPDATE Inventory SET UnitsAvailable = UnitsAvailable + ?, LastUpdated = ? WHERE BankID = ? AND BloodGroup = ?", (units, dstr, bid, bg))
        else:
            run_write("INSERT INTO Inventory (BankID,BloodGroup,UnitsAvailable,LastUpdated) VALUES (?,?,?,?)", (bid, bg, units, dstr))
        st.success("Donation logged and inventory updated.")
    st.markdown("### Recent Donations")
    rec = fetch_all("""SELECT D.DonationID, Donor.Name AS Donor, BloodBank.Name AS Bank, D.Date, D.Units, D.Hemoglobin
                       FROM Donation D JOIN Donor ON D.DonorID = Donor.DonorID JOIN BloodBank ON D.BankID = BloodBank.BankID
                       ORDER BY D.DonationID DESC LIMIT 10""")
    if rec:
        st.table(rec)
    else:
        st.info("No donations yet")
    st.markdown("#### Delete Donation (if wrong entry)")
    delid = st.number_input("DonationID to delete (0 skip)", min_value=0, step=1, key="del_d")
    pin = st.text_input("Admin PIN", type="password", key="del_d_pin")
    if st.button("Delete Donation", key="delete_donation_btn"):
        if delid > 0 and pin == ADMIN_PIN:
            run_write("DELETE FROM Donation WHERE DonationID = ?", (delid,))
            st.success("Donation deleted (inventory NOT auto-corrected).")
        else:
            st.error("Invalid ID or PIN")

# ---------- Requests (create / assign / fulfill) with OTP ----------
def requests_view():
    st.header("Requests — Create / Assign / Fulfill")
    # Request creation OTP controls OUTSIDE the form
    st.markdown("**Email verification for request creation**")
    if "req_otp_email" not in st.session_state:
        st.session_state["req_otp_email"] = ""
    st.session_state["req_otp_email"] = st.text_input("Email to receive OTP (request)", value=st.session_state["req_otp_email"], key="req_otp_email_global")
    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Send OTP to request email", key="send_req_otp"):
            e = st.session_state["req_otp_email"].strip()
            if not valid_email(e):
                st.error("Enter a valid email for OTP")
            else:
                ok, msg = set_otp_for("req_reg_otp", e)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
    with col2:
        req_otp_entered = st.text_input("Enter OTP received (request)", value="", key="req_otp_enter")
        if st.button("Verify request OTP", key="verify_req_otp"):
            e = st.session_state.get("req_otp_email", "").strip()
            if not e:
                st.error("Provide email first")
            else:
                ok, msg = verify_otp_for("req_reg_otp", req_otp_entered.strip())
                if ok:
                    st.session_state["req_reg_verified_email"] = e
                    st.success("OTP verified for " + e)
                else:
                    st.error(msg)

    # Form for creating request
    with st.form("req_form"):
        patient = st.text_input("Patient Name *")
        req_bg = st.selectbox("Required Blood Group *", ["A+","A-","B+","B-","O+","O-","AB+","AB-"])
        units = st.number_input("Units required", min_value=1, max_value=10, value=1)
        city = st.text_input("City *")
        email = st.text_input("Contact Email *", value=st.session_state.get("req_otp_email", ""))
        lat = st.number_input("Latitude", format="%.6f")
        lon = st.number_input("Longitude", format="%.6f")
        rdate = st.date_input("Request Date", value=date.today())
        s = st.form_submit_button("Create Request")
    if s:
        # require OTP verification for request creation
        verified = st.session_state.get("req_reg_verified_email")
        if not verified or verified != st.session_state.get("req_otp_email", "").strip():
            st.error("To create a request, you must verify the email with OTP. Send & verify OTP first.")
            st.stop()
        run_write("INSERT INTO Request (PatientName, RequiredBloodGroup, UnitsRequired, City, Email, Latitude, Longitude, RequestDate) VALUES (?,?,?,?,?,?,?,?)",
                  (patient, req_bg, units, city, st.session_state.get("req_otp_email","").strip(), lat, lon, iso(rdate)))
        st.success("Request created")
        if "req_reg_verified_email" in st.session_state:
            st.session_state.pop("req_reg_verified_email", None)

    st.markdown("### Pending Requests (suggestions shown)")
    pending = fetch_all("SELECT * FROM Request WHERE Status='Pending' ORDER BY RequestDate DESC")
    if not pending:
        st.info("No pending requests")
    else:
        for r in pending:
            st.write(f"Request {r['RequestID']}: {r['PatientName']} — {r['RequiredBloodGroup']} x {r['UnitsRequired']} ({r['City']})")
            banks = fetch_all("""SELECT Inventory.BankID, BloodBank.Name, Inventory.UnitsAvailable, BloodBank.Latitude, BloodBank.Longitude
                                 FROM Inventory JOIN BloodBank ON Inventory.BankID = BloodBank.BankID
                                 WHERE Inventory.BloodGroup = ? AND Inventory.UnitsAvailable >= ?""", (r['RequiredBloodGroup'], r['UnitsRequired']))
            if banks:
                for b in banks:
                    b['dist2'] = (b['Latitude'] - r['Latitude'])**2 + (b['Longitude'] - r['Longitude'])**2
                banks_sorted = sorted(banks, key=lambda x: x['dist2'])
                nearest = banks_sorted[0]
                st.success(f"Suggested Bank: {nearest['Name']} — UnitsAvailable: {nearest['UnitsAvailable']}")
                if st.button(f"Assign Bank {nearest['BankID']} to Req {r['RequestID']}", key=f"assignb_{r['RequestID']}"):
                    run_write("UPDATE Request SET AssignedBankID=?, Status='Assigned' WHERE RequestID = ?", (nearest['BankID'], r['RequestID']))
                    run_write("UPDATE Inventory SET UnitsAvailable = UnitsAvailable - ? WHERE BankID = ? AND BloodGroup = ?", (r['UnitsRequired'], nearest['BankID'], r['RequiredBloodGroup']))
                    st.success("Assigned and inventory decremented")
            else:
                st.warning("No bank with sufficient units. Showing nearest donors.")
                donors = fetch_all("SELECT DonorID, Name, Latitude, Longitude, Phone FROM Donor WHERE BloodGroup = ?", (r['RequiredBloodGroup'],))
                if donors:
                    for d in donors:
                        d['dist2'] = (d['Latitude'] - r['Latitude'])**2 + (d['Longitude'] - r['Longitude'])**2
                    nearest = sorted(donors, key=lambda x: x['dist2'])[0]
                    st.info(f"Suggested Donor: {nearest['Name']} — Phone: {nearest.get('Phone')}")
                    if st.button(f"Assign Donor {nearest['DonorID']} to Req {r['RequestID']}", key=f"assignd_{r['RequestID']}"):
                        run_write("UPDATE Request SET AssignedDonorID=?, Status='Assigned' WHERE RequestID = ?", (nearest['DonorID'], r['RequestID']))
                        st.success("Donor assigned")
            st.markdown("---")
    st.markdown("### All Requests (recent)")
    allr = fetch_all("SELECT * FROM Request ORDER BY RequestDate DESC LIMIT 20")
    st.table(allr)
    st.markdown("#### Mark Request Fulfilled")
    rid = st.number_input("RequestID to mark fulfilled (0 skip)", min_value=0, step=1, key="fulfill_req")
    if st.button("Mark Fulfilled", key="mark_fulfilled_btn"):
        if rid > 0:
            run_write("UPDATE Request SET Status='Fulfilled' WHERE RequestID = ?", (rid,))
            st.success("Request marked fulfilled")
        else:
            st.error("Enter a valid RequestID")
    st.markdown("#### Delete Request (dangerous)")
    delid = st.number_input("RequestID to delete (0 skip)", min_value=0, step=1, key="del_req")
    pin = st.text_input("Admin PIN", type="password", key="del_req_pin")
    if st.button("Delete Request", key="delete_request_btn"):
        if delid > 0 and pin == ADMIN_PIN:
            run_write("DELETE FROM Request WHERE RequestID = ?", (delid,))
            st.success("Request deleted")
        else:
            st.error("Invalid ID or PIN")

# ---------- Inventory & Exports ----------
def inventory_and_export_view():
    st.header("Inventory & Exports")
    inv = fetch_all("""SELECT Inventory.InventoryID, BloodBank.Name AS Bank, Inventory.BloodGroup, Inventory.UnitsAvailable, Inventory.LastUpdated
                       FROM Inventory JOIN BloodBank ON Inventory.BankID = BloodBank.BankID ORDER BY Inventory.UnitsAvailable ASC""")
    if inv:
        st.table(inv)
    else:
        st.info("No inventory records")
    st.markdown("---")
    st.subheader("Download / Backup")
    if os.path.exists(DB):
        with open(DB, "rb") as f:
            data = f.read()
        st.download_button("Download database file (.sqlite)", data=data, file_name=DB, mime="application/octet-stream")
    tlist = [r['name'] for r in fetch_all("SELECT name FROM sqlite_master WHERE type='table'")]
    sel = st.selectbox("Export table to CSV", [""] + tlist)
    if sel:
        rows = fetch_all(f"SELECT * FROM {sel}")
        if rows:
            header = ",".join(rows[0].keys())
            lines = [header]
            for r in rows:
                lines.append(",".join(str(r[k]) if r[k] is not None else "" for k in r.keys()))
            csv = "\n".join(lines).encode()
            st.download_button(f"Download {sel}.csv", data=csv, file_name=f"{sel}.csv", mime="text/csv")
        else:
            st.info("No data to export for this table")

# ---------- Simple admin: reset ----------
def admin_view():
    st.header("Admin")
    st.markdown("Reset DB (drops all tables). Use only if you want to recreate schema and sample data.)")
    pin = st.text_input("Admin PIN", type="password")
    if st.button("Reset DB (drop tables)", key="reset_db_btn"):
        if pin == ADMIN_PIN:
            for t in ["Request","Donation","Inventory","BloodBank","Donor"]:
                run_write(f"DROP TABLE IF EXISTS {t}")
            ensure_schema()
            st.success("Dropped and re-created schema. (No sample data added.)")
        else:
            st.error("Wrong PIN")

# ---------- App Navigation ----------
menu = ["Dashboard","Donors","Banks","Donations","Requests","Inventory/Export","Admin"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Dashboard":
    dashboard_view()
elif choice == "Donors":
    donors_view()
elif choice == "Banks":
    banks_view()
elif choice == "Donations":
    donations_view()
elif choice == "Requests":
    requests_view()
elif choice == "Inventory/Export":
    inventory_and_export_view()
elif choice == "Admin":
    admin_view()

# ---------- Quick note ----------
if SEND_EMAILS and not os.path.exists(EMAIL_CONFIG_FILE):
    st.sidebar.error(f"Email enabled but {EMAIL_CONFIG_FILE} not found. Create it or set SEND_EMAILS=False.")
st.sidebar.markdown("---")
st.sidebar.caption(f"Backup of previous file (if needed): /mnt/data/111c5e1c-cceb-440b-bbcc-d857acbc0658.py")
