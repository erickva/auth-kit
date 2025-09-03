"""
Passkey service for WebAuthn operations
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import base64
import json
import logging

from sqlalchemy.orm import Session
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json
)
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    AuthenticatorTransport,
    UserVerificationRequirement,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    AuthenticatorAttachment,
    RegistrationCredential,
    AuthenticationCredential
)

from ..models.user import BaseUser, UserCredential
from ..core.events import auth_events
from ..config import AuthConfig

logger = logging.getLogger(__name__)


class PasskeyService:
    """
    Service for passkey/WebAuthn operations
    
    Handles:
    - Passkey registration
    - Passkey authentication
    - Credential management
    """
    
    def __init__(self, db: Session, config: AuthConfig):
        """
        Initialize passkey service
        
        Args:
            db: Database session
            config: Authentication configuration
        """
        self.db = db
        self.config = config
        
    def get_user_credentials(
        self,
        user_id: UUID
    ) -> List[UserCredential]:
        """
        Get all user credentials
        
        Args:
            user_id: User ID
            
        Returns:
            List of user credentials
        """
        return self.db.query(UserCredential).filter(
            UserCredential.user_id == user_id
        ).all()
        
    def get_credential(
        self,
        credential_id: str
    ) -> Optional[UserCredential]:
        """
        Get credential by ID
        
        Args:
            credential_id: Credential ID (base64)
            
        Returns:
            Credential or None
        """
        return self.db.query(UserCredential).filter(
            UserCredential.credential_id == credential_id
        ).first()
        
    def get_credential_by_uuid(
        self,
        uuid: UUID,
        user_id: UUID
    ) -> Optional[UserCredential]:
        """
        Get credential by UUID and user ID
        
        Args:
            uuid: Credential UUID
            user_id: User ID
            
        Returns:
            Credential or None
        """
        return self.db.query(UserCredential).filter(
            UserCredential.id == uuid,
            UserCredential.user_id == user_id
        ).first()
        
    async def begin_registration(
        self,
        user: BaseUser,
        credential_name: str
    ) -> Dict[str, Any]:
        """
        Begin passkey registration
        
        Args:
            user: User object
            credential_name: Name for the credential
            
        Returns:
            Registration options as dict
        """
        # Get existing credentials to exclude
        existing_credentials = self.get_user_credentials(user.id)
        exclude_credentials = []
        
        for cred in existing_credentials:
            try:
                # Decode credential ID
                credential_id_bytes = base64.urlsafe_b64decode(cred.credential_id + "==")
                exclude_credentials.append(
                    PublicKeyCredentialDescriptor(
                        id=credential_id_bytes,
                        transports=[AuthenticatorTransport.INTERNAL, AuthenticatorTransport.USB]
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to decode credential {cred.id}: {e}")
                
        # Generate registration options
        options = generate_registration_options(
            rp_id=self.config.passkey_rp_id,
            rp_name=self.config.passkey_rp_name,
            user_id=str(user.id).encode(),
            user_name=user.email,
            user_display_name=user.display_name,
            exclude_credentials=exclude_credentials,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED
            ),
            timeout=self.config.passkey_timeout_ms
        )
        
        # Convert to JSON-serializable format
        options_dict = json.loads(options_to_json(options))
        
        # Store challenge for verification
        # In production, use Redis or similar for challenge storage
        options_dict['_challenge'] = base64.b64encode(options.challenge).decode()
        
        return options_dict
        
    async def complete_registration(
        self,
        user: BaseUser,
        credential_name: str,
        registration_response: Dict[str, Any],
        expected_challenge: str
    ) -> UserCredential:
        """
        Complete passkey registration
        
        Args:
            user: User object
            credential_name: Name for the credential
            registration_response: Registration response from client
            expected_challenge: Expected challenge (base64)
            
        Returns:
            Created credential
            
        Raises:
            ValueError: If registration verification fails
        """
        try:
            # Decode challenge
            expected_challenge_bytes = base64.b64decode(expected_challenge)
            
            # Create credential object from response
            credential = RegistrationCredential(
                id=registration_response['id'],
                raw_id=registration_response['rawId'],
                response=registration_response['response'],
                authenticator_attachment=registration_response.get('authenticatorAttachment'),
                client_extension_results=registration_response.get('clientExtensionResults', {}),
                type=registration_response['type']
            )
            
            # Verify registration
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=expected_challenge_bytes,
                expected_origin=self.config.passkey_origin,
                expected_rp_id=self.config.passkey_rp_id
            )
            
            if not verification.verified:
                raise ValueError("Registration verification failed")
                
        except Exception as e:
            logger.error(f"Registration verification failed: {e}")
            raise ValueError(f"Registration verification failed: {str(e)}")
            
        # Save credential
        credential_record = UserCredential(
            user_id=user.id,
            credential_id=base64.b64encode(verification.credential_id).decode(),
            public_key=base64.b64encode(verification.credential_public_key).decode(),
            sign_count=verification.sign_count,
            name=credential_name,
            authenticator_type="platform" if registration_response.get('authenticatorAttachment') == "platform" else "cross-platform",
            is_discoverable=True  # Modern passkeys are discoverable
        )
        
        self.db.add(credential_record)
        self.db.commit()
        self.db.refresh(credential_record)
        
        # Emit event
        await auth_events.emit("passkey_registered", {
            "user_id": str(user.id),
            "passkey_id": str(credential_record.id),
            "passkey_name": credential_name
        })
        
        return credential_record
        
    async def begin_authentication(
        self,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Begin passkey authentication
        
        Args:
            user_email: Optional user email for conditional UI
            
        Returns:
            Authentication options as dict
        """
        allow_credentials = []
        
        if user_email:
            # Find user by email
            user = self.db.query(self.config.user_model).filter(
                BaseUser.email == user_email
            ).first()
            
            if user:
                # Get user's credentials
                credentials = self.get_user_credentials(user.id)
                
                for cred in credentials:
                    try:
                        credential_id_bytes = base64.urlsafe_b64decode(cred.credential_id + "==")
                        allow_credentials.append(
                            PublicKeyCredentialDescriptor(
                                id=credential_id_bytes,
                                transports=[AuthenticatorTransport.INTERNAL, AuthenticatorTransport.USB]
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Failed to decode credential {cred.id}: {e}")
                        
        # Generate authentication options
        options = generate_authentication_options(
            rp_id=self.config.passkey_rp_id,
            allow_credentials=allow_credentials if allow_credentials else None,
            user_verification=UserVerificationRequirement.PREFERRED,
            timeout=self.config.passkey_timeout_ms
        )
        
        # Convert to JSON-serializable format
        options_dict = json.loads(options_to_json(options))
        
        # Store challenge
        options_dict['_challenge'] = base64.b64encode(options.challenge).decode()
        
        return options_dict
        
    async def complete_authentication(
        self,
        authentication_response: Dict[str, Any],
        expected_challenge: str
    ) -> tuple[BaseUser, UserCredential]:
        """
        Complete passkey authentication
        
        Args:
            authentication_response: Authentication response from client
            expected_challenge: Expected challenge (base64)
            
        Returns:
            Tuple of (user, credential)
            
        Raises:
            ValueError: If authentication fails
        """
        try:
            # Get credential ID from response
            credential_id = authentication_response['id']
            
            # Find credential in database
            credential_record = self.get_credential(credential_id)
            if not credential_record:
                raise ValueError("Credential not found")
                
            # Get user
            user = self.db.query(self.config.user_model).filter(
                BaseUser.id == credential_record.user_id
            ).first()
            
            if not user or not user.is_active:
                raise ValueError("User not found or inactive")
                
            # Decode stored public key and challenge
            public_key_bytes = base64.b64decode(credential_record.public_key)
            expected_challenge_bytes = base64.b64decode(expected_challenge)
            
            # Create credential object
            credential = AuthenticationCredential(
                id=authentication_response['id'],
                raw_id=authentication_response['rawId'],
                response=authentication_response['response'],
                authenticator_attachment=authentication_response.get('authenticatorAttachment'),
                client_extension_results=authentication_response.get('clientExtensionResults', {}),
                type=authentication_response['type']
            )
            
            # Verify authentication
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=expected_challenge_bytes,
                expected_origin=self.config.passkey_origin,
                expected_rp_id=self.config.passkey_rp_id,
                credential_public_key=public_key_bytes,
                credential_current_sign_count=credential_record.sign_count
            )
            
            if not verification.verified:
                raise ValueError("Authentication verification failed")
                
        except Exception as e:
            logger.error(f"Authentication verification failed: {e}")
            raise ValueError(f"Authentication verification failed: {str(e)}")
            
        # Update credential usage
        credential_record.update_usage(verification.new_sign_count)
        self.db.commit()
        
        # Update user last login
        user.update_last_login()
        self.db.commit()
        
        # Emit event
        await auth_events.emit("passkey_authenticated", {
            "user_id": str(user.id),
            "passkey_id": str(credential_record.id)
        })
        
        return user, credential_record
        
    async def delete_credential(
        self,
        credential_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Delete a passkey credential
        
        Args:
            credential_id: Credential UUID
            user_id: User ID (for verification)
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If deleting last auth method
        """
        # Get credential
        credential = self.get_credential_by_uuid(credential_id, user_id)
        if not credential:
            return False
            
        # Check if user has other auth methods
        user = self.db.query(self.config.user_model).filter(
            self.config.user_model.id == user_id
        ).first()
        
        if not user:
            return False
            
        # Count remaining credentials
        credential_count = self.db.query(UserCredential).filter(
            UserCredential.user_id == user_id
        ).count()
        
        # Check if this is the last auth method
        if credential_count == 1 and not user.hashed_password:
            raise ValueError("Cannot delete last authentication method")
            
        # Delete credential
        self.db.delete(credential)
        self.db.commit()
        
        # Emit event
        await auth_events.emit("passkey_deleted", {
            "user_id": str(user_id),
            "passkey_id": str(credential_id)
        })
        
        return True
        
    async def rename_credential(
        self,
        credential_id: UUID,
        user_id: UUID,
        new_name: str
    ) -> Optional[UserCredential]:
        """
        Rename a passkey credential
        
        Args:
            credential_id: Credential UUID
            user_id: User ID (for verification)
            new_name: New name for the credential
            
        Returns:
            Updated credential or None
        """
        # Get credential
        credential = self.get_credential_by_uuid(credential_id, user_id)
        if not credential:
            return None
            
        # Update name
        credential.name = new_name
        credential.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(credential)
        
        return credential