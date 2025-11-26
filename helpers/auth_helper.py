from datetime import datetime, timedelta
import ldap3
from config import LDAP_BASE_DN, LDAP_BIND_DN, LDAP_BIND_PASSWORD, LDAP_PORT, LDAP_SERVER, LDAP_USER_DN
from fastapi import HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from constants import TokenParams
import bcrypt
from helpers.exceptions import CREDENTIAL_EXCEPTION

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

#password verification
def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

#access token creation
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=TokenParams.ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, TokenParams.SECRETE_KEY, algorithm=TokenParams.ALGORITHM)
    return encoded_jwt

#decode access token
def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, TokenParams.SECRETE_KEY, algorithms=[TokenParams.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

#token extration
def extract_token_from_cookies(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing in cookies")
    return token

#jwt verification
def verify_jwt(token: str) -> bool:
    isTokenValid: bool = False
    try:
        payload = jwt.decode(token, TokenParams.SECRETE_KEY, algorithms=[TokenParams.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except JWTError:
        raise CREDENTIAL_EXCEPTION
    if payload:
        isTokenValid = True
    return isTokenValid

#ldap connection
def connect_to_ldap():
    try:
        server = ldap3.Server(LDAP_SERVER, port=LDAP_PORT, get_info=ldap3.ALL)
        connection = ldap3.Connection(server, user=LDAP_BIND_DN, password=LDAP_BIND_PASSWORD)
        if not connection.bind():
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to bind to the LDAP server: {connection.last_error}")
        return connection
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error connecting to LDAP: {e}")

#ldap authentication
def authenticate_user_ldap(username: str, password: str) -> bool:
    try:
        connection = connect_to_ldap()
        if connection is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No connection to LDAP server.")

        user_dn = f"uid={username},{LDAP_USER_DN},{LDAP_BASE_DN}"
        user_connection = ldap3.Connection(connection.server, user=user_dn, password=password)
        if user_connection.bind():
            user_connection.unbind()
            return True
        else:
            user_connection.unbind()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error during authentication: {e}")

#authenticate username
def authenticate_username(username: str) -> bool:
    try:
        connection = connect_to_ldap()
        if connection is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No connection to LDAP server.")

        search_filter = f"(uid={username})"
        connection.search(
            search_base=f"{LDAP_USER_DN},{LDAP_BASE_DN}",
            search_filter=search_filter,
            attributes=["uid"]
        )

        if connection.entries:
            return True
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Username not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error during username validation: {e}")

#user creation
def create_user(username: str, password: str) -> bool:
    try:
        connection = connect_to_ldap()
        if connection is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No connection to LDAP server.")

        base_dn = LDAP_BASE_DN
        ou_dn = f"ou=users,{base_dn}"

        user_dn = f"uid={username},{ou_dn}"
        if connection.search(ou_dn, f"(uid={username})", search_scope=ldap3.SUBTREE):
            connection.unbind()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")  

        attributes = {
            "objectClass": ["top", "person", "organizationalPerson", "inetOrgPerson"],
            "uid": username,
            "cn": username,
            "sn": "user",
            "userPassword": password,
            "mail": f"{username}@cybotronics.com",
        }

        if connection.add(user_dn, attributes=attributes):
            connection.unbind()
            return True
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create user: {connection.last_error}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error during user creation: {e}")
