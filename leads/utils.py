import re

# 1. Yahan apne hisaab se Employee Ranges define karein
EMPLOYEE_RANGES = [
    ('', 'All Sizes'),
    ('1-10', '1-10'),
    ('11-50', '11-50'),
    ('51-200', '51-200'),
    ('201-500', '201-500'),
    ('501-1000', '501-1,000'),
    ('1001-5000', '1,001-5,000'),
    ('5001-10000', '5,001-10,000'),
    ('10001+', '10,001+'),
]

def parse_employee_string(emp_str):
    """
    Database se "150", "100-500", "5000+", "1,000" jaise text ko
    (min, max) numbers mein badalta hai.
    """
    if not emp_str:
        return (None, None)
        
    emp_str = str(emp_str).strip().replace(',', '')
    
    # Range: "100-500"
    match = re.fullmatch(r'(\d+)\s*-\s*(\d+)', emp_str)
    if match:
        return (int(match.group(1)), int(match.group(2)))
        
    # Plus: "1000+"
    match = re.fullmatch(r'(\d+)\s*\+', emp_str)
    if match:
        return (int(match.group(1)), float('inf'))
        
    # Single number: "150"
    match = re.fullmatch(r'(\d+)', emp_str)
    if match:
        num = int(match.group(1))
        return (num, num)
        
    # Unknown format
    return (None, None)

def check_range_overlap(range_str, db_emp_str):
    """
    Check karta hai ki user ka selected range (e.g., '51-200')
    database ki value (e.g., '150' ya '100-500') se match karta hai ya nahi.
    """
    # 1. User ke selected filter range ko parse karo
    filter_min, filter_max = parse_employee_string(range_str)
    
    # 2. Database ki value ko parse karo
    db_min, db_max = parse_employee_string(db_emp_str)
    
    if filter_min is None or db_min is None:
        return False # Agar koi value parse nahi hui toh match nahi karega
        
    # 3. Overlap Logic:
    # Filter range [A, B]
    # DB range     [C, D]
    # Overlap tab hota hai jab A <= D aur B >= C
    return filter_min <= db_max and filter_max >= db_min