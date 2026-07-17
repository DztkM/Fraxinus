# Internal File Gateway

## Getting Started

### 1. Environment Setup
Create your environment configuration file:
```bash
cp .env.example .env
```

### 2. Running the Application

You can run the application in either Production or Development mode.

#### Production Mode
To spin up the entire stack using Docker:
```bash
docker compose -f compose.yaml up -d
```

#### Development Mode
For local development with hot-reloading for the FastAPI backend:

1. Start the dependent services (Database, MinIO, etc.):
   ```bash
   docker compose -f compose.dev.yaml up -d
   ```
2. Setup `uv`:
   ```bash
   cd backend
   uv sync
   ```
3. Apply the latest database schemas using Alembic:
   ```bash
   uv run alembic upgrade head
   ```
4. Run the backend locally:
   ```bash
   uv run fastapi dev app/main.py 
   ```

---

## Useful Links
- **FastAPI Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **MinIO WebUI:** [http://127.0.0.1:9001/](http://127.0.0.1:9001/)

---

## Cleanup
To stop the services and remove volumes (**Warning:** this will erase your database and uploaded files!):
```bash
docker compose down -v 
```

---

## Setup Clerk (Authentication)

To use your own Clerk application for authentication, follow these steps:

### 1. Create a Project in Clerk
1. Go to the [Clerk Dashboard](https://dashboard.clerk.com/) and create a new application.
2. Select the authentication methods you want

### 2. Configure JWT Template
The backend expects a specific JWT structure. You need to create a JWT template:
1. In the Clerk Dashboard, go to **Configure > JWT Templates**.
2. Click **New Template** and select **Custom**.
3. Name the template **`backend`** (this exact name is required by `clerk_token/index.html` and the backend).
4. You can leave the default JSON structure. Save the template.

### 3. Create a Test User
1. Go to **Users** in the Clerk Dashboard.
2. Click **Create User** and fill in the details.

### 4. Update the Project with Your Keys
You need to update the application to use your new Clerk project:

1. In the Clerk Dashboard, go to **API Keys**.
2. Copy your **Publishable Key** (starts with `pk_test_`).
3. Copy your **Frontend API URL** (e.g., `https://your-app-123.clerk.accounts.dev`).

**Frontend / HTML Token Tool:**
Open `clerk_token/index.html` and update the keys in the `<script>` tags:
- Replace `data-clerk-publishable-key` with your new Publishable Key.
- Replace the script `src` URLs to point to your new Frontend API URL. For example:
  `src="https://<YOUR_FRONTEND_API_URL>/npm/@clerk/clerk-js@6/dist/clerk.browser.js"`

**Backend:**
Open `backend/app/core/auth.py` and update the constants:
- Replace `CLERK_FRONTEND_API` with your new Frontend API URL.
- Replace `JWKS_URL` with your new JWKS URL (e.g., `https://<YOUR_FRONTEND_API_URL>/.well-known/jwks.json`).

### 5. Getting a Clerk JWT Token for Testing
To test endpoints that require authentication, you can use the provided HTML tool to generate a valid JWT token.

1. Open the file `clerk_token/index.html` in your web browser.
2. Click **Login** and authenticate with the test user you created.
3. Once authenticated, click **Get JWT**.
4. The token will be displayed on the screen. Click **Copy Token** to easily copy it to your clipboard.
5. If you need to test as a different user, click **Logout** and log in again.


## Testing Multipart Upload
To test multipart upload and file endpoints a test script is provided.

1. Start Docker containers (`compose.dev.yaml`) and the FastAPI backend.
2. Get a valid JWT token from Clerk.
3. Run the test script from the `backend` folder:
```bash
cd backend
uv run python scripts/test_upload.py "<YOUR_JWT_TOKEN>" "path/to/any/file.jpg" "[OPTIONAL]folder_id"
```
This script will:
- Contact `/api/files/upload/init` to create DB records and get pre-signed MinIO URLs for 5MB chunks.
- Upload each chunk directly to MinIO.
- Contact `/api/files/{file_id}/upload/complete` to finish the upload.

You can then view the uploaded files in the MinIO WebUI (credentials in `.env`) or test the download endpoint via Swagger (`http://localhost:8000/docs`).