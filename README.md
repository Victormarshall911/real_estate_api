# ⚙️ LandMarket API Engine — Backend REST Infrastructure

[![Django](https://img.shields.io/badge/Django-5.x-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Django REST Framework](https://img.shields.io/badge/DRF-3.15-ff1709?logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16.x-316192?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Cloudinary](https://img.shields.io/badge/Cloudinary-Media_Storage-3448C5?logo=cloudinary&logoColor=white)](https://cloudinary.com/)
[![Render Deployment](https://img.shields.io/badge/Deployed_on-Render-46E3B7?logo=render&logoColor=black)](https://real-estate-api-orbx.onrender.com)

**LandMarket API** is the core backend service powering Nigeria's premier real estate, agent, and architectural marketplace. Built with **Django REST Framework**, it provides scalable, secure, and resilient endpoints handling role-based authentication, property directory listing management, real estate agent portfolios, architect showcase directories, and media management.

🔌 **Live Production API Base URL**: [https://real-estate-api-orbx.onrender.com/api/v1/](https://real-estate-api-orbx.onrender.com/api/v1/)  
🌐 **Client Frontend SPA**: [https://landmarketnig.vercel.app](https://landmarketnig.vercel.app)

---

## 🏗️ Architectural Highlights

### 🔐 Multi-Role Authentication & Security
- **JWT Authentication**: Powered by `djangorestframework-simplejwt` with short-lived access tokens and refresh mechanisms.
- **Role-Based Access Control (RBAC)**: Custom model roles distinguishing between `buyer`, `realtor`, `architect`, and `agent` workflows.
- **Dynamic CORS & CSRF Protection**: Configured with regex origin allowances supporting dynamic preview environments and production vercel domains.

### 📐 Directory & Profiles Ecosystem
- **Architects & Urban Planners Engine**: Endpoints for studio onboarding, portfolio URLs, WhatsApp consultation formatting, and automated completion tagging.
- **Realtor & Agent Directories**: Optimized queryset retrieval with serialized ratings, review aggregates, and location filtering.
- **Profile Management**: Dual serializers (`UserSerializer` & `UserUpdateSerializer`) ensuring read-only integrity while allowing authenticated user detail updates and profile picture persistence.

### ☁️ Persistent Media Storage
- **Cloudinary Integration**: Automatic media routing via `django-cloudinary-storage`. Uploaded profile photos, architectural blueprints, and property images are automatically stored on Cloudinary's CDN, ensuring 100% persistence across serverless container restarts.
- **Absolute URI Resolution**: Serializer method fields guarantee absolute URLs across all endpoints whether running on local disk storage or cloud CDNs.

---

## 📡 Core API Modules (`/api/v1/`)

| Endpoint Prefix | Description | Key Methods |
| :--- | :--- | :--- |
| `/auth/` | Authentication, JWT tokens, account registration & profile edits | `POST /login/`, `GET/PATCH /profile/`, `PATCH /complete-profile/` |
| `/properties/` | Property listings catalog, filtering, search & creation | `GET /properties/`, `GET /properties/<id>/` |
| `/architects/` | Nigerian architects & planners directory, reviews & profile creation | `GET /architects/`, `POST /architects/me/` |
| `/agents/` | Real estate field agents catalog and verification status | `GET /agents/` |
| `/realtors/` | Professional real estate agencies and portfolio management | `GET /realtors/` |
| `/kyc/` | Identity verification and KYC document submission workflows | `POST /kyc/submit/` |

---

## 🛠️ Getting Started Locally

### Prerequisites
- **Python 3.10+**
- **PostgreSQL** (or SQLite for local development)

### 1. Clone & Virtual Environment Setup
```bash
git clone https://github.com/Victormarshall911/real_estate_api.git
cd real_estate_api
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration (`.env`)
Create a `.env` file in the project root:
```env
DEBUG=True
SECRET_KEY=your-development-secret-key
DATABASE_URL=sqlite:///db.sqlite3
FRONTEND_URL=http://localhost:5173

# Optional: Cloudinary Storage for local media upload testing
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### 4. Database Migrations
```bash
python manage.py migrate
```

### 5. Create Superuser (Admin Dashboard)
```bash
python manage.py createsuperuser
```

### 6. Run Development Server
```bash
python manage.py runserver 0.0.0.0:8000
```
API endpoints will be accessible at `http://localhost:8000/api/v1/`.

---

## 📁 Project Structure

```text
real_estate_api/
├── apps/
│   ├── accounts/       # User models, authentication, JWT views & profile update serializers
│   ├── agents/         # Agent profiles & directory views
│   ├── architects/     # Architect models, serializers & review engines
│   ├── properties/     # Real estate listing models & filtering viewsets
│   ├── realtors/       # Realtor agency profiles & ratings
│   └── wallets/        # User wallet & financial transaction tracking
├── config/
│   ├── settings/       # Split settings (base.py, dev.py, prod.py)
│   ├── urls.py         # Global route dispatcher & media serving fallback
│   └── wsgi.py         # WSGI server configuration for Render deployment
├── manage.py
└── requirements.txt
```

---

## 📄 License

Proprietary backend system for **LandMarket Nigeria**. All rights reserved.
