from fastapi import APIRouter, Depends, Request, Response, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
import flaat
from urllib.parse import quote, unquote

from ...core.config import settings
from ...core.logging_config import logger
from ...db.session import get_db
from ...crud.user import crud_user
from ..dependencies import get_db_dependency

router = APIRouter()

# Configure FLAAT with your OIDC providers
oidc_config = {
    "client_id": settings.OIDC_CLIENT_ID,
    "client_secret": settings.OIDC_CLIENT_SECRET,
    "redirect_uri": f"{settings.PUBLIC_BASE_URL}/api/v1/auth/callback"
}

# Initialize FLAAT with your configuration
flaat_handler = flaat.Flaat()
flaat_handler.set_trusted_OP_list(settings.OIDC_PROVIDERS)
flaat_handler.set_client_id(oidc_config["client_id"])
flaat_handler.set_client_secret(oidc_config["client_secret"])
flaat_handler.set_redirect_uri(oidc_config["redirect_uri"])

@router.get("/auth/login")
async def login(request: Request, next: Optional[str] = Query(None)):
    """
    Handle login requests. Redirects to the IDP login page.
    Optionally takes a 'next' parameter for redirect after successful login.
    """
    logger.info("Login request received")
    
    # Store the next URL in session for later redirection after authentication
    redirect_after_login = next or "/"
    encoded_redirect = quote(redirect_after_login)
    
    # Generate login page with provider selection
    providers_html = ""
    for provider in settings.OIDC_PROVIDERS:
        auth_url = flaat_handler.get_login_url(request, provider, state=encoded_redirect)
        providers_html += f'<a href="{auth_url}" class="provider-button">{provider}</a><br>'
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; height: 100vh; }}
            .login-container {{ width: 400px; padding: 40px; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #333; }}
            .provider-button {{ display: block; width: 100%; padding: 10px; margin: 10px 0; text-align: center; background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 4px; text-decoration: none; color: #333; }}
            .provider-button:hover {{ background-color: #e9ecef; }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <h1>Select Login Provider</h1>
            {providers_html}
        </div>
    </body>
    </html>
    """)

@router.get("/auth/callback")
async def oidc_callback(
    request: Request, 
    code: str, 
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db_dependency())
):
    """
    Handle the OIDC callback after user authentication.
    Processes the authorization code and creates/updates the user.
    """
    try:
        # Exchange code for token and get user info
        user_info = await flaat_handler.get_user_info_from_code(request, code)
        
        # Extract important claims
        sub = user_info.get("sub")
        iss = user_info.get("iss")
        email = user_info.get("email")
        name = user_info.get("name", "")
        
        if not sub or not iss:
            logger.error("Missing required claims in token")
            return HTMLResponse(content="<html><body><h1>Authentication Error</h1><p>Missing required user information</p></body></html>")
        
        # Create or update user
        db_user = await crud_user.get_by_sub_and_iss(db, sub, iss)
        if not db_user:
            # Create new user
            from ...schemas.user import UserCreate
            user_create = UserCreate(
                sub=sub,
                iss=iss,
                email=email,
                name=name,
                is_active=True
            )
            db_user = await crud_user.create(db, obj_in=user_create)
        
        # Create session token
        session_token = flaat_handler.create_session_token(user_info)
        response = RedirectResponse(url="/")
        
        # If state contains a redirect URL, use it
        if state:
            try:
                redirect_url = unquote(state)
                response = RedirectResponse(url=redirect_url)
            except Exception as e:
                logger.error(f"Error decoding redirect URL: {e}")
        
        # Set session cookie
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session_token,
            httponly=True,
            secure=settings.ENVIRONMENT != "development",
            max_age=settings.SESSION_COOKIE_MAX_AGE
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error during OIDC callback: {e}")
        return HTMLResponse(
            content="<html><body><h1>Authentication Error</h1><p>Could not process login. Please try again.</p></body></html>",
            status_code=400
        )

@router.get("/auth/logout")
async def logout(response: Response):
    """Log out the current user by clearing the session cookie."""
    response = RedirectResponse(url="/")
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME)
    return response