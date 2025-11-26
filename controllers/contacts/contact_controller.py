from typing import List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import ldap3
from pydantic import BaseModel, EmailStr
from config import LDAP_BASE_DN
from helpers.auth_helper import connect_to_ldap
from helpers.contact_helper import create_contact, get_all_contacts, update_contact_device_id_by_email
from helpers.notification_helper import get_db_connection
from models.contacts import Contact, CreateContactRequest, EmailRequest, UpdateContactRequest

router = APIRouter(
    prefix="/contacts",
    tags=["Contacts Controller"]
)

@router.post("/create-contact")
async def create_contact_endpoint(request: CreateContactRequest, request1: Request):
    try:
        if create_contact(request.username, request.email, request.Division):
            return JSONResponse(content={"message": f"Contact {request.username} created successfully."}, status_code=200)
        else:
            raise HTTPException(status_code=500, detail="Failed to create contact.")
    except Exception as e:
        print(f"Error in create-contact API: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

@router.delete("/delete-contact/{username}")
async def delete_contact(username: str, request: Request):
    try:
        connection = connect_to_ldap()
        if connection is None:
            raise HTTPException(status_code=500, detail="Failed to connect to LDAP server.")
        
        contact_dn = f"cn={username},ou=contacts,{LDAP_BASE_DN}"
        
        if not connection.search(contact_dn, '(objectClass=*)', search_scope=ldap3.BASE):
            raise HTTPException(status_code=404, detail=f"Contact {username} not found.")
        
        if connection.delete(contact_dn):
            print(f"Contact {username} deleted successfully.")
            connection.unbind()
            return JSONResponse(content={"message": f"Contact {username} deleted successfully."}, status_code=200)
        else:
            raise HTTPException(status_code=500, detail="Failed to delete contact.")
        
    except Exception as e:
        print(f"Error in delete-contact API: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

@router.put("/update-device-id-by-email/{email}")
async def update_contact_device_id_by_email_endpoint(email: EmailStr, request: UpdateContactRequest, request1: Request):
    try:
        if update_contact_device_id_by_email(email, request.device_id):
            return JSONResponse(
                content={"message": f"Device ID updated successfully for contact {email}"},
                status_code=200
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to update device ID"
            )
    except Exception as e:
        print(f"Error in update-device-id-by-email API: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing the request."
        )

@router.get("/all", response_model=List[Contact])
async def get_all_contacts_endpoint(request: Request):
    try:
        contacts = get_all_contacts()
        conn = get_db_connection()
        cursor = conn.cursor()

        if contacts:
            for contact in contacts:
                cursor.execute(
                    "SELECT device_type FROM devices WHERE device_id = %s LIMIT 1", 
                    (contact.device_id,)
                )
                device = cursor.fetchone()

                if device:
                    contact.device_type = device[0]  
                else:
                    contact.device_type = "Unknown"  

            return contacts
        else:
            return []

    except Exception as e:
        print(f"Error in get-all-contacts API: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while fetching contacts."
        )

    except Exception as e:
        print(f"Error in get-all-contacts API: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while fetching contacts."
        )


@router.post("/verify_email")
async def verify_email(request: EmailRequest):
    email = request.email
    connection = connect_to_ldap()
    
    if connection is None:
        raise HTTPException(status_code=500, detail="No connection to LDAP server.")
    
    search_filter = f"(mail={email})"
    print(f"Searching LDAP with filter: {search_filter}")
    
    if not connection.search(LDAP_BASE_DN, search_filter, search_scope=ldap3.SUBTREE):
        connection.unbind()
        raise HTTPException(status_code=404, detail=f"Contact with email {email} not found.")
    
    if len(connection.entries) == 0:
        connection.unbind()
        raise HTTPException(status_code=404, detail=f"No entries returned for email {email}.")
    
    contact_dn = connection.entries[0].entry_dn
    print(f"Found contact DN: {contact_dn}")
    connection.unbind()
    
    return {"message": f"Email {email} exists in LDAP.", "contact_dn": contact_dn}