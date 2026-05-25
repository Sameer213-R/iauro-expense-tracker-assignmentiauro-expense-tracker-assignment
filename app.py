import os
import io
from flask import Flask, render_template, url_for, flash, redirect, request, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from models import db, User, Expense
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_db():
    with app.app_context():
        db.create_all()

@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard():
    expenses = Expense.query.filter_by(author=current_user).order_by(Expense.created_at.desc()).all()
    return render_template('index.html', title='Dashboard', expenses=expenses)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
            
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered. Please login.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        user = User(full_name=full_name, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', title='Register')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login')

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/expense/new", methods=['GET', 'POST'])
@login_required
def new_expense():
    if request.method == 'POST':
        category = request.form.get('category')
        amount = request.form.get('amount')
        comments = request.form.get('comments')
        expense = Expense(category=category, amount=float(amount), comments=comments, author=current_user)
        db.session.add(expense)
        db.session.commit()
        flash('Your expense has been added!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('expense_form.html', title='Add Expense', legend='New Expense')

@app.route("/expense/<int:expense_id>/update", methods=['GET', 'POST'])
@login_required
def update_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if expense.author != current_user:
        flash('You are not authorized to edit this expense.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        expense.category = request.form.get('category')
        expense.amount = float(request.form.get('amount'))
        expense.comments = request.form.get('comments')
        db.session.commit()
        flash('Your expense has been updated!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('expense_form.html', title='Update Expense', legend='Update Expense', expense=expense)

@app.route("/expense/<int:expense_id>/delete", methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if expense.author != current_user:
        flash('You are not authorized to delete this expense.', 'danger')
        return redirect(url_for('dashboard'))
    db.session.delete(expense)
    db.session.commit()
    flash('Your expense has been deleted!', 'success')
    return redirect(url_for('dashboard'))

@app.route("/analytics/chart.png")
@login_required
def expense_chart():
    expenses = Expense.query.filter_by(author=current_user).all()
    if not expenses:
        # Create an empty figure
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.pie([1], labels=['No Expenses'], colors=['#e0e0e0'])
        ax.set_title('Expense Distribution')
    else:
        categories = {}
        for exp in expenses:
            categories[exp.category] = categories.get(exp.category, 0) + exp.amount
            
        labels = list(categories.keys())
        sizes = list(categories.values())
        
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, 
               colors=['#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4cc9f0', '#00b4d8', '#0077b6'])
        ax.set_title('Expense Distribution', pad=20, fontsize=16, fontweight='bold', color='#333')
        
    plt.tight_layout()
    img = io.BytesIO()
    plt.savefig(img, format='png', transparent=True)
    img.seek(0)
    plt.close()
    return send_file(img, mimetype='image/png')

if __name__ == '__main__':
    create_db()
    app.run(debug=True)
