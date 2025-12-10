from fastapi import APIRouter, Depends, Request, Response, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import quote, unquote
import secrets
from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.middleware.sessions import SessionMiddleware
from starlette.config import Config
from flaat import access_tokens



from ...core.config import settings
from ...db.session import get_async_db
from ...core.logging_config import logger
from ...crud.user import crud_user
from ...schemas.user import UserCreate
from ...web.templating import templates

router = APIRouter()

# Configure OAuth with providers from settings
oauth = OAuth()
providers = []

for provider_name, provider in settings.OIDC_PROVIDERS.items():
    provider_url = provider["url"]

    client_id = provider["client_id"]
    client_secret = provider["client_secret"]

    if client_id and client_secret:
        oauth.register(
            name=provider_name,
            server_metadata_url=f"{provider_url}/.well-known/openid-configuration",
            client_id=client_id,
            client_secret=client_secret,
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        providers.append(provider_name)

# # Generate a random secret key for session encryption
# SECRET_KEY = getattr(settings, "SECRET_KEY", secrets.token_urlsafe(32))

@router.get("/auth/login")
async def login(request: Request, next: Optional[str] = Query(None)):
    """
    Handle login requests. Shows available identity providers.
    """
    redirect_after_login = next or "/"
    encoded_redirect = quote(redirect_after_login)
    
    providers_html = ""
    for provider_name in providers:
        auth_url = f"/api/v1/auth/authorize/{provider_name}?next={encoded_redirect}"
        providers_html += f'<a href="{auth_url}" class="provider-button">{provider_name}</a><br>'
    
    # TODO Add a better HTML template for login page
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

@router.get("/auth/authorize/{provider}")
async def authorize(request: Request, provider: str, next: Optional[str] = Query("/")):
    """Initiate authentication flow with selected provider"""
    redirect_uri = f"{settings.PUBLIC_BASE_URL}/api/v1/auth/callback/{provider}"
    
    # Store the post-login redirect URL in session
    request.session['next_url'] = next
    
    client = oauth.create_client(provider)
    if not client:
        return HTMLResponse(content=f"<h1>Provider '{provider}' not configured</h1>", status_code=400)
    
    return await client.authorize_redirect(request, redirect_uri)

@router.get("/auth/callback/{provider}")
async def oidc_callback(
    request: Request, 
    provider: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Handle the OIDC callback after user authentication.
    """
    try:
        client = oauth.create_client(provider)
        token_response = await client.authorize_access_token(request)
        id_token = token_response.get("id_token")

        if not id_token:
            logger.error("Missing ID token")
            return HTMLResponse(content="<html><body><h1>Authentication Error</h1><p>Missing ID token</p></body></html>")

        claims = access_tokens.get_access_token_info(id_token, verify=False) # TODO Do not forget to turn this on in production
        sub = claims.body.get("sub")
        iss = claims.body.get("iss")

        if not sub or not iss:
            logger.error("Missing required claims in token")
            return HTMLResponse(content="<html><body><h1>Authentication Error</h1><p>Missing required user information</p></body></html>")
        
        # Create or update user
        user = await crud_user.get_by_sub_and_iss(db, sub=sub, iss=iss)
        if not user:
            user = await crud_user.create(db, UserCreate(sub=sub, iss=iss))
        
        # Get the redirect URL from session
        redirect_url = request.session.get('next_url', '/')
        
        
        # Create response with redirect
        response = RedirectResponse(url=redirect_url)

        # response.set_cookie(
        #     key="id_token",
        #     value=id_token,
        #     httponly=True,
        #     secure=settings.ENVIRONMENT == "production",
        #     max_age=300 # TODO Time for cookie expiration (consult for a better value)
        # ) # TODO change this to session cookie?!

        request.session["id_token"] = id_token 


        return response
        
    except OAuthError as error:
        logger.error(f"OAuth error: {error.error}")
        return HTMLResponse(
            content=f"<html><body><h1>Authentication Error</h1><p>{error.description}</p></body></html>",
            status_code=400
        )
    except Exception as e:
        logger.error(f"Error during OIDC callback: {e}", exc_info=True)
        return HTMLResponse(
            content="<html><body><h1>Authentication Error</h1><p>Could not process login. Please try again.</p></body></html>",
            status_code=400
        )


@router.get("/auth/logout")
async def logout(request: Request):
    """Log out the current user by clearing the session."""
    request.session.clear()
    return templates.TemplateResponse(
        "logout_success.html",
        {"request": request}
    )

# @router.get("/auth/logout")
# async def logout(request: Request):
#     """Log out the current user by clearing tokens and session."""
#     response = RedirectResponse(url="/")
    
#     # Clear cookies
#     response.delete_cookie(key="access_token")
#     response.delete_cookie(key="refresh_token")
#     response.delete_cookie(key="csrf_token")
    
#     # Clear session
#     request.session.clear()
    
#     return response

# @router.get("/auth/refresh")
# async def refresh_token(request: Request):
#     """Refresh the access token using a refresh token"""
#     refresh_token = request.cookies.get("refresh_token")
#     if not refresh_token:
#         return RedirectResponse(url="/api/v1/auth/login", status_code=303)
    
#     # Get provider from user session
#     if 'user' not in request.session or 'iss' not in request.session['user']:
#         return RedirectResponse(url="/api/v1/auth/login", status_code=303)
    
#     # Find provider by issuer
#     provider_name = None
#     for p in providers:
#         client = oauth.create_client(p)
#         if client and client.server_metadata_url.startswith(request.session['user']['iss']):
#             provider_name = p
#             break
    
#     if not provider_name:
#         logger.error("Could not find provider for token refresh")
#         return RedirectResponse(url="/api/v1/auth/login", status_code=303)
    
#     try:
#         # Use the refresh token to get a new access token
#         client = oauth.create_client(provider_name)
#         token = await client.refresh_token(refresh_token)
        
#         response = RedirectResponse(url="/", status_code=303)
        
#         # Update tokens in cookies
#         response.set_cookie(
#             key="access_token",
#             value=token['access_token'],
#             httponly=True,
#             secure=settings.ENVIRONMENT == "production",
#             max_age=token.get('expires_in', 3600)
#         )
        
#         if 'refresh_token' in token:
#             response.set_cookie(
#                 key="refresh_token",
#                 value=token['refresh_token'],
#                 httponly=True,
#                 secure=settings.ENVIRONMENT == "production",
#                 max_age=86400 * 30  # 30 days
#             )
        
#         return response
        
#     except Exception as e:
#         logger.error(f"Error refreshing token: {e}", exc_info=True)
#         return RedirectResponse(url="/api/v1/auth/login", status_code=303)