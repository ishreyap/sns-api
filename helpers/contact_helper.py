from typing import List
import ldap3
from config import LDAP_BASE_DN
from helpers.auth_helper import connect_to_ldap
from models.contacts import Contact

#contact creation
def create_contact(username: str, email: str, division: str) -> bool:
    try:
        connection = connect_to_ldap()
        if connection is None:
            print("No connection to LDAP server.")
            return False

        ou_dn = f"ou=contacts,{LDAP_BASE_DN}"
        
        if not connection.search(LDAP_BASE_DN, f"(ou=contacts)", search_scope=ldap3.SUBTREE):
            ou_attributes = {
                "objectClass": ["top", "organizationalUnit"],
                "ou": "contacts"
            }
            if not connection.add(ou_dn, attributes=ou_attributes):
                print(f"Failed to create 'ou=contacts': {connection.last_error}")
                connection.unbind()
                return False

        contact_dn = f"cn={username},{ou_dn}"
        
        attributes = {
            "objectClass": ["top", "inetOrgPerson"],
            "cn": username,
            "sn": username,  
            "mail": email,
            "ou": division,  
        }

        if connection.add(contact_dn, attributes=attributes):
            print(f"Contact {username} created successfully.")
            connection.unbind()
            return True
        else:
            print(f"Failed to create contact {username}: {connection.last_error}")
            connection.unbind()
            return False
    except Exception as e:
        print(f"Error during contact creation: {e}")
        return False
    
# fetch all contacts
def get_all_contacts() -> List[Contact]:
    try:
        connection = connect_to_ldap()
        if connection is None:
            print("No connection to LDAP server.")
            return []

        ou_dn = f"ou=contacts,{LDAP_BASE_DN}"
        
        search_filter = "(objectClass=inetOrgPerson)"
        attributes = ['cn', 'mail', 'ou', 'employeeNumber']
        
        if not connection.search(
            ou_dn,
            search_filter,
            attributes=attributes,
            search_scope=ldap3.SUBTREE
        ):
            print("No contacts found or search failed")
            connection.unbind()
            return []

        contacts = []
        for entry in connection.entries:
            try:
                device_id = str(entry.employeeNumber) if hasattr(entry, 'employeeNumber') else None
                
                contact = Contact(
                    username=str(entry.cn),
                    email=str(entry.mail),
                    Division=str(entry.ou),
                    device_id=device_id
                )
                contacts.append(contact)
            except Exception as e:
                print(f"Error processing contact entry: {e}")
                continue

        connection.unbind()
        return contacts

    except Exception as e:
        print(f"Error fetching contacts: {e}")
        return []
    
#update contact
def update_contact_device_id_by_email(email: str, device_id: str) -> bool:
    try:
        connection = connect_to_ldap()
        if connection is None:
            print("No connection to LDAP server.")
            return False

        search_filter = f"(mail={email})"
        print(f"Searching LDAP with filter: {search_filter}")
        
        if not connection.search(LDAP_BASE_DN, search_filter, search_scope=ldap3.SUBTREE):
            print(f"Contact with email {email} not found. Last error: {connection.last_error}")
            connection.unbind()
            return False

        if len(connection.entries) == 0:
            print(f"No entries returned for email {email}. Check if the email format matches.")
            connection.unbind()
            return False

        contact_dn = connection.entries[0].entry_dn
        print(f"Found contact DN: {contact_dn}")

        changes = {
            'employeeNumber': [(ldap3.MODIFY_REPLACE, [device_id])]
        }

        if connection.modify(contact_dn, changes):
            print(f"Device ID updated successfully for {email}")
            connection.unbind()
            return True
        else:
            print(f"Failed to update device ID for {email}: {connection.last_error}")
            connection.unbind()
            return False

    except Exception as e:
        print(f"Error updating device ID by email: {e}")
        return False