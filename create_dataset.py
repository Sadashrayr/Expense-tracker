import csv
import random
from datetime import datetime, timedelta

# Set parameters
num_records = 100
start_date = datetime(2024, 1, 1)
end_date = datetime(2025, 3, 31)

# Generate random dates
date_range = (end_date - start_date).days
random_days = [random.randint(0, date_range) for _ in range(num_records)]
random_days.sort()  # Sort days for chronological order
dates = [start_date + timedelta(days=day) for day in random_days]
dates_formatted = [date.strftime('%Y-%m-%d') for date in dates]

# Define expense categories and their typical amount ranges
expense_categories = {
    "Groceries": (20, 200),
    "Dining Out": (15, 150),
    "Utilities": (50, 300),
    "Rent/Mortgage": (800, 2500),
    "Transportation": (10, 100),
    "Entertainment": (15, 120),
    "Healthcare": (20, 500),
    "Shopping": (25, 400),
    "Travel": (100, 1500),
    "Education": (50, 800),
    "Subscriptions": (5, 50),
    "Insurance": (40, 500),
    "Home Maintenance": (50, 600),
    "Gifts": (20, 200),
    "Miscellaneous": (10, 150)
}

# Generate descriptions and amounts
descriptions = []
amounts = []

for _ in range(num_records):
    category = random.choice(list(expense_categories.keys()))
    min_amount, max_amount = expense_categories[category]
    
    # Generate a more specific description
    specifics = {
        "Groceries": ["Supermarket", "Farmer's Market", "Convenience Store", "Bulk Food Store"],
        "Dining Out": ["Restaurant", "Café", "Fast Food", "Food Delivery"],
        "Utilities": ["Electricity Bill", "Water Bill", "Gas Bill", "Internet Bill", "Phone Bill"],
        "Rent/Mortgage": ["Monthly Rent", "Mortgage Payment", "Housing Fee"],
        "Transportation": ["Fuel", "Public Transit", "Taxi/Uber", "Car Maintenance"],
        "Entertainment": ["Movie Tickets", "Concert", "Sports Event", "Streaming Service"],
        "Healthcare": ["Doctor Visit", "Prescription", "Dental Care", "Eye Care"],
        "Shopping": ["Clothing", "Electronics", "Home Goods", "Books"],
        "Travel": ["Flight Tickets", "Hotel Stay", "Car Rental", "Vacation Package"],
        "Education": ["Tuition", "Books", "Online Course", "School Supplies"],
        "Subscriptions": ["Digital Service", "Magazine", "Software License", "Membership Fee"],
        "Insurance": ["Health Insurance", "Car Insurance", "Home Insurance", "Life Insurance"],
        "Home Maintenance": ["Repairs", "Cleaning Service", "Gardening", "Furniture"],
        "Gifts": ["Birthday Present", "Holiday Gift", "Anniversary Gift", "Charity Donation"],
        "Miscellaneous": ["Office Supplies", "Pet Supplies", "Hobby Supplies", "Unexpected Expense"]
    }
    
    specific = random.choice(specifics[category])
    description = f"{category} - {specific}"
    
    # Generate amount with some decimal precision
    amount = round(random.uniform(min_amount, max_amount), 2)
    
    descriptions.append(description)
    amounts.append(amount)

# Create and write to CSV
with open('Expense_dataset.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    # Write header
    writer.writerow(['Date', 'Amount', 'Description'])
    # Write data
    for i in range(num_records):
        writer.writerow([dates_formatted[i], amounts[i], descriptions[i]])

print("Expense dataset successfully created and saved as 'Expense_dataset.csv'")
print(f"Generated {num_records} records from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print("\nFirst 5 rows of the dataset:")
for i in range(min(5, num_records)):
    print(f"{dates_formatted[i]}, ${amounts[i]:.2f}, {descriptions[i]}")