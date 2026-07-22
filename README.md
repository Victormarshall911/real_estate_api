# ⚙️ LandMarket API Engine — Backend REST Infrastructure

[![Django](https://img.shields.io/badge/Django-5.x-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Django REST Framework](https://img.shields.io/badge/DRF-3.15-ff1709?logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16.x-316192?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Daphne](https://img.shields.io/badge/ASGI-Daphne-0B3C5D?logo=django&logoColor=white)](https://github.com/django/daphne)
[![Render Deployment](https://img.shields.io/badge/Deployed_on-Render-46E3B7?logo=render&logoColor=black)](https://real-estate-api-orbx.onrender.com)

**LandMarket API** is the core backend engine powering Nigeria's premier real estate, agent, and architectural marketplace. Built with **Django REST Framework** and **Django Channels**, it provides scalable, secure, and resilient endpoints handling role-based authentication, real-time WebSocket chat connections, identity verification, property directories, wallet escrows, and blogging modules.

🔌 **Live Production API Base URL**: [https://real-estate-api-orbx.onrender.com/api/v1/](https://real-estate-api-orbx.onrender.com/api/v1/)  
🌐 **Client Frontend SPA**: [https://landmarketnig.vercel.app](https://landmarketnig.vercel.app)

---

## 🏗️ Architectural Highlights

### 🔐 Multi-Role Authentication & Security
- **JWT Authentication**: Powered by `djangorestframework-simplejwt` with short-lived access tokens and refresh mechanisms.
- **Role-Based Access Control (RBAC)**: Custom model roles distinguishing between `buyer`, `realtor`, `architect`, `agent`, `landlord`, and `developer` workflows.

### 💬 Real-Time WebSockets (ASGI / Channels)
- **Stateful Connections**: Async WebSocket consumers built on `channels` and `daphne` to handle instant chat messaging.
- **Query String Authentication**: WebSocket connections authenticate token-based sessions directly via URL query params.

### 🛡️ Identity Verification (KYC)
- **Dojah Integration**: Real-time identification check API validating BVN (Bank Verification Number) and NIN (National Identification Number).
- **Webhooks Listener**: Receives asynchronous verification success/failure webhooks directly from Dojah.

### 💰 Virtual Escrow Wallet Engine
- **Milestone Escrows**: Secure payment holding module. Connections fees or property transactions are deducted from the buyer's wallet and held in escrow.
- **Milestone Dispute & Release**: Standard dispute filing and validation logic allowing users to resolve or release milestone funds.

### 📐 Property listings directory
- **Multi-Owner Listings**: Unified property creation schema supporting Realtors, Landlords, Developers, and certified Architects.
- **View Deduplication**: Custom property view tracking logic to filter unique view count increments by IP per hour.

### 📰 Blog Engine
- **Auto-Read Time**: Custom tag, category, and markdown parsing that auto-calculates article read time.
- **Role Permissions**: Staff, admins, and authenticated realtors can manage and publish drafts.

---

## 📡 Core API Modules (`/api/v1/`)

| Endpoint Prefix | Description | Key Features / Methods |
| :--- | :--- | :--- |
| `/auth/` | Authentication, registrations, profile completions, and details | `POST /login/`, `GET /profile/`, `PATCH /complete-profile/` |
| `/properties/` | Property listings catalog, views, state/LGA filtering, and creations | `GET /properties/`, `POST /properties/`, `POST /properties/<id>/images/` |
| `/agents/` | Agent profiles, locations coverage management, and connection setups | `GET /agents/profiles/`, `POST /agents/profiles/<id>/add_location/` |
| `/architects/` | Accredited architects directory, profile setups, and ratings | `GET /architects/profiles/`, `POST /architects/profiles/me/` |
| `/landlords/` | Private landlord directories, descriptions, and reviews | `GET /landlords/profiles/`, `POST /landlords/profiles/me/` |
| `/developers/` | Estate developers layout showcases and directories | `GET /developers/profiles/`, `POST /developers/profiles/me/` |
| `/wallets/` | Deposit modules, transaction logs, and balances | `GET /wallets/me/`, `POST /wallets/deposit/` |
| `/escrows/` | Property escrow contracts, releases, and dispute declarations | `POST /escrows/`, `POST /escrows/<id>/release/` |
| `/chat/` | Chat session details, message lists, and WebSocket routes | `GET /chat/sessions/`, `WS /ws/chat/<session_id>/` |
| `/blog/` | Public blog posts, category configurations, and dashboard draft editors | `GET /blog/posts/`, `POST /blog/posts/`, `GET /blog/categories/` |
| `/kyc/` | BVN/NIN identity check submissions and Webhook interfaces | `POST /kyc/initiate/`, `POST /kyc/webhook/` |

---

## 🛠️ Getting Started Locally

### Prerequisites
- **Python 3.10+**
- **SQLite** (or PostgreSQL/Neon for live operations)

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
```

### 4. Database Migrations
```bash
python manage.py migrate
```

### 5. Create Superuser (Admin Dashboard Access)
```bash
python manage.py createsuperuser
```

### 6. Run Development server (ASGI Daphne)
To enable full WebSocket support (chat), run the server using Daphne:
```bash
daphne -p 8002 config.asgi:application
```
API endpoints will be accessible at `http://localhost:8002/api/v1/`.

---

## 📁 Project Structure

```text
apps/
├── accounts/         # Custom user models, JWT tokens, & RBAC profiles
├── agents/           # Agent locations pricing, connections & completions
├── architects/       # Accredited architect profiles & reviews
├── blog/             # Categories, tags, & markdown draft posts
├── chat/             # Chat message models & WebSocket routing consumers
├── developers/       # Developer layouts & showcase listings
├── escrows/          # Payment holds, milestones & disputes
├── kyc/              # Dojah BVN/NIN verification services & webhooks
├── landlords/        # Landlord profiles & reviews
├── payments/         # Paystack transaction logging
├── properties/       # Property listings, image uploads & unique view counts
├── subscriptions/    # Listing plans & limitations
└── wallets/          # Wallet transactions & deposits
config/
├── asgi.py           # ASGI configuration (Daphne/Channels setup)
├── settings/         # Base, local, dev & production settings init
└── urls.py           # Global versioned route entries
```
