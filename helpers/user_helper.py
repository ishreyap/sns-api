from constants import TokenParams
from jose import jwt

def get_username(token = str):
    payload = jwt.decode(token, TokenParams.SECRETE_KEY, algorithms=[TokenParams.ALGORITHM])
    
    username = payload.get("sub")
    return username