# 🤖 FlowAI — AI WhatsApp Receptionist & Business Automation

A Python/Flask-based AI business automation platform designed to help businesses manage customer conversations, appointments, services, payments, and business information through automated workflows.

## 🚀 Overview

FlowAI is an ongoing SaaS project focused on solving everyday business problems through AI and automation.

The system combines an AI conversational layer with business management features so that businesses can handle customer interactions while keeping important information such as customers, appointments, services, conversations, and payments organized.

The project is being developed with a focus on practical business use cases and scalable SaaS architecture.

---

## ✨ Current Capabilities

### 💬 AI Customer Conversations

* AI-powered customer responses
* Conversation history and memory
* Business-specific AI prompts
* Customer identity and conversation tracking
* Business knowledge storage for frequently asked questions

### 📱 WhatsApp Integration

* WhatsApp messaging workflows
* Incoming customer message handling
* Automated AI responses
* Customer conversation storage

### 📅 Appointment Management

* Customer appointment records
* Services associated with appointments
* Appointment time and status
* Customer contact information

### 🛍️ Business Services

Businesses can manage service information including:

* Service name
* Category
* Price
* Duration
* Deposit
* Availability
* Service images

### 👥 Customer Management

The system maintains customer records associated with individual businesses, including customer names and phone numbers.

### 💳 M-Pesa Integration

The project includes integration with the **Safaricom Daraja API** for M-Pesa payments.

Current implementation includes:

* Access-token generation
* STK Push requests
* Payment amount and phone-number handling
* Payment callback configuration
* M-Pesa receipt and payment status storage

### 📊 Business Dashboard & Analytics

The application includes business-focused dashboard functionality and analytics around:

* Appointments
* Services
* Payments
* Customer activity

### 🔐 Multi-Business SaaS Architecture

The application is structured around individual business accounts, allowing business-specific data such as customers, services, appointments, conversations, payments, and knowledge to be associated with a business.

---

## 🧠 AI Architecture

The AI service sends conversation messages to an LLM API and returns the generated response to the application.

Current implementation uses **OpenRouter** with an OpenAI-compatible chat-completions endpoint.

High-level flow:

```text
Customer
   ↓
WhatsApp
   ↓
Flask Application
   ↓
Conversation & Business Context
   ↓
LLM API
   ↓
AI Response
   ↓
WhatsApp
   ↓
Customer
```

---

## 🏗️ Application Architecture

The project uses a modular Flask structure with separate route modules for major areas of the application.

```text
FlowAI
│
├── app.py
├── models.py
├── services.py
├── routes/
│   ├── auth
│   ├── dashboard
│   ├── services
│   ├── appointments
│   ├── customers
│   ├── payments
│   └── whatsapp
│
├── brain/
├── templates/
├── static/
├── requirements.txt
└── Procfile
```

This structure separates application concerns and makes the project easier to extend as new business automation features are added.

---

## 🛠️ Technology Stack

**Backend**

* Python
* Flask
* Flask-SQLAlchemy

**AI**

* LLM APIs
* OpenRouter
* OpenAI-compatible chat completion API

**Communication**

* WhatsApp
* Twilio APIs

**Payments**

* Safaricom Daraja API
* M-Pesa STK Push

**Frontend**

* HTML
* CSS
* JavaScript
* Tailwind CSS

**Database**

* SQLite for local development
* PostgreSQL-compatible database configuration for deployment

**Deployment**

* Render
* Procfile-based deployment

---

## 📁 Project Structure

### `app.py`

Main Flask application responsible for application configuration, database initialization, blueprint registration, and application-level routes.

### `models.py`

Defines database models for:

* Businesses
* Customers
* Services
* Appointments
* Payments
* Conversations
* Business knowledge

### `services.py`

Contains reusable service logic including:

* M-Pesa authentication
* M-Pesa STK Push
* LLM API requests
* Application service functions

### `routes/`

Contains modular Flask blueprints for authentication, dashboard functionality, services, appointments, customers, payments, and WhatsApp workflows.

---

## 🔐 Environment Variables

Sensitive credentials should be stored as environment variables rather than committed to GitHub.

Examples include:

```text
SECRET_KEY
DATABASE_URL
OPENROUTER_API_KEY
MPESA_CONSUMER_KEY
MPESA_CONSUMER_SECRET
MPESA_SHORTCODE
MPESA_PASSKEY
CALLBACK_URL
```

Never commit real API keys, passwords, payment credentials, or other secrets to the repository.

---

## 🎯 Project Goal

FlowAI is being developed as a practical SaaS product for businesses that want to automate customer communication and repetitive business workflows.

The longer-term goal is to make it easier for businesses to:

**Receive enquiries → understand customers → answer questions → manage bookings → process payments → organize customer information**

through one connected system.

---

## 👩🏽‍💻 Developer

**Rachael Wanja Maara**

AI Automation & Python Developer
Nairobi, Kenya

I am a self-taught developer focused on building AI-powered business automation systems using Python, APIs, LLMs, WhatsApp integrations, and SaaS architecture.

GitHub:
https://github.com/rachaelwanja

---

## 🚧 Project Status

**Active development**

FlowAI is an evolving project. Features, architecture, integrations, and workflows continue to be improved as the platform develops toward production-ready SaaS use cases.

---

## 📌 What This Project Demonstrates

This project demonstrates hands-on experience with:

* Python backend development
* Flask application architecture
* REST/API integrations
* LLM integration
* WhatsApp automation
* Webhooks
* Database modeling
* SaaS architecture
* M-Pesa payment integration
* Authentication
* Customer management
* Appointment workflows
* Cloud deployment
* Building software around real business problems
