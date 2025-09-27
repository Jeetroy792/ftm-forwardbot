# Overview
This is a Telegram Auto-Forward Bot (V2) built with Python and Pyrogram. The bot enables users to automatically forward messages from one Telegram channel/chat to another with advanced filtering, customization, and management features. It supports both regular bots and userbots (session-based authentication) for accessing private channels, includes duplicate message detection, custom captions, buttons, and real-time monitoring capabilities.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
- **Core Framework**: Pyrogram (v2.0.93) for Telegram Bot API interactions
- **Architecture Pattern**: Plugin-based modular architecture with separate files for different functionalities
- **Concurrency**: Asyncio-based asynchronous programming with 50 workers for handling multiple requests
- **Process Management**: Flask web server integration for deployment monitoring and uptime checks

## Authentication System
- **Multi-Bot Support**: Users can add multiple bots or userbots to their account
- **Session Management**: Support for both bot tokens and user session strings
- **Phone Authentication**: Direct phone number authentication for userbot setup
- **Access Control**: Owner-based permissions with configurable admin IDs

## Message Processing
- **Forward Engine**: Custom forwarding logic with source and target chat validation
- **FTM Mode**: Special forwarding mode that adds source link tracking and attribution
- **Filter System**: Comprehensive filtering by message type (text, photo, video, document, audio, voice, animation, sticker, poll)
- **Duplicate Detection**: MongoDB-based duplicate message tracking to prevent redundant forwards
- **Size Filtering**: File size limits and extension-based filtering capabilities

## Data Storage
- **Database**: MongoDB with Motor async driver for non-blocking database operations
- **Collections**: 
  - `users`: User data and ban status
  - `bots`: Bot configurations and credentials
  - `channels`: Channel/chat configurations
  - `notify`: Notification settings
- **Data Models**: Structured schemas for user management, bot storage, and channel tracking

## Configuration Management
- **Settings System**: Per-user configurable settings including filters, captions, buttons, and forwarding preferences
- **Environment Variables**: Centralized configuration through environment variables for API credentials
- **Dynamic Configuration**: Runtime configuration updates through inline keyboard interfaces

## User Interface
- **Command System**: Comprehensive command set including `/start`, `/forward`, `/settings`, `/broadcast`
- **Inline Keyboards**: Rich interactive menus for settings management and bot configuration
- **Callback Handlers**: Event-driven interface updates and setting modifications
- **Progress Tracking**: Real-time status updates during forwarding operations

## Administrative Features
- **Broadcast System**: Mass messaging to all bot users with delivery status tracking
- **System Monitoring**: Network speed testing and system resource monitoring
- **User Management**: Ban/unban capabilities and user statistics
- **Error Handling**: Comprehensive error catching with user-friendly error messages

# External Dependencies

## Telegram Services
- **Telegram Bot API**: Core bot functionality through official Telegram Bot API
- **Telegram Client API**: Direct client access for userbot functionality via Pyrogram
- **Bot Management**: Integration with @BotFather for bot token management

## Database Services
- **MongoDB**: Primary database for persistent data storage
- **Connection**: Motor async MongoDB driver for non-blocking database operations
- **Cloud Database**: Configured for MongoDB Atlas cloud database connectivity

## Python Libraries
- **Pyrogram/Pyrofork**: Telegram client library for bot and userbot functionality
- **Flask**: Web framework for deployment health checks and monitoring endpoints
- **Motor**: Async MongoDB driver for database operations
- **psutil**: System monitoring and resource tracking
- **speedtest-cli**: Network performance testing capabilities

## Deployment Infrastructure
- **Container Support**: Docker/container-ready with app.json configuration
- **Process Management**: Multi-threaded execution with Flask and bot running simultaneously
- **Environment Configuration**: Heroku/cloud platform compatible with environment variable configuration
- **Port Management**: Dynamic port allocation for web server component

## Security Dependencies
- **TgCrypto**: Telegram encryption library for secure message handling
- **cryptg**: Additional cryptography support for Telegram operations
- **Access Control**: Role-based permissions and user validation systems
