from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import DbTask
import random
import pandas as pd
import time
from datetime import datetime
import numpy as np

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages and sessions

# Create database connection
db_task = DbTask()
db_connect = db_task.creating_connecting()
cursor = db_connect.cursor()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/balance_enquiry', methods=['GET', 'POST'])
def balance_enquiry():
    if request.method == 'POST':
        ac = request.form.get('account_id')
        pin = request.form.get('pin')
        
        if not ac or not pin:
            flash('Please fill all fields', 'danger')
            return render_template('balance_enquiry.html')
        
        try:
            ac = int(ac)
            pin = int(pin)
        except ValueError:
            flash('Account ID and PIN must be numbers', 'danger')
            return render_template('balance_enquiry.html')
        
        # Check if account exists
        q1 = "SELECT ACCOUNT_ID FROM ACCOUNTS;"
        cursor.execute(q1)
        result = cursor.fetchall()
        result2 = [row[0] for row in result]
        
        if ac in result2:
            q2 = f"SELECT PIN, BALANCE FROM ACCOUNTS WHERE ACCOUNT_ID={ac};"
            cursor.execute(q2)
            result = cursor.fetchall()
            
            if pin == result[0][0]:
                flash(f'Current Balance: {result[0][1]}', 'success')
            else:
                flash('Incorrect PIN number', 'danger')
        else:
            flash('There is no account with that ID', 'danger')
            
        return render_template('balance_enquiry.html')
    
    return render_template('balance_enquiry.html')

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        name = request.form.get('name')
        ph = request.form.get('mobile')
        city = request.form.get('city')
        pin = request.form.get('pin')
        pin2 = request.form.get('pin2')
        
        if not name or not ph or not city or not pin or not pin2:
            flash('Please fill all fields', 'danger')
            return render_template('create_account.html')
        
        try:
            pin = int(pin)
            pin2 = int(pin2)
        except ValueError:
            flash('PIN must be a number', 'danger')
            return render_template('create_account.html')
        
        # Generate unique account number
        q1 = "SELECT ACCOUNT_ID FROM ACCOUNTS;"
        cursor.execute(q1)
        result = cursor.fetchall()
        result2 = [row[0] for row in result]
        
        ac = random.randint(1000000, 9999999)
        while ac in result2:
            ac = random.randint(1000000, 9999999)
        
        if pin == pin2:
            try:
                q2 = f"INSERT INTO ACCOUNTS VALUES ({ac},'{name}','{ph}','{city}',{pin},500,now());"
                cursor.execute(q2)
                
                # Create transaction table for the user
                q3 = f'CREATE TABLE {name}(TRANSACTION_ID INT PRIMARY KEY AUTO_INCREMENT, AC_ID INT, AMOUNT DECIMAL(6,2), TRANS_DATE DATETIME);'
                cursor.execute(q3)
                
                # Create trigger for automatic balance update
                q4 = f"CREATE TRIGGER AFTER_INSERT_{name} AFTER INSERT ON {name} FOR EACH ROW UPDATE ACCOUNTS SET BALANCE = BALANCE + NEW.AMOUNT WHERE ACCOUNT_ID = NEW.AC_ID"
                cursor.execute(q4)
                
                db_connect.commit()
                flash(f'Account created successfully with account number {ac}', 'success')
            except Exception as e:
                db_connect.rollback()
                flash(f'Error creating account: {str(e)}', 'danger')
        else:
            flash('PIN numbers do not match', 'danger')
            
        return render_template('create_account.html')
    
    return render_template('create_account.html')

@app.route('/credit', methods=['GET', 'POST'])
def credit():
    if request.method == 'POST':
        ac = request.form.get('account_id')
        amount = request.form.get('amount')
        
        if not ac or not amount:
            flash('Please fill all fields', 'danger')
            return render_template('credit.html')
        
        try:
            ac = int(ac)
            amount = float(amount)
        except ValueError:
            flash('Account ID and amount must be numbers', 'danger')
            return render_template('credit.html')
        
        # Check if account exists
        q1 = "SELECT ACCOUNT_ID, HOLDER_NAME FROM ACCOUNTS WHERE ACCOUNT_ID = %s;"
        cursor.execute(q1, (ac,))
        result = cursor.fetchall()
        
        if result:
            try:
                q2 = f"INSERT INTO {result[0][1]} (AC_ID, AMOUNT, TRANS_DATE) VALUES ({ac}, {amount}, now())"
                cursor.execute(q2)
                db_connect.commit()
                flash('Amount credited successfully', 'success')
            except Exception as e:
                db_connect.rollback()
                flash(f'Error crediting amount: {str(e)}', 'danger')
        else:
            flash('There is no account with that ID', 'danger')
            
        return render_template('credit.html')
    
    return render_template('credit.html')

@app.route('/debit', methods=['GET', 'POST'])
def debit():
    if request.method == 'POST':
        ac = request.form.get('account_id')
        amount = request.form.get('amount')
        pin = request.form.get('pin')
        
        if not ac or not amount or not pin:
            flash('Please fill all fields', 'danger')
            return render_template('debit.html')
        
        try:
            ac = int(ac)
            amount = float(amount)
            pin = int(pin)
        except ValueError:
            flash('Account ID, amount, and PIN must be numbers', 'danger')
            return render_template('debit.html')
        
        # Check if account exists and get balance
        q1 = "SELECT ACCOUNT_ID, BALANCE, PIN, HOLDER_NAME FROM ACCOUNTS WHERE ACCOUNT_ID = %s;"
        cursor.execute(q1, (ac,))
        result = cursor.fetchall()
        
        if result:
            if pin == result[0][2]:
                if amount <= result[0][1]:
                    try:
                        q2 = f"INSERT INTO {result[0][3]} (AC_ID, AMOUNT, TRANS_DATE) VALUES ({ac}, {-amount}, now());"
                        cursor.execute(q2)
                        db_connect.commit()
                        flash('Amount debited successfully', 'success')
                    except Exception as e:
                        db_connect.rollback()
                        flash(f'Error debiting amount: {str(e)}', 'danger')
                else:
                    flash('Insufficient funds', 'danger')
            else:
                flash('Incorrect PIN number', 'danger')
        else:
            flash('There is no account with that ID', 'danger')
            
        return render_template('debit.html')
    
    return render_template('debit.html')

@app.route('/change_pin', methods=['GET', 'POST'])
def change_pin():
    if request.method == 'POST':
        ac = request.form.get('account_id')
        old_pin = request.form.get('old_pin')
        new_pin = request.form.get('new_pin')
        new_pin2 = request.form.get('new_pin2')
        
        if not ac or not old_pin or not new_pin or not new_pin2:
            flash('Please fill all fields', 'danger')
            return render_template('change_pin.html')
        
        try:
            ac = int(ac)
            old_pin = int(old_pin)
            new_pin = int(new_pin)
            new_pin2 = int(new_pin2)
        except ValueError:
            flash('Account ID and PINs must be numbers', 'danger')
            return render_template('change_pin.html')
        
        # Check if account exists
        q1 = "SELECT ACCOUNT_ID, PIN FROM ACCOUNTS WHERE ACCOUNT_ID = %s;"
        cursor.execute(q1, (ac,))
        result = cursor.fetchall()
        
        if result:
            if old_pin == result[0][1]:
                if new_pin == new_pin2:
                    try:
                        q2 = f"UPDATE ACCOUNTS SET PIN = {new_pin} WHERE ACCOUNT_ID = {ac};"
                        cursor.execute(q2)
                        db_connect.commit()
                        flash('PIN changed successfully', 'success')
                    except Exception as e:
                        db_connect.rollback()
                        flash(f'Error changing PIN: {str(e)}', 'danger')
                else:
                    flash('New PINs do not match', 'danger')
            else:
                flash('Incorrect old PIN', 'danger')
        else:
            flash('There is no account with that ID', 'danger')
            
        return render_template('change_pin.html')
    
    return render_template('change_pin.html')

@app.route('/view_transactions', methods=['GET', 'POST'])
def view_transactions():
    if request.method == 'POST':
        ac = request.form.get('account_id')
        
        if not ac:
            flash('Please enter an account ID', 'danger')
            return render_template('view_transactions.html')
        
        try:
            ac = int(ac)
        except ValueError:
            flash('Account ID must be a number', 'danger')
            return render_template('view_transactions.html')
        
        # Check if account exists
        q1 = "SELECT ACCOUNT_ID, HOLDER_NAME FROM ACCOUNTS WHERE ACCOUNT_ID = %s;"
        cursor.execute(q1, (ac,))
        result = cursor.fetchall()
        
        if result:
            try:
                q2 = f'SELECT TRANSACTION_ID, AMOUNT, TRANS_DATE FROM {result[0][1]}'
                cursor.execute(q2)
                transactions = cursor.fetchall()
                
                # Convert to list of dictionaries for the template
                transactions_list = []
                for row in transactions:
                    transactions_list.append({
                        'transaction_id': row[0],
                        'amount': row[1],
                        'trans_date': row[2].strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                return render_template('view_transactions.html', transactions=transactions_list)
            except Exception as e:
                flash(f'Error retrieving transactions: {str(e)}', 'danger')
        else:
            flash('There is no account with that ID', 'danger')
            
        return render_template('view_transactions.html')
    
    return render_template('view_transactions.html')

if __name__ == '__main__':
    app.run(debug=True)