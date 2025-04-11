# FlaskBin Changelog

All notable changes to the FlaskBin project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]
- Added AI-powered code summary generation for pastes
- Implemented premium feature tracking for AI functionality
- Added free trial system for AI features (3 free uses)
- Redesigned paste view with improved layout and organization
- Added separated metadata section between title and action buttons
- Moved paste action buttons to a dedicated row to prevent layout breaking with long titles
- Made content reporting functionality available to all users (not just registered users)
- Made Report button more prominent with action buttons for better content moderation
- Added user notification system for comments and forks
- Added dark/light theme toggle with automatic mode detection
- Added paste templates for common layouts and code snippets
- Added paste forking functionality with visibility options
- Added fork count and "forked from" indicators on pastes
- Added support for paste versioning (history of edits) for registered users
- Redesigned paste metadata display with flexible single-row layout
- Improved UI styling with italic timestamps and compact date format
- Fixed spacing issues between visibility indicator and expiration time
- Added comprehensive user dashboard with detailed statistics and visualizations
- Enhanced error handling for database operations
- Added paste comments/discussion functionality
- Implemented custom error pages with detailed error information
- Added support for nested comment replies
- Implemented rate limiting to prevent abuse of key routes
- Implemented paste collections/folders for better organization
- Added Sentry integration for error monitoring and tracking
- Improved folder selection UI with a clean dropdown interface
- Moved folder display from dashboard to profile page to match Pastebin's UI
- Implemented administrator dashboard for site moderation and management
- Added content moderation system with flagging and review functionality
- Added admin-only user management tools for handling user roles and permissions
- Added site-wide settings management for configuration options
- Implemented comprehensive audit logging for administrator actions
- Added security features for account lockout and protection against abuse
- Implemented automatic programming language detection for pastes
- Fixed shadowban toggle functionality in admin panel
- Enhanced content flagging system with clear UI and improved button styling
- Added comprehensive paste export functionality with multiple format options (JSON, CSV, plaintext)
- Added paste import functionality with support for JSON and CSV formats
- Added dedicated user interface for import/export operations with collection filtering

## [1.0.0] - 2025-04-09
### Added
- Core pastebin functionality with syntax highlighting
- User registration and authentication system
- Paste creation, editing, and deletion
- Multiple expiration options (10 minutes, 1 hour, 1 day, 1 month, never)
- Public, private, and unlisted paste visibility settings
- User profiles with statistics (total pastes, views)
- Profile editing functionality
- Paste search functionality by content, title, syntax, or author
- Syntax highlighting for over 20 programming languages
- Automated paste pruning system for expired pastes
- Cron job setup for scheduled pruning
- Share buttons for social media
- Copy to clipboard functionality
- Real-time expiration countdown display
- Print view for pastes
- Raw and download options for pastes
- Unique view counting system

### Fixed
- Database integrity errors when deleting pastes
- Expiration countdown display issues
- CSRF token implementation across all forms

### Technical
- Flask web framework with PostgreSQL database
- Flask-Login for authentication
- Flask-WTF for form handling and CSRF protection
- SQLAlchemy ORM for database operations
- Pygments for syntax highlighting
- Bleach for content sanitization
- Bootstrap 5 for frontend styling
- Responsive design for mobile and desktop
- Automated database creation and initialization
- Comprehensive error handling and logging
