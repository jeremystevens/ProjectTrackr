# FlaskBin TODO List
This document tracks future enhancements and features planned for the FlaskBin application.
## Medium Priority
- [ ] Create a browser extension for quick pasting
- [ ] [Undecided] Add support for image/file uploads within pastes (content moderation concerns)
- [ ] Implement a dark/light theme toggle
## Low Priority
- [ ] Add email verification for new user registrations (pending SendGrid integration)
- [ ] Add API endpoints for programmatic paste creation and access
- [ ] Add user notification system
- [ ] Create paste collections/folders for organization
- [ ] Implement language detection for unspecified syntax
- [ ] Add export/import functionality for user pastes
- [ ] Support collaborative real-time editing
- [ ] Create a desktop application using Electron
- [ ] Add support for custom paste syntax themes
- [ ] Implement paste encryption for added security
- [ ] Add internationalization (i18n) support
- [ ] Add OpenAI integration for smart features
## Technical Debt
- [ ] Improve test coverage with unit and integration tests
- [ ] Optimize database queries for better performance
- [ ] Add comprehensive API documentation
- [ ] Implement more robust error tracking and monitoring
- [ ] Improve accessibility (WCAG compliance)
- [ ] Containerize application using Docker
- [ ] Set up CI/CD pipeline for automated testing and deployment
- [ ] Add performance metrics and analytics
## Completed Items
- [x] Add paste forking functionality
- [x] Add support for paste versioning (history of edits) for registered users
- [x] Fix UI issues with paste expiration countdown display
- [x] Redesign metadata layout for better spacing and consistency
- [x] Improve UI styling with italic timestamp and compact date format
- [x] Fix duplicate "Enable comments" checkbox in paste form
- [x] Create a user dashboard with more detailed statistics
- [x] Implement real-time expiration countdown
- [x] Create automated paste pruning system
- [x] Implement paste templates (common layouts/snippets)
- [x] Fix database integrity issues with paste deletion
- [x] Add CSRF protection for all forms
- [x] Add password strength meter to registration form
- [x] Implement security answer validation to prevent common answers
- [x] Add two-factor security for account recovery (security questions)
- [x] Implement comprehensive error handling with custom error pages
- [x] Create comment system with reply functionality
- [x] Implement rate limiting to prevent abuse
- [x] Add paste comments/discussion functionality
- [x] Improve error pages with more helpful messages
- [x] Implement password reset functionality with security questions
- [x] Implement account lockout protection after failed attempts
- [x] Add password strength requirements and validation
