import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

class ExpenseTracker:
    def __init__(self):
        self.df = None
        self.categories = {
            'groceries': ['supermarket', 'grocery', 'food mart', 'market'],
            'dining': ['restaurant', 'cafe', 'coffee', 'dining', 'bar', 'pub'],
            'transportation': ['gas', 'fuel', 'uber', 'lyft', 'taxi', 'bus', 'train', 'transport', 'metro'],
            'utilities': ['electric', 'water', 'gas bill', 'internet', 'phone', 'utility'],
            'entertainment': ['movie', 'theater', 'concert', 'netflix', 'spotify', 'subscription'],
            'shopping': ['amazon', 'mall', 'retail', 'clothing', 'store', 'online purchase'],
            'healthcare': ['doctor', 'pharmacy', 'hospital', 'medical', 'dental', 'health'],
            'housing': ['rent', 'mortgage', 'lease', 'property'],
            'travel': ['hotel', 'flight', 'airbnb', 'vacation', 'travel'],
            'education': ['tuition', 'course', 'book', 'education', 'school'],
            'personal care': ['haircut', 'salon', 'spa', 'gym'],
            'miscellaneous': []
        }
    
    def load_data(self, file_path):
        """Load expense data from CSV file"""
        try:
            self.df = pd.read_csv(file_path)
            
            # Check if required columns exist
            required_cols = ['date', 'amount', 'description']
            missing_cols = [col for col in required_cols if col not in self.df.columns]
            
            if missing_cols:
                print(f"Error: Missing required columns: {', '.join(missing_cols)}")
                print(f"Available columns: {', '.join(self.df.columns)}")
                return False
            
            # Convert date to datetime
            self.df['date'] = pd.to_datetime(self.df['date'])
            
            # Ensure amount is numeric
            self.df['amount'] = pd.to_numeric(self.df['amount'], errors='coerce')
            
            # Add month and year columns for easier analysis
            self.df['month'] = self.df['date'].dt.month
            self.df['year'] = self.df['date'].dt.year
            
            print(f"Successfully loaded {len(self.df)} expense records")
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def categorize_expenses(self):
        """Categorize expenses based on description keywords"""
        if self.df is None:
            print("No data loaded. Please load data first.")
            return
        
        def assign_category(description):
            description = str(description).lower()
            for category, keywords in self.categories.items():
                for keyword in keywords:
                    if keyword in description:
                        return category
            return 'miscellaneous'
        
        self.df['category'] = self.df['description'].apply(assign_category)
        print("Expenses categorized successfully")
    
    def add_custom_category_rules(self, rules_dict):
        """Add custom categorization rules"""
        for category, keywords in rules_dict.items():
            if category in self.categories:
                self.categories[category].extend(keywords)
            else:
                self.categories[category] = keywords
        
        print(f"Added custom rules for categories: {', '.join(rules_dict.keys())}")
        
        # Re-categorize if data is already loaded
        if self.df is not None:
            self.categorize_expenses()
    
    def get_monthly_summary(self):
        """Generate monthly expense summary"""
        if self.df is None or 'category' not in self.df.columns:
            print("Data not loaded or expenses not categorized yet")
            return None
        
        monthly_summary = self.df.groupby(['year', 'month', 'category'])['amount'].sum().reset_index()
        return monthly_summary
    
    def get_category_summary(self):
        """Generate summary by category"""
        if self.df is None or 'category' not in self.df.columns:
            print("Data not loaded or expenses not categorized yet")
            return None
        
        category_summary = self.df.groupby('category')['amount'].agg(['sum', 'mean', 'count']).reset_index()
        category_summary = category_summary.sort_values('sum', ascending=False)
        return category_summary
    
    def plot_expenses_by_category(self):
        """Plot expenses by category"""
        if self.df is None or 'category' not in self.df.columns:
            print("Data not loaded or expenses not categorized yet")
            return
        
        plt.figure(figsize=(12, 6))
        category_totals = self.df.groupby('category')['amount'].sum().sort_values(ascending=False)
        category_totals.plot(kind='bar', color='skyblue')
        plt.title('Total Expenses by Category')
        plt.xlabel('Category')
        plt.ylabel('Amount')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('static/images/expenses_by_category.png')
        plt.close()
        print("Plot saved as 'expenses_by_category.png'")
    
    def plot_monthly_trend(self):
        """Plot monthly expense trend"""
        if self.df is None:
            print("No data loaded. Please load data first.")
            return
        
        plt.figure(figsize=(12, 6))
        monthly_data = self.df.groupby(['year', 'month'])['amount'].sum().reset_index()
        monthly_data['date'] = monthly_data.apply(lambda x: datetime(int(x['year']), int(x['month']), 1), axis=1)
        monthly_data = monthly_data.sort_values('date')
        
        plt.plot(monthly_data['date'], monthly_data['amount'], marker='o', linestyle='-')
        plt.title('Monthly Expense Trend')
        plt.xlabel('Month')
        plt.ylabel('Total Expenses')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('static/images/monthly_expense_trend.png')
        plt.close()
        print("Plot saved as 'monthly_expense_trend.png'")
    
    def identify_unusual_expenses(self, threshold_factor=2.0):
        """Identify unusually large expenses"""
        if self.df is None or 'category' not in self.df.columns:
            print("Data not loaded or expenses not categorized yet")
            return None
        
        # Calculate average expense amount by category
        category_avg = self.df.groupby('category')['amount'].mean()
        
        # Find expenses that exceed the category average by the threshold factor
        unusual_expenses = []
        for _, row in self.df.iterrows():
            category = row['category']
            amount = row['amount']
            avg = category_avg[category]
            
            if amount > avg * threshold_factor:
                unusual_expenses.append({
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'description': row['description'],
                    'amount': amount,
                    'category': category,
                    'category_avg': avg,
                    'times_above_avg': amount / avg
                })
        
        unusual_df = pd.DataFrame(unusual_expenses)
        if len(unusual_df) > 0:
            unusual_df = unusual_df.sort_values('times_above_avg', ascending=False)
        
        return unusual_df
    
    def generate_report(self, output_file='expense_report.txt'):
        """Generate a comprehensive expense report"""
        if self.df is None or 'category' not in self.df.columns:
            print("Data not loaded or expenses not categorized yet")
            return
        
        with open(output_file, 'w') as f:
            f.write("===== EXPENSE ANALYSIS REPORT =====\n\n")
            
            # Overall summary
            f.write("OVERALL SUMMARY:\n")
            f.write(f"Total Records: {len(self.df)}\n")
            f.write(f"Date Range: {self.df['date'].min().strftime('%Y-%m-%d')} to {self.df['date'].max().strftime('%Y-%m-%d')}\n")
            f.write(f"Total Expenses: ${self.df['amount'].sum():.2f}\n")
            f.write(f"Average Monthly Expenses: ${self.df.groupby(['year', 'month'])['amount'].sum().mean():.2f}\n\n")
            
            # Category summary
            f.write("CATEGORY SUMMARY:\n")
            category_summary = self.get_category_summary()
            for _, row in category_summary.iterrows():
                f.write(f"{row['category'].capitalize()}: ${row['sum']:.2f} ({row['count']} transactions, avg ${row['mean']:.2f})\n")
            f.write("\n")
            
            # Monthly breakdown
            f.write("MONTHLY BREAKDOWN:\n")
            monthly_data = self.df.groupby(['year', 'month'])['amount'].sum().reset_index()
            for _, row in monthly_data.sort_values(['year', 'month']).iterrows():
                month_name = datetime(int(row['year']), int(row['month']), 1).strftime('%B %Y')
                f.write(f"{month_name}: ${row['amount']:.2f}\n")
            f.write("\n")
            
            # Top expenses
            f.write("TOP 10 LARGEST EXPENSES:\n")
            top_expenses = self.df.sort_values('amount', ascending=False).head(10)
            for i, (_, row) in enumerate(top_expenses.iterrows(), 1):
                f.write(f"{i}. ${row['amount']:.2f} - {row['description']} ({row['date'].strftime('%Y-%m-%d')}) - {row['category'].capitalize()}\n")
            f.write("\n")
            
            # Unusual expenses
            unusual_expenses = self.identify_unusual_expenses()
            if unusual_expenses is not None and len(unusual_expenses) > 0:
                f.write("UNUSUAL EXPENSES (2x+ CATEGORY AVERAGE):\n")
                for i, (_, row) in enumerate(unusual_expenses.head(10).iterrows(), 1):
                    f.write(f"{i}. ${row['amount']:.2f} - {row['description']} ({row['date']}) - {row['times_above_avg']:.1f}x avg\n")
            
            print(f"Report generated and saved to {output_file}")