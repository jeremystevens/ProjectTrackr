from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import db, User
from datetime import datetime, timedelta
import os

# Create blueprint
account_bp = Blueprint('account', __name__)

@account_bp.route('/account')
@login_required
def account_page():
    """Display the user's account details including subscription information"""
    user = current_user
    
    # Calculate subscription values for display
    subscription_active = user.is_subscription_active()
    days_remaining = user.get_subscription_days_remaining()
    tier_limits = user.get_tier_limits()
    
    # Get subscription features
    features = {
        'ai_calls': {
            'remaining': user.ai_calls_remaining,
            'total': tier_limits['ai_calls'],
            'percentage': (user.ai_calls_remaining / tier_limits['ai_calls'] * 100) if tier_limits['ai_calls'] > 0 else 0
        },
        'ai_search': {
            'remaining': user.ai_search_queries_remaining,
            'total': tier_limits['ai_search_queries'],
            'percentage': (user.ai_search_queries_remaining / tier_limits['ai_search_queries'] * 100) if tier_limits['ai_search_queries'] > 0 else 0
        },
        'free_ai_trials': {
            'remaining': user.get_remaining_free_trials(),
            'total': 3,  # Maximum number of free trials
            'used': user.free_ai_trials_used,
            'percentage': ((3 - user.free_ai_trials_used) / 3 * 100) if user.free_ai_trials_used <= 3 else 0
        },
        'live_collaboration': tier_limits['live_collaboration'],
        'team_seats': tier_limits['team_seats'],
        'custom_themes': tier_limits['custom_themes'],
        'analytics': tier_limits['analytics'],
        'scheduled_publishing': tier_limits['scheduled_publishing'],
        'private_comments': tier_limits['private_comments']
    }
    
    return render_template(
        'user/account.html',
        user=user,
        subscription_active=subscription_active,
        days_remaining=days_remaining,
        tier_name=user.get_tier_display_name(),
        features=features
    )

@account_bp.route('/account/upgrade')
@login_required
def upgrade_subscription():
    """Page to upgrade subscription"""
    # This is a placeholder and will be expanded with actual payment integration
    return render_template('user/upgrade.html')

@account_bp.route('/account/simulate_upgrade/<tier>')
@login_required
def simulate_upgrade(tier):
    """
    Simulates upgrading to a subscription tier (for development only).
    In production, this would be handled by a payment processor callback.
    """
    if tier not in ['free', 'starter', 'pro', 'team']:
        flash('Invalid subscription tier.', 'error')
        return redirect(url_for('account.account_page'))
    
    # Update user's subscription details
    user = current_user
    
    # Set subscription tier
    user.subscription_tier = tier
    
    if tier == 'free':
        # Cancelling subscription
        user.subscription_end_date = datetime.utcnow()
        user.ai_calls_remaining = 0
        user.ai_search_queries_remaining = 0
        flash('You have downgraded to the Free plan.', 'info')
    else:
        # Set subscription dates
        user.subscription_start_date = datetime.utcnow()
        user.subscription_end_date = datetime.utcnow() + timedelta(days=30)  # 30-day subscription
        
        # Reset usage counters based on tier
        limits = user.get_tier_limits()
        user.ai_calls_remaining = limits['ai_calls']
        user.ai_search_queries_remaining = limits['ai_search_queries']
        
        # Set premium flag to true
        user.is_premium = True
        
        flash(f'You have upgraded to the {user.get_tier_display_name()} plan!', 'success')
    
    db.session.commit()
    return redirect(url_for('account.account_page'))