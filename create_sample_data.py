import pandas as pd
import random

# Generate sample data
students = []
subjects = ["Math", "Physics", "Chemistry", "Biology", "Literature", "History"]

for i in range(1, 51):
    student = {
        "Student ID": f"SV{i:03d}",
        "Name": f"Student {i}",
    }
    
    # Randomly assign 3-5 subjects
    num_subs = random.randint(3, 5)
    chosen_subs = random.sample(subjects, num_subs)
    
    for sub in subjects:
        if sub in chosen_subs:
            student[sub] = 90 # 90 minutes duration
        else:
            student[sub] = None
            
    students.append(student)

df = pd.DataFrame(students)
df.to_excel("sample_data.xlsx", index=False)
print("Created sample_data.xlsx")
