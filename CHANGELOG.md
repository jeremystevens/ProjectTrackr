# FlaskBin Changelog

All notable changes to the FlaskBin project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]
- Enhanced error handling for database operations
- Added paste comments/discussion functionality
- Implemented custom error pages with detailed error information
- Added support for nested comment replies

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
