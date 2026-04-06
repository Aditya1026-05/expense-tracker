from flask import Flask, render_template, request, redirect, url_for, make_response, flash, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime, date as dt_date
from sqlalchemy import func

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'my-secret-key'

db = SQLAlchemy(app)

class Expenses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)

with app.app_context():
    db.create_all()

CATEGORIES = ['Food','transport','Health','Utilities','Rent']

def parse_date_or_none(s: str):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None



@app.route("/")
def index():

#1 reading query strings
    start_str = (request.args.get("start") or "").strip()
    end_str = (request.args.get("end") or "").strip()
    selected_category = (request.args.get("category") or "").strip()

#2 parsing

    start_date = parse_date_or_none(start_str)
    end_date = parse_date_or_none(end_str)
    



    if start_date and end_date and end_date < start_date:
        flash("End date cannot be before start date", "error")
        start_date = end_date = None
        start_str = end_str = ""

    q = Expenses.query
    
    if start_date:
        q = q.filter(Expenses.date >= start_date)
    if end_date:
        q = q.filter(Expenses.date <= end_date)

    if selected_category:
        q = q.filter(Expenses.category == selected_category)

    expenses = q.order_by(Expenses.date.desc(), Expenses.id.desc()).all()
    total = round(sum(e.amount for e in expenses), 2)


###for pie chart
    cat_q = db.session.query(Expenses.category, func.sum(Expenses.amount))

    if start_date:
        cat_q = cat_q.filter(Expenses.date >= start_date)

    if end_date:
        cat_q = cat_q.filter(Expenses.date <= end_date)

    if selected_category:
        cat_q = cat_q.filter(Expenses.category == selected_category)

    cat_rows = cat_q.group_by(Expenses.category).all()
    cat_labels = [c for c, _ in cat_rows]
    cat_values = [round(float(s or 0),2) for _, s in cat_rows]
#################

###for day chart
    day_q = db.session.query(Expenses.date, func.sum(Expenses.amount))

    if start_date:
        day_q = day_q.filter(Expenses.date >= start_date)

    if end_date:
        day_q = day_q.filter(Expenses.date <= end_date)

    if selected_category:
        day_q = day_q.filter(Expenses.category == selected_category)

    day_rows = day_q.group_by(Expenses.date).order_by(Expenses.date).all()
    day_labels = [d.isoformat() for d, _ in day_rows]
    day_values = [round(float(s or 0),2) for _, s in day_rows]
#################


    print(expenses)
    return render_template("index.html",  
            categories=CATEGORIES,
            today = date.today().isoformat(),
            expenses=expenses,
            total = total,
            start_str = start_str,
            end_str = end_str,
            selected_category= selected_category,
            cat_labels=cat_labels,
            cat_values=cat_values,
            day_labels=day_labels,
            day_values=day_values,

    
    )


@app.route("/add", methods=['POST'])
def add():

    description = (request.form.get("description") or "").strip()
    amount_str = (request.form.get("amount") or "").strip()
    category = (request.form.get("category") or "").strip()
    date_str = (request.form.get("date") or "").strip()

    if not description or not amount_str or not category:
        flash("Please fill the description, amount, and category", "error")
        return redirect(url_for("index"))
    
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError 


    except ValueError:
        flash('amout must be a positive number',"error")
        return redirect(url_for("index"))

    try:
        d = datetime.strptime(date_str,"%Y-%m-%d").date() if date_str else date.today()

    except ValueError:
        d = date.today()

    
    e = Expenses(description=description, amount=amount, category=category, date=d)
    db.session.add(e)
    db.session.commit()

    flash("Expense added", "success")
    return redirect(url_for("index"))
 

@app.route("/delete/<int:expense_id>", methods=['POST'])
def delete(expense_id):
    e = Expenses.query.get_or_404(expense_id)
    db.session.delete(e)
    db.session.commit()
    flash("Expense deleted", "success")
    return redirect(url_for("index"))

@app.route("/edit/<int:expense_id>", methods=['GET'])
def edit(expense_id):
    e = Expenses.query.get_or_404(expense_id)
    
    return render_template('edit.html',
    expenses = e,
    categories=CATEGORIES,
    today=dt_date.today().isoformat()
     )

@app.route("/edit/<int:expense_id>", methods=['POST'])
def edit_post(expense_id):
    e = Expenses.query.get_or_404(expense_id)

    description = (request.form.get("description") or "").strip()
    amount_str = (request.form.get("amount") or "").strip()
    category = (request.form.get("category") or "").strip()
    date_str = (request.form.get("date") or "").strip()

    print(request.form)

    if not description or not amount_str or not category:
        flash("Please fill description, amount, category!", "error")
        return redirect(url_for("edit", expense_id=expense_id))

    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Amount must be positive number")

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else dt_date.today()
    except ValueError:
        d = dt_date.taday()

    e.description = description
    e.amount = amount
    e.category = category
    e.date = d

    db.session.commit()
    flash("Expense updated", "success")
    return redirect(url_for("index"))



    return render_template('edit.html',
    expenses = e,
    categories=CATEGORIES,
    today=dt_date.today().isoformat()
     )

@app.route("/export.csv")
def export_csv():
#1 reading query strings
    start_str = (request.args.get("start") or "").strip()
    end_str = (request.args.get("end") or "").strip()
    selected_category = (request.args.get("category") or "").strip()

#2 parsing

    start_date = parse_date_or_none(start_str)
    end_date = parse_date_or_none(end_str)

    q = Expenses.query
    
    if start_date:
        q = q.filter(Expenses.date >= start_date)
    if end_date:
        q = q.filter(Expenses.date <= end_date)

    if selected_category:
        q = q.filter(Expenses.category == selected_category)

    expenses = q.order_by(Expenses.date, Expenses.id).all()

    lines = ["date, description, category, amount"]

    for e in expenses:
        lines.append(f"{e.date.isoformat()},{e.description}, {e.category}, {e.amount: .2f}")
    csv_data = "\n".join(lines)

    fname_start = start_str or "all"
    fname_end = end_str or "all"
    filename = f"expenses_{fname_start}_to_{fname_end}.csv"

    return Response(
        csv_data,
        headers = {
            "Content-Type": "text/csv",
            "Content-Disposition": f"attachments; filename={filename}"
        }
    )


if __name__ == "__main__":
    app.run(debug=True,port=4848)
