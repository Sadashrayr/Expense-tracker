from expense_tracker import ExpenseTracker
import os
from flask import Flask,render_template,request,redirect,url_for,session,flash,request
from werkzeug.utils import secure_filename
import matplotlib
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, ChatHistory, Expense
from assistant import get_agent, ask_question
import pandas as pd
from dotenv import load_dotenv
# Top of app.py
from datetime import datetime
from collections import defaultdict

matplotlib.use("Agg")  # Use non-interactive backend

app = Flask(__name__)
app.secret_key = "s3cr3t"  # Change this to a random secret key
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload
app.config["ALLOWED_EXTENSIONS"] = {"csv"}
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create upload folder if it doesn't exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            flash("Username already exists", "warning")
            return redirect(url_for("register"))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session.clear()  # ✅ Clear old session data
            login_user(user)

            if user.first_login:
                flash("Welcome, new user! Let's set up your first budget 🎉", "info")
                user.first_login = False
                db.session.commit()

            flash("Logged in successfully", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("index"))

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        flash("No file part", "error")
        return redirect(request.url)

    file = request.files["file"]

    if file.filename == "":
        flash("No file selected", "error")
        return redirect(request.url)

    if file and allowed_file(file.filename):
        # Save file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Process the file
        tracker = ExpenseTracker()
        success = tracker.load_data(filepath)

        if not success:
            flash("Error loading data. Please check your CSV format.", "error")
            return redirect(url_for("index"))

        # Add custom categories if provided
        if request.form.get("custom_categories"):
            try:
                custom_categories = {}
                categories_text = request.form.get("custom_categories")
                for line in categories_text.split("\n"):
                    if ":" in line:
                        category, keywords = line.split(":", 1)
                        custom_categories[category.strip()] = [
                            k.strip() for k in keywords.split(",")
                        ]

                if custom_categories:
                    tracker.add_custom_category_rules(custom_categories)
            except Exception as e:
                flash(
                    f"Error processing custom categories: {str(e)}", "warning")

        # Categorize expenses
        tracker.categorize_expenses()

        # Store the required data in session
        session["has_data"] = True
        session["filepath"] = filepath

        # Generate charts and get data
        category_summary = tracker.get_category_summary()
        monthly_summary = tracker.get_monthly_summary()
        unusual_expenses = tracker.identify_unusual_expenses()

        # Convert DataFrames to lists for JSON serialization
        session["category_summary"] = (
            category_summary.to_dict(
                "records") if category_summary is not None else []
        )
        session["monthly_summary"] = (
            monthly_summary.to_dict(
                "records") if monthly_summary is not None else []
        )
        session["unusual_expenses"] = (
            unusual_expenses.to_dict(
                "records") if unusual_expenses is not None else []
        )

        # Generate and save charts
        try:
            # Category chart
            tracker.plot_expenses_by_category()
            # Monthly trend chart
            tracker.plot_monthly_trend()

            session["charts_generated"] = True
        except Exception as e:
            flash(f"Error generating charts: {str(e)}", "warning")
            session["charts_generated"] = False

        # User's budget (simple implementation)
        if request.form.get("budget"):
            try:
                session["budget"] = float(request.form.get("budget"))
            except ValueError:
                flash("Invalid budget value. Using no budget comparison.", "warning")

        return redirect(url_for("dashboard"))

    flash("Invalid file format. Please upload a CSV file.", "error")
    return redirect(url_for("index"))

@app.route("/upload-from-add-expense", methods=["POST"])
@login_required
def upload_from_add_expense():
    return upload_file()


@app.route("/dashboard")
@login_required
def dashboard():
    view_type = request.args.get("view", "monthly")
    data_scope = request.args.get("scope", "present")
    source = request.args.get("source", "manual")

    is_returning = bool(session.get("filepath") or Expense.query.filter_by(user_id=current_user.id).first())

    uploaded_data = []
    if source == "csv" and session.get("filepath") and os.path.exists(session["filepath"]):
        try:
            df = pd.read_csv(session["filepath"])
            for _, row in df.iterrows():
                uploaded_data.append({
                    "category": str(row.get("category", "unknown")).strip().lower(),
                    "amount": float(row.get("amount", 0)),
                    "date": row.get("date", datetime.now().strftime("%Y-%m-%d"))
                })
        except Exception as e:
            flash(f"Error loading uploaded data: {e}", "danger")

    manual_data = [
        {
            "category": exp.category,
            "amount": exp.amount,
            "date": exp.date.strftime("%Y-%m-%d")
        }
        for exp in Expense.query.filter_by(user_id=current_user.id).all()
    ]

    all_expenses = uploaded_data if (source == "csv" and uploaded_data) else manual_data

    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    current_expenses = []
    historical_expenses = []

    for item in all_expenses:
        try:
            date_obj = datetime.strptime(item.get("date", current_month), "%Y-%m-%d")
        except:
            date_obj = now

        y_m = date_obj.strftime("%Y-%m")
        category = item.get("category", "other").lower()
        amount = float(item.get("amount", 0))

        if data_scope == "present" and y_m == current_month:
            current_expenses.append((category, amount))
        elif data_scope == "past" and y_m != current_month:
            current_expenses.append((category, amount))  # 💡 Here we treat "past" as current scope
        historical_expenses.append((category, amount))  # 🔁 Always build historical from everything

    # 🔹 Scope-based current summary
    category_summary = {}
    total_expenses = 0
    for cat, amt in current_expenses:
        total_expenses += amt
        if cat not in category_summary:
            category_summary[cat] = {"sum": 0, "count": 0}
        category_summary[cat]["sum"] += amt
        category_summary[cat]["count"] += 1

    # 🔹 Historical includes everything
    history_summary = {}
    for cat, amt in historical_expenses:
        if cat not in history_summary:
            history_summary[cat] = 0
        history_summary[cat] += amt

    # 🔸 Budget
    budget = session.get("budget", 0)
    budget_status = {
        "budget": budget,
        "total": total_expenses,
        "remaining": budget - total_expenses,
        "percentage": (total_expenses / budget) * 100 if budget else 0
    } if budget else None

    # 🔸 Trend (simplified - only current scope)
    monthly_summary = defaultdict(float)
    for cat, amt in current_expenses:
        monthly_summary[current_month] += amt

    trend_data = {
        "labels": list(monthly_summary.keys()),
        "values": list(monthly_summary.values())
    }

    pie_data = {
        "labels": list(category_summary.keys()),
        "values": [c["sum"] for c in category_summary.values()]
    }

    category_table = [
        {
            "category": cat,
            "amount": f"₹{summary['sum']:.2f}",
            "percent": f"{(summary['sum'] / total_expenses) * 100:.1f}%" if total_expenses else "0%"
        }
        for cat, summary in category_summary.items()
    ]

    history_total = sum(history_summary.values())
    history_table = [
        {
            "category": cat,
            "amount": f"₹{amt:.2f}",
            "percent": f"{(amt / history_total) * 100:.1f}%" if history_total else "0%"
        }
        for cat, amt in history_summary.items()
    ]

    history_pie = {
        "labels": list(history_summary.keys()),
        "values": list(history_summary.values())
    }

    return render_template(
        "dashboard.html",
        is_returning=is_returning,
        budget_status=budget_status,
        trend_data=trend_data,
        pie_data=pie_data,
        category_table=category_table,
        data_scope=data_scope,
        view_type=view_type,
        source=source,
        history_table=history_table,
        history_pie=history_pie
    )






  # Ensure this is imported

@app.route("/add-expense", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        try:
            base_amount = float(request.form.get("base_amount"))
            time_range = request.form.get("time_range")
            month_year = request.form.get("month_year")

            if not month_year:
                flash("Please select the month for which you are entering expenses.", "warning")
                return redirect(url_for("add_expense"))

            # ✅ Save budget info and selected month in session
            session["budget"] = base_amount
            session["budget_time_range"] = time_range
            session["expense_month"] = month_year  # e.g. "2025-06"

            categories = ['rent', 'food', 'travel', 'electricity', 'entertainment', 'healthcare', 'other']

            for cat in categories:
                amount_str = request.form.get(f"category_{cat}")
                date_str = request.form.get(f"date_{cat}")

                if amount_str:
                    try:
                        amount = float(amount_str)

                        # If no specific date is given, use the first day of the selected month
                        if date_str:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                        else:
                            date_obj = datetime.strptime(month_year + "-01", "%Y-%m-%d").date()

                        expense = Expense(
                            user_id=current_user.id,
                            category=cat,
                            amount=amount,
                            date=date_obj
                        )
                        db.session.add(expense)

                    except ValueError:
                        flash(f"Invalid amount or date for {cat}", "warning")

            db.session.commit()
            session["has_data"] = True
            flash("Budget and expenses saved successfully!", "success")
            return redirect(url_for("dashboard"))

        except Exception as e:
            flash(f"Error processing form: {str(e)}", "danger")
            return redirect(url_for("add_expense"))

    return render_template("add_expense.html", today=datetime.now().strftime("%Y-%m-%d"))






@app.route("/reset")
def reset():
    # Clear session data
    session.clear()
    # Remove temporary files
    if "filepath" in session and os.path.exists(session["filepath"]):
        try:
            os.remove(session["filepath"])
        except:
            pass

    flash("Data has been reset. You can upload a new file.", "info")
    return redirect(url_for("index"))

@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    from datetime import timedelta

    selected_month = request.form.get("month") or session.get("expense_month") or datetime.now().strftime("%Y-%m")
    session["expense_month"] = selected_month

    selected_scope = request.form.get("scope", "present")
    selected_data_type = request.form.get("data_type", "manual")

    # ✅ Generate last 7 months for dropdown
    months_list = [(datetime.now() - timedelta(days=30 * i)).strftime("%Y-%m") for i in range(7)]

    df = pd.DataFrame()

    # Load from database (manual input)
    if selected_data_type == "manual":
        expenses = Expense.query.filter_by(user_id=current_user.id).all()
        manual_data = [
            {
                "category": e.category,
                "amount": e.amount,
                "date": e.date.strftime("%Y-%m-%d")
            }
            for e in expenses
            if e.date.strftime("%Y-%m") == selected_month
        ]
        df = pd.DataFrame(manual_data)

    # Load from CSV
    elif selected_data_type == "csv" and session.get("filepath") and os.path.exists(session["filepath"]):
        try:
            tracker = ExpenseTracker()
            tracker.load_data(session["filepath"])
            data = tracker.data.copy()
            data["date"] = pd.to_datetime(data["date"])
            df = data[data["date"].dt.strftime("%Y-%m") == selected_month].copy()
        except Exception as e:
            flash(f"Error loading uploaded data: {e}", "danger")

    if df.empty:
        flash("No expense data found for the selected month.", "danger")
        return render_template(
            "chat.html",
            chat_history=[],
            answer=None,
            selected_scope=selected_scope,
            selected_data_type=selected_data_type,
            selected_month=selected_month,
            months_list=months_list
        )

    # Ask AI (✅ Removed allow_dangerous_code)
    answer = None
    if request.method == "POST" and request.form.get("question"):
        question = request.form["question"]
        agent = get_agent(df)
        answer = ask_question(agent, question, df)

        new_chat = ChatHistory(user_id=current_user.id, question=question, answer=answer)
        db.session.add(new_chat)
        db.session.commit()

    history = ChatHistory.query.filter_by(user_id=current_user.id).order_by(ChatHistory.timestamp.desc()).all()

    return render_template(
        "chat.html",
        chat_history=history,
        answer=answer,
        selected_scope=selected_scope,
        selected_data_type=selected_data_type,
        selected_month=selected_month,
        months_list=months_list
    )


@app.route("/chat-history")
@login_required
def chat_history():
    history = ChatHistory.query.filter_by(user_id=current_user.id).order_by(ChatHistory.timestamp.desc()).all()
    return render_template("chat_history.html", chat_history=history)



if __name__ == "__main__":
    app.run(debug=True)
