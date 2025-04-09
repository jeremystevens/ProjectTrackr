from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, URL, Optional, ValidationError
import re
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    security_question = SelectField('Security Question', choices=[
        ('pet', 'What was the name of your first pet?'),
        ('school', 'What was the name of your first school?'),
        ('city', 'In what city were you born?'),
        ('mother', 'What is your mother\'s maiden name?'),
        ('book', 'What is your favorite book?'),
        ('food', 'What is your favorite food?'),
        ('custom', 'Custom question (specify below)')
    ])
    custom_question = StringField('Custom Security Question (optional)')
    security_answer = StringField('Security Answer', validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already taken. Please choose a different one.')
        
        # Check if username has valid characters
        if not re.match(r'^[a-zA-Z0-9_]+$', username.data):
            raise ValidationError('Username can only contain letters, numbers, and underscores.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered. Please use a different one.')

class PasteForm(FlaskForm):
    title = StringField('Title', validators=[Length(max=255)])
    content = TextAreaField('Content', validators=[DataRequired()])
    syntax = SelectField('Syntax Highlighting', choices=[
        ('text', 'Plain Text'),
        ('python', 'Python'),
        ('javascript', 'JavaScript'),
        ('html', 'HTML'),
        ('css', 'CSS'),
        ('java', 'Java'),
        ('c', 'C'),
        ('cpp', 'C++'),
        ('csharp', 'C#'),
        ('php', 'PHP'),
        ('ruby', 'Ruby'),
        ('go', 'Go'),
        ('rust', 'Rust'),
        ('swift', 'Swift'),
        ('bash', 'Bash/Shell'),
        ('sql', 'SQL'),
        ('xml', 'XML'),
        ('json', 'JSON'),
        ('markdown', 'Markdown'),
        ('yaml', 'YAML')
    ])
    expiration = SelectField('Expiration', choices=[
        ('0', 'Never'),
        ('1', '10 Minutes'),
        ('2', '1 Hour'),
        ('3', '1 Day'),
        ('4', '1 Month')
    ])
    visibility = SelectField('Visibility', choices=[
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
        ('private', 'Private')
    ])
    submit = SubmitField('Create Paste')

class ProfileEditForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=500)])
    website = StringField('Website', validators=[Optional(), URL()])
    location = StringField('Location', validators=[Optional(), Length(max=100)])
    current_password = PasswordField('Current Password', validators=[Optional()])
    new_password = PasswordField('New Password', validators=[Optional(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[
        Optional(), EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Update Profile')

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    search_type = SelectField('Search By', choices=[
        ('content', 'Content'),
        ('title', 'Title'),
        ('syntax', 'Syntax'),
        ('author', 'Author')
    ])
    submit = SubmitField('Search')

class RequestPasswordResetForm(FlaskForm):
    """Form for requesting a password reset"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if not user:
            raise ValidationError('There is no account with that email. Please register first.')
            
class SecurityAnswerForm(FlaskForm):
    """Form for answering the security question during password reset"""
    security_answer = StringField('Answer to Security Question', validators=[DataRequired()])
    submit = SubmitField('Verify Answer')

class ResetPasswordForm(FlaskForm):
    """Form for setting a new password after reset"""
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')
