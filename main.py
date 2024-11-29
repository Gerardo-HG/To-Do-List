import os
import datetime as dt
from typing import List
from flask import Flask, render_template, url_for, redirect,flash, request
from flask_wtf import FlaskForm
from flask_bootstrap import Bootstrap5
from wtforms import EmailField, SelectField, StringField, PasswordField,SubmitField
from wtforms.validators import DataRequired,InputRequired
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from flask_login import LoginManager, login_required, logout_user, current_user, UserMixin, login_user
from werkzeug.security import generate_password_hash, check_password_hash


#Flask 
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///to-do-list.db"
Bootstrap5(app)

# Register Formx
class RegisterForm(FlaskForm):
    name = StringField(label="Enter your Name. ",validators=[DataRequired()])
    email = EmailField(label="Your Email. ",validators=[DataRequired()])
    password = PasswordField(label="Your Password. ",validators=[DataRequired()])
    major = SelectField(label="Your major. ",choices=['x','Software Enginner','Computer Science','Web Designer','Data Engineer','Data Scientist','Cloud Engineer'],validate_choice=True)
    submit = SubmitField(label="Submit")

# Login Form
class LoginForm(FlaskForm):
    email = EmailField(label='Email',validators=[InputRequired()])
    password = PasswordField(label='Password',validators=[InputRequired()])
    submit = SubmitField(label='Log in')

# Creating Model Declarative Base
class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
db.init_app(app)

class User(UserMixin,db.Model):
    __tablename__ = "user"
    id_user: Mapped[int]  = mapped_column(Integer,primary_key=True)
    name: Mapped[str] = mapped_column(String(250),nullable=False)
    email: Mapped[str] = mapped_column(String(250),unique=True,nullable=False)
    password: Mapped[str] = mapped_column(String(250),nullable=False)
    major: Mapped[str] = mapped_column(String(250),nullable=False)
    tasks : Mapped[List["Task"]] = relationship("Task",back_populates="user")

    def get_id(self):
        return self.id_user

class Task(db.Model):
    __tablename__ = "task"
    id_task : Mapped[int] = mapped_column(Integer,primary_key=True)
    description : Mapped[str] = mapped_column(String(250),nullable=False) 
    state: Mapped[bool] = mapped_column(Boolean,default=False)
    id_user : Mapped[int] = mapped_column(ForeignKey("user.id_user"))
    user: Mapped["User"] = relationship("User",back_populates="tasks")

with app.app_context():
    db.create_all()

# Login Authentication
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User,user_id)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template('index.html')

@login_required
@app.route("/task/<int:id>", methods=["GET","POST"])
def show_tasks(id):
    user = db.get_or_404(User,id)
    date_today = dt.datetime.now().strftime("%x")
    
    if not current_user.is_authenticated:
        flash('You need to login with your account')
        return redirect(url_for('login_page'))
    
    elif id != current_user.id_user:
        logout_user()
        flash("It requires another account")
        return redirect(url_for("login_page"))

    if request.method == "POST":
            new_task = Task(
                description = request.form.get("task"),
                id_user = current_user.id_user,                
                )
            db.session.add(new_task)
            db.session.commit()
            return redirect(url_for('show_tasks',id=current_user.id_user))

    all_tasks_complete = not db.session.execute(db.select(Task.state).where(Task.id_user == id, Task.state == False)).scalars().first()

    return render_template('to-do.html',user=user,logged_in=user.is_authenticated,date=str(date_today),all_tasks_complete=all_tasks_complete)



@app.route('/register',methods=["POST","GET"])
def register_page():
    register_form = RegisterForm()
    error = None
    emails_registered = db.session.execute(db.select(User.email)).scalars().all()

    if register_form.validate_on_submit():
        email_ = register_form.email.data
        if email_ in emails_registered:
            flash("You've already sign up with that email, Log in instead")
            return redirect(url_for('login_page'))
        else:
            flash("Your were successfully register in")
            secure_password = generate_password_hash(register_form.password.data)
            new_user = User(
                name = register_form.name.data,
                email = email_,
                password = secure_password,
                major = register_form.major.data
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('home'))

    return render_template('register.html',form=register_form)

@app.route('/login',methods=["GET","POST"])
def login_page():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        user_selected = db.session.execute(db.select(User).where(User.email == login_form.email.data)).scalar()
        if not user_selected:
            flash('The email does not exist. Please try again.')
            return redirect(url_for('login_page'))

        elif not check_password_hash(user_selected.password, login_form.password.data):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login_page'))
        else:
            login_user(user_selected)
            return redirect(url_for('show_tasks',id=user_selected.id_user))

    return render_template('login.html',form=login_form)


@app.route('/done/<int:task_id>')
def done_task(task_id):
    task_complete = db.get_or_404(Task,task_id)
    task_complete.state = True if task_complete.state == False else False
    db.session.commit()
    
    return redirect(url_for('show_tasks',id=task_complete.id_user))
    

@login_required
@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    task_to_delete = db.get_or_404(Task,task_id)
    db.session.delete(task_to_delete)
    db.session.commit()

    return redirect(url_for('show_tasks',id=task_to_delete.id_user))

if __name__ == '__main__':
    app.run(debug=True)