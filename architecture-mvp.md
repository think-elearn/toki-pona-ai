# Toki Pona Learning Platform

## One-Week MVP Architecture Plan

## 1. Executive Summary

This document outlines a streamlined architecture for a Django-based Toki Pona learning platform MVP, designed to be built by a single developer within one week. The MVP will integrate core functionalities from the existing listening, writing, and signing application prototypes into a cohesive web application deployable on Heroku or Fly.io.

## 2. MVP Scope

### 2.1 Core Features

- User authentication (signup, login, logout)
- Dashboard with access to all learning modules
- Simplified version of each learning module:
  - **Listening**: Basic audio playback and translation exercises
  - **Writing**: Simplified glyph recognition and drawing interface
  - **Signing**: Basic webcam capture and sign comparison
- Progress tracking

### 2.2 Scope Limitations

- No advanced analytics
- Limited personalization
- Focus on functionality over visual polish
- Basic error handling and user feedback

## 3. Technology Stack

### 3.1 Framework & Core

- **Django 4.2+**: Web framework with built-in templating
- **Python 3.9+**: Programming language
- **PostgreSQL**: Database (Heroku/Fly.io compatible)
- **Gunicorn**: WSGI server for production

### 3.2 Frontend

- **Django Templates**: Server-side rendering
- **Bootstrap 5**: CSS framework for responsive design
- **JavaScript (vanilla)**: For interactive components
- **HTML5 Canvas API**: For drawing functionality

### 3.3 Media & AI Components

- **MediaPipe**: For computer vision (hand tracking)
- **OpenAI API**: For text translation validation
- **MobileNetV3** (TensorFlow.js): For glyph recognition

### 3.4 Deployment

- **Heroku** or **Fly.io**: PaaS for hosting
- **WhiteNoise**: Static file serving
- **AWS S3** (optional): Media storage if needed

## 4. System Architecture

### 4.1 Django Project Structure

```text
toki-pona-ai/
├── manage.py
├── requirements.txt
├── Procfile                  # For Heroku deployment
├── runtime.txt               # Python version for deployment
├── fly.toml                  # For Fly.io deployment (if used)
├── config/                   # Project configuration
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/                     # Application directory
│   ├── __init__.py           # Make it a Python package
│   ├── accounts/             # User authentication app
│   ├── dashboard/            # Main dashboard app
│   ├── listening/            # Listening exercises app
│   ├── writing/              # Writing practice app
│   └── signing/              # Sign language app
├── static/                   # Global static files
│   ├── css/
│   ├── js/
│   └── images/
└── templates/                # Global templates
    ├── base.html
    └── ...
```

### 4.2 App Structure (example for each module)

```text
listening/
├── __init__.py
├── admin.py                  # Admin integration
├── apps.py
├── forms.py                  # Form definitions
├── migrations/               # Database migrations
├── models.py                 # Data models
├── services.py               # Business logic & AI integration
├── static/                   # App-specific static files
│   ├── listening/css/
│   ├── listening/js/
│   └── listening/audio/
├── templates/                # App-specific templates
│   └── listening/
│       ├── index.html
│       ├── exercise.html
│       └── ...
├── tests.py                  # Unit tests
├── urls.py                   # URL routing
└── views.py                  # View controllers
```

### 4.3 Data Models

**Core Models:**

```python
# accounts/models.py
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Add any user profile fields

# dashboard/models.py
class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    module = models.CharField(max_length=20)  # 'listening', 'writing', 'signing'
    activity = models.CharField(max_length=50)
    score = models.FloatField()
    completed = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now=True)
```

**Module-specific Models:**

```python
# listening/models.py
class TokiPonaPhrase(models.Model):
    text = models.CharField(max_length=200)
    translations = models.JSONField()  # Store multiple valid translations
    audio_file = models.FileField(upload_to='audio/', null=True, blank=True)

# writing/models.py
class Glyph(models.Model):
    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to='glyphs/')

# signing/models.py
class SignReference(models.Model):
    name = models.CharField(max_length=50)
    video = models.FileField(upload_to='signs/', null=True, blank=True)
    landmarks = models.JSONField(null=True)  # Store MediaPipe landmarks
```

## 5. Module Integration

### 5.1 Listening Module

- **Core Functionality**:
  - Audio playback of Toki Pona phrases
  - Text input for translation
  - Validation against multiple correct translations
  - Simple feedback on correctness

- **Implementation Approach**:
  - Port core audio functionality to Django template
  - Use HTML5 audio elements for playback
  - Implement server-side validation of translations
  - Store pre-recorded audio files

### 5.2 Writing Module

- **Core Functionality**:
  - Canvas drawing interface for Sitelen Pona glyphs
  - Recognition of drawn glyphs
  - Visual feedback on correctness

- **Implementation Approach**:
  - Implement drawing with HTML5 Canvas and JavaScript
  - Capture canvas data and send to backend for processing
  - Use TensorFlow.js for client-side recognition where possible
  - Simplify recognition to most common glyphs

### 5.3 Signing Module

- **Core Functionality**:
  - Webcam capture for sign language practice
  - Basic comparison with reference signs
  - Visual feedback on signing accuracy

- **Implementation Approach**:
  - Use MediaPipe via JavaScript for hand tracking
  - Implement simplified comparison algorithm
  - Focus on a small subset of signs for MVP

### 5.4 Dashboard & Navigation

- **Core Functionality**:
  - Central access point to all modules
  - Basic progress tracking
  - User account management

- **Implementation Approach**:
  - Simple Bootstrap-based navigation
  - Progress indicators for each module
  - Session-based activity tracking

## 6. Implementation Plan

### 6.1 Day 1: Project Setup & Core Framework

- Initialize Django project
- Set up database and models
- Create user authentication
- Implement base templates and styling
- Set up static file handling

### 6.2 Day 2-3: Listening Module

- Implement TokiPonaPhrase model and initial data
- Create audio playback interface
- Develop translation input and validation
- Build exercise completion tracking

### 6.3 Day 4-5: Writing Module

- Implement Glyph model and load reference images
- Create drawing canvas interface
- Develop basic glyph recognition service
- Build practice exercise flow

### 6.4 Day 6: Signing Module

- Set up webcam integration
- Implement basic MediaPipe hand tracking
- Create simplified sign comparison
- Build practice interface

### 6.5 Day 7: Integration & Deployment

- Finalize dashboard and navigation
- Implement cross-module progress tracking
- Final testing and bug fixes
- Deploy to Heroku/Fly.io

## 7. Technical Considerations

### 7.1 Performance Optimization

- Minify and compress static assets
- Optimize database queries with select_related/prefetch_related
- Lazy load JavaScript for module-specific functionality
- Use Django's caching framework for frequently accessed data

### 7.2 AI Components Simplification

- Pre-compute and store reference data where possible
- Use client-side processing for real-time features
- Limit AI functionality to core features
- Consider static references instead of dynamic processing

### 7.3 Deployment Preparation

- Configure PostgreSQL for production
- Set up environment variables for sensitive data
- Configure static file serving with WhiteNoise
- Create CI/CD pipeline for Heroku/Fly.io

## 8. Post-MVP Enhancements

### 8.1 Immediate Improvements

- Enhanced error handling
- User feedback mechanisms
- Additional exercises and content
- Improved UI/UX

### 8.2 Future Architecture Evolution

- Gradual migration to more sophisticated frontend (React)
- API refactoring for better separation of concerns
- Enhanced AI capabilities with dedicated services
- Improved analytics and personalization

## 9. Implementation Checklist

### 9.1 Project Initialization

- [ ] Create Django project
- [ ] Configure database
- [ ] Set up authentication
- [ ] Create base templates

### 9.2 Core Modules

- [ ] Implement dashboard app
- [ ] Implement listening app
- [ ] Implement writing app
- [ ] Implement signing app

### 9.3 Deployment

- [ ] Configure static file serving
- [ ] Set up environment variables
- [ ] Create deployment configuration
- [ ] Deploy to Heroku/Fly.io

## 10. Conclusion

This architecture plan provides a focused approach for developing a Toki Pona learning platform MVP in one week using Django. By leveraging Django's built-in features and simplifying the AI components, the plan balances functionality with development speed. The resulting MVP will provide a foundation for future enhancements while delivering immediate value to users.
