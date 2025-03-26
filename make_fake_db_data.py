import os
import csv
import random
import datetime
from faker import Faker

fake = Faker()

# Make sure the output directory exists
output_dir = "./table_csvs"
os.makedirs(output_dir, exist_ok=True)

##################################################
# 1) Define how many rows of data to generate per table
##################################################
NUM_HEADER_ROWS = 3
NUM_STUDENT_ROWS = 2000
NUM_ALTERNATE_IDS_ROWS = 500
NUM_DEMOGRAPHICS_ROWS = 2000
NUM_QUALIFYING_MOVES_ROWS = 1500
NUM_ENROLLMENTS_ROWS = 1000
NUM_COURSE_HISTORY_ROWS = 8000
NUM_ASSESSMENTS_ROWS = 7000

##################################################
# 2) Utility Generators
##################################################

def random_date_yyyymmdd(start_year=1990, end_year=2025):
    """Generate a random date in YYYYMMDD format."""
    start = datetime.date(start_year, 1, 1)
    end = datetime.date(end_year, 12, 31)
    delta = end - start
    random_days = random.randrange(delta.days)
    random_date = start + datetime.timedelta(days=random_days)
    return random_date.strftime("%Y%m%d")

def random_date_yymm(start_year=1990, end_year=2025):
    """Generate a random date in MMYYYY format (for Assessment Administration Date)."""
    # We only need month and year
    start = datetime.date(start_year, 1, 1)
    end = datetime.date(end_year, 12, 31)
    delta = end - start
    random_days = random.randrange(delta.days)
    random_date = start + datetime.timedelta(days=random_days)
    return random_date.strftime("%m%Y")

def random_timestamp_yyyymmddhhmmssSSS(start_year=2010, end_year=2025):
    """Generate a random timestamp in 'YYYYMMDDhhmmssSSS' format."""
    start = datetime.datetime(start_year, 1, 1)
    end = datetime.datetime(end_year, 12, 31, 23, 59, 59)
    delta = end - start
    random_seconds = random.randrange(int(delta.total_seconds()))
    random_dt = start + datetime.timedelta(seconds=random_seconds)
    # For microseconds, we only keep 3 digits to mimic 'SSS'
    ms = f"{int(random_dt.microsecond/1000):03d}"
    return random_dt.strftime(f"%Y%m%d%H%M%S") + ms

def random_state_code():
    """Return a random (valid) US state code (2 letters)."""
    states = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
              "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
              "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
              "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
              "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"]
    return random.choice(states)

def random_yes_no():
    return random.choice(["Yes", "No"])

def random_grade_level():
    valid_grades = [
        "P0","P1","P2","P3","P4","P5","PS","PX","KG",
        "01","02","03","04","05","06","07","08","09",
        "10","11","12","UG","00"
    ]
    return random.choice(valid_grades)

def random_assessment_type():
    # Subset from the specs
    valid_types = ["01","02","03","04","05","06","07","08","09","10","11"]
    return random.choice(valid_types)

def random_assessment_interpretation(assessment_type):
    # If it's 09,10,11, we use restricted values
    if assessment_type in ["09", "10", "11"]:
        restricted = [
            "Advanced","Proficient or Above","Proficient","Passed",
            "Failed","Not Proficient","Basic","Below Basic","Far Below Basic"
        ]
        return random.choice(restricted)
    else:
        # could be "Other" or something else
        return random.choice(["Other","Passed","Failed","Proficient"])

##################################################
# 3) Generate the sets of data for each table
#
#    We'll place them into lists of dicts,
#    then write them out to CSV.
##################################################

#######################
# 3a) Header Table
#######################
def generate_header_table_data(num_rows):
    """
    Let's create a trivial primary key named `header_id`.
    We'll produce several example rows with random data.
    """
    data = []
    for i in range(1, num_rows + 1):
        row = {
            "header_id": i,  # PK
            "Submitting State": random_state_code(),
            "Submission Date": random_timestamp_yyyymmddhhmmssSSS(),
            "Total Students in File": random.randint(1, 500),
            "Total Records in File": random.randint(1, 1000),
            "Beginning Effective Date": random_timestamp_yyyymmddhhmmssSSS(),
            "Ending Effective Date": random_timestamp_yyyymmddhhmmssSSS(),
        }
        # Make sure the End date is after the Beginning
        if row["Ending Effective Date"] < row["Beginning Effective Date"]:
            row["Ending Effective Date"], row["Beginning Effective Date"] = (
                row["Beginning Effective Date"],
                row["Ending Effective Date"],
            )
        data.append(row)
    return data

#######################
# 3b) Student Table
#######################
def generate_student_table_data(num_rows):
    """
    We'll produce:
      - A 'student_id' as PK (1 to num_rows).
      - 'Student Record ID' matches 'student_id' or any 7-digit within range.
      - MSIX Identification Number = 12-digit random number
      - ...
    """
    data = []
    for i in range(1, num_rows + 1):
        # 7-digit ID up to 40000
        stud_rec_id = str(i).zfill(7)  # "0000001" etc.
        # MSIX ID: 12-digit numeric
        msix_id = "".join([str(random.randint(0, 9)) for _ in range(12)])
        state_code = random_state_code()
        state_stu_id = "".join(random.choices("0123456789", k=random.randint(5, 15)))
        # State Student Identifier Type (2-digit code)
        ssi_type = random.choice(["01","02"])
        # Action Code: I / U / D
        action_code = random.choice(["I","U","D"])

        row = {
            "student_id": i,  # Our own PK for reference
            "Student Record ID": stud_rec_id,
            "MSIX Identification Number": msix_id,
            "Reporting State Code": state_code,
            "State Student Identifier": state_stu_id,
            "State Student Identifier Type": ssi_type,
            "Action Code": action_code
        }
        data.append(row)
    return data

#######################
# 3c) Alternate State Student IDs (K)
#######################
def generate_alternate_ids_table_data(num_rows, student_ids):
    """
    The PK here is 'alt_state_id_pk' (our own).
    We'll have a foreign key referencing 'student_id'.
    'Alternate State Record ID' is up to 3 digits (001 to 999).
    """
    data = []
    for i in range(1, num_rows + 1):
        alt_record_id = str(random.randint(1, 999)).zfill(3)
        row = {
            "alt_state_id_pk": i,  # PK
            "student_id_fk": random.choice(student_ids),  # FK
            "Alternate State Record ID": alt_record_id,
            "Alternate State Student ID": "".join(
                random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=random.randint(5, 15))
            ),
            "Alternate State Student ID Type": random.choice(["01","02","03"]),
        }
        data.append(row)
    return data

#######################
# 3d) Demographics (D)
#######################
def generate_demographics_table_data(num_rows, student_ids):
    """
    The PK is 'demographics_id'.  We have a 3-digit record ID from 001..999
    We'll reference a random student_id_fk
    """
    data = []
    for i in range(1, num_rows + 1):
        rec_id = str(random.randint(1, 999)).zfill(3)
        row = {
            "demographics_id": i,
            "student_id_fk": random.choice(student_ids),
            "Demographics Record ID": rec_id,
            "First Name": fake.first_name(),
            "Middle Name": fake.first_name() if random.random() < 0.6 else "",
            "Last Name 1": fake.last_name(),
            "Last Name 2": fake.last_name() if random.random() < 0.3 else "",
            "Suffix": random.choice(["Jr.","Sr.","III",""]) if random.random() < 0.2 else "",
            "Sex": random.choice(["Male","Female","Other"]),
            "Birth Date": random_date_yyyymmdd(start_year=1995, end_year=2020),
            "Multiple Birth Flag": random_yes_no(),
            "Birth Date Verification": random.choice(["1003","1004","1005","1009","1012","9999"]),
            "Male Parent First Name": fake.first_name_male() if random.random() < 0.7 else "",
            "Male Parent Last Name": fake.last_name() if random.random() < 0.7 else "",
            "Female Parent First Name": fake.first_name_female() if random.random() < 0.7 else "",
            "Female Parent Last Name": fake.last_name() if random.random() < 0.7 else "",
            "Parent 1 Email Address": fake.email() if random.random() < 0.5 else "",
            "Parent 2 Email Address": fake.email() if random.random() < 0.3 else "",
            "Parent 1 Phone Number": "".join(random.choices("0123456789", k=10)) if random.random() < 0.5 else "",
            "Parent 2 Phone Number": "".join(random.choices("0123456789", k=10)) if random.random() < 0.3 else "",
        }
        data.append(row)
    return data

#######################
# 3e) Qualifying Moves (Q)
#######################
def generate_qualifying_moves_table_data(num_rows, student_ids):
    data = []
    for i in range(1, num_rows + 1):
        rec_id = str(random.randint(1, 999)).zfill(3)
        from_city = fake.city()
        from_state = random_state_code()
        from_country = random.choice(["USA","MEX","CAN","GTM","SLV","HND","IND","BRA"])
        to_city = fake.city()
        to_state = random_state_code()
        qad = random_date_yyyymmdd(start_year=2015, end_year=2025)
        # eligibility expires ~3 years later, or random earlier
        eed_year = int(qad[:4]) + 3
        if eed_year > 2025:
            eed_year = 2025
        eed_fake = qad[:4]  # get the year part
        eed_dt_str = qad
        # Just do a simplistic approach:
        eed_dt_str = qad[:4] + qad[4:6] + qad[6:]
        # We can do a smaller random offset
        random_expiry = random.randint(0, 365*3)
        start_dt = datetime.datetime.strptime(qad, "%Y%m%d")
        exp_dt = start_dt + datetime.timedelta(days=random_expiry)
        eed_dt_str = exp_dt.strftime("%Y%m%d")

        row = {
            "qual_moves_id": i,
            "student_id_fk": random.choice(student_ids),
            "Qualifying Moves Record ID": rec_id,
            "Qualifying Arrival Date": qad,
            "Qualifying Move From City": from_city,
            "Qualifying Move From State": from_state,
            "Qualifying Move From Country": from_country,
            "Qualifying Move To City": to_city,
            "Qualifying Move To State": to_state,
            "Eligibility Expiration Date": eed_dt_str
        }
        data.append(row)
    return data

#######################
# 3f) Enrollments (E)
#######################
def generate_enrollments_table_data(num_rows, student_ids):
    data = []
    for i in range(1, num_rows + 1):
        rec_id = str(random.randint(1, 999)).zfill(3)
        enroll_date = random_date_yyyymmdd(start_year=2015, end_year=2025)
        # possible enrollment types
        enrollment_type = random.choice(["01","02","03","04","05","06","07"])
        mep_project_type = random.choice(["01","02",""])  # sometimes blank
        school_name = fake.company() + " School"
        # let's create random phone for the facility
        facility_phone = "".join(random.choices("0123456789", k=10))
        withdraw_date = random_date_yyyymmdd(start_year=int(enroll_date[:4]), end_year=2025)
        # Ensure withdrawal date >= enrollment date
        if withdraw_date < enroll_date:
            withdraw_date, enroll_date = enroll_date, withdraw_date

        row = {
            "enrollment_id": i,
            "student_id_fk": random.choice(student_ids),
            "Enrollments Record ID": rec_id,
            "Enrollment Date": enroll_date,
            "Enrollment Type": enrollment_type,
            "School or Project Name": school_name,
            "MEP Project Type": mep_project_type,
            "School Identification Code": "".join(random.choices("0123456789", k=12)),
            "Facility Name": fake.company() if random.random() < 0.5 else "",
            "Facility Address 1": fake.street_address(),
            "Facility Address 2": "",
            "Facility Address 3": "",
            "Facility City": fake.city(),
            "School District ID": "".join(random.choices("0123456789", k=7)),
            "School District": fake.company() + " District",
            "Facility State": random_state_code(),
            "Facility Zip": "".join(random.choices("0123456789", k=5)),
            "Telephone Number": facility_phone,
            "Grade Level": random_grade_level(),
            "LEP Indicator (EL)": random_yes_no(),
            "IEP Indicator": random_yes_no(),
            "Med Alert Indicator": random.choice(["Chronic","Acute","None"]),
            "PFS Flag": random_yes_no(),
            "Immunization Record Flag": random_yes_no(),
            "Withdrawal Date": withdraw_date,
            "District of Residence": "".join(random.choices("0123456789", k=7)),
            "Residency Date": random_date_yyyymmdd(start_year=int(enroll_date[:4]), end_year=2025),
            "Residency Verification Date": random_date_yyyymmdd(start_year=int(enroll_date[:4]), end_year=2025),
            "Designated Graduation School": "".join(random.choices("0123456789", k=12)) if random.random() < 0.3 else "",
            "Graduation/HSE Indicator": random.choice(["Graduation","HSE",""]) if random.random() < 0.3 else "",
            "Graduation/HSE Date": random_date_yyyymmdd() if random.random() < 0.2 else "",
            "Out of State Transcript Indicator": random_yes_no(),
            "Continuation of Services Reason": random.choice(["01","02","03",""]),
            "Algebra 1 or Equivalent Indicator": random_yes_no(),
            "Enrollment Comment": fake.sentence() if random.random() < 0.3 else ""
        }
        data.append(row)
    return data

#######################
# 3g) Course History (C)
#######################
def generate_course_history_table_data(num_rows, student_ids):
    data = []
    for i in range(1, num_rows + 1):
        rec_id = str(random.randint(1, 999)).zfill(3)
        begin_year = random.randint(2015, 2023)
        end_year = begin_year if random.random() < 0.7 else begin_year + 1

        row = {
            "course_history_id": i,
            "student_id_fk": random.choice(student_ids),
            "Course History Record ID": rec_id,
            "Course Title": random.choice(["Algebra I","Algebra II","English I","World History","Chemistry","Art I"]),
            "Subject Area Name": random.choice(["Mathematics","English","History","Science","Arts"]),
            "Course Type": random.choice(["01","02","03","04","05","07","08","09","00"]),
            "Begin Academic Year": begin_year,
            "End Academic Year": end_year,
            "Course Section": random.choice(["01","02","03"]),
            "Term Type": random.choice(["0827","0834","0835","0832","0830","0833","0828","0829","9999"]),
            "Clock Hours": random.randint(0, 180),
            "Grade-to-Date": str(random.randint(50,100)) if random.random() < 0.7 else random.choice(["A","B","C","D","F"]),
            "Credits Granted": round(random.uniform(0.25,1.5),2),
            "Final Grade": random.choice(["A","B","C","D","F","P","Incomplete"]) if random.random() < 0.5 else ""
        }
        data.append(row)
    return data

#######################
# 3h) Assessments (A)
#######################
def generate_assessments_table_data(num_rows, student_ids):
    data = []
    for i in range(1, num_rows + 1):
        rec_id = str(random.randint(1, 999)).zfill(3)
        assess_type = random_assessment_type()
        row = {
            "assessments_id": i,
            "student_id_fk": random.choice(student_ids),
            "Assessments Record ID": rec_id,
            "Assessment Title": random.choice([
                "State Reading Test",
                "State Math Test",
                "End-of-Course Exam",
                "English Proficiency Test"
            ]),
            "Assessment Content": random.choice(["Mathematics","Reading","Language Arts","Writing","Other"]),
            "Assessment Type": assess_type,
            "Assessment Administration Date": random_date_yymm(),
            "Assessment Reporting Method": random.choice([
                "0144","0490","0493","0499","0500","0503","0512","9999"
            ]),
            "Score Results": str(random.randint(200, 900)),
            "Assessment Interpretation": random_assessment_interpretation(assess_type)
        }
        data.append(row)
    return data

##################################################
# 4) Actually generate data and write CSV files
##################################################

def write_csv(filename, fieldnames, rows):
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def main():
    # Generate the data for each table in order that respects PK/FK references.

    # 1) Header
    header_data = generate_header_table_data(NUM_HEADER_ROWS)
    header_fields = list(header_data[0].keys()) if header_data else []
    write_csv(
        os.path.join(output_dir, "Header.csv"),
        header_fields,
        header_data
    )

    # 2) Student
    student_data = generate_student_table_data(NUM_STUDENT_ROWS)
    student_fields = list(student_data[0].keys()) if student_data else []
    write_csv(
        os.path.join(output_dir, "Student.csv"),
        student_fields,
        student_data
    )

    # Prepare a list of valid student_ids for foreign keys
    student_ids = [row["student_id"] for row in student_data]

    # 3) Alternate State Student IDs
    alt_ids_data = generate_alternate_ids_table_data(NUM_ALTERNATE_IDS_ROWS, student_ids)
    alt_ids_fields = list(alt_ids_data[0].keys()) if alt_ids_data else []
    write_csv(
        os.path.join(output_dir, "Alternate_State_Student_IDs.csv"),
        alt_ids_fields,
        alt_ids_data
    )

    # 4) Demographics
    demo_data = generate_demographics_table_data(NUM_DEMOGRAPHICS_ROWS, student_ids)
    demo_fields = list(demo_data[0].keys()) if demo_data else []
    write_csv(
        os.path.join(output_dir, "Demographics.csv"),
        demo_fields,
        demo_data
    )

    # 5) Qualifying Moves
    qual_moves_data = generate_qualifying_moves_table_data(NUM_QUALIFYING_MOVES_ROWS, student_ids)
    qual_moves_fields = list(qual_moves_data[0].keys()) if qual_moves_data else []
    write_csv(
        os.path.join(output_dir, "Qualifying_Moves.csv"),
        qual_moves_fields,
        qual_moves_data
    )

    # 6) Enrollments
    enroll_data = generate_enrollments_table_data(NUM_ENROLLMENTS_ROWS, student_ids)
    enroll_fields = list(enroll_data[0].keys()) if enroll_data else []
    write_csv(
        os.path.join(output_dir, "Enrollments.csv"),
        enroll_fields,
        enroll_data
    )

    # 7) Course History
    course_hist_data = generate_course_history_table_data(NUM_COURSE_HISTORY_ROWS, student_ids)
    course_hist_fields = list(course_hist_data[0].keys()) if course_hist_data else []
    write_csv(
        os.path.join(output_dir, "Course_History.csv"),
        course_hist_fields,
        course_hist_data
    )

    # 8) Assessments
    assess_data = generate_assessments_table_data(NUM_ASSESSMENTS_ROWS, student_ids)
    assess_fields = list(assess_data[0].keys()) if assess_data else []
    write_csv(
        os.path.join(output_dir, "Assessments.csv"),
        assess_fields,
        assess_data
    )

    print("Fake data CSVs generated in:", output_dir)

if __name__ == "__main__":
    main()
