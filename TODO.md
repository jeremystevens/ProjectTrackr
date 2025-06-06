# FlaskBin TODO List
This document tracks future enhancements and features planned for the FlaskBin application.
## High Priority
- [ ] Implement premium subscription functionality with Stripe integration
  - [ ] Complete Stripe checkout flow for plan purchases
  - [ ] Implement webhooks for payment events
  - [ ] Add billing history view
  - [ ] Setup automated monthly/yearly billing
- [ ] Create OpenAI integration for AI-powered features (tags, fixes, refactoring, summarization)
  - [ ] Implement API key management
  - [ ] Add queue-based processing for heavy operations
  - [ ] Create result caching system to minimize API costs
  - [ ] Develop AI Summarization feature that explains what code does
  - [ ] Implement free trial AI features for non-guest users (3 free uses)

## Subscription Management
- [ ] Show user's current plan details from database or Stripe
- [ ] Implement plan upgrade/downgrade workflows
- [ ] Create admin interface to manage user subscription tiers
- [ ] Build monthly usage counters and automated resets
- [ ] Implement restriction of premium features based on plan tier
- [ ] Add usage alerts when approaching limits

## Medium Priority
- [ ] [Undecided] Add support for image/file uploads within pastes (content moderation concerns)
- [ ] Fix light mode styling issues (temporarily disabled theme toggle)
- [ ] Implement custom syntax themes for Pro and Team subscribers
- [ ] Build per-paste analytics for subscribers (views, source info)

## Premium Features
- [ ] AI-Generated Tags for pastes (Starter+)
- [ ] AI Fix Suggestions for code pastes (Starter+)
- [ ] AI Code Refactoring (Pro+)
- [ ] AI Code Summarization feature (Starter+)
- [ ] Free AI feature trials for registered users (3 free uses)
- [ ] Advanced AI Search (Pro+)
- [ ] Per-Paste Analytics (Starter+)
- [ ] Paste Access Insights (Pro+)
- [ ] Scheduled Paste Publishing (Pro+)
- [ ] Private Comments functionality (Pro+)
- [ ] Live Collaborative Pastes (Team)
- [ ] Team seat sharing (Team)
- [x] Tagging system as a Premium feature
## Low Priority
- [ ] Add email verification for new user registrations (pending SendGrid integration)
- [ ] Add API endpoints for programmatic paste creation and access
- [ ] Create a browser extension for quick pasting
- [ ] Support collaborative real-time editing
- [ ] Create a desktop application using Electron
- [ ] Add internationalization (i18n) support
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
- [x] Restructure paste view layout with separated title, metadata, and action rows
- [x] Make reporting functionality available to all users for better content moderation
- [x] Prepare UI layout for future AI code summary section
- [x] Implement paste encryption with password protection
- [x] Add export/import functionality for user pastes
- [x] Create paste collections/folders for organization
- [x] Create administrator dashboard for site monitoring and moderation
- [x] Implement language detection for unspecified syntax
- [x] Add user notification system
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
- [x] Implement a dark/light theme toggle with customized styling
- [x] Implement tagging system as a Premium feature
