"""
Email service for authentication
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import ssl
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..core.security import (
    generate_email_verification_token,
    generate_password_reset_token
)
from ..core.events import auth_events
from ..config import AuthConfig

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending authentication-related emails
    
    Supports:
    - Email verification
    - Password reset
    - 2FA notifications
    - Security alerts
    """
    
    def __init__(self, config: AuthConfig):
        """
        Initialize email service
        
        Args:
            config: Authentication configuration
        """
        self.config = config
        
        # Initialize template environment if templates are available
        if config.email_template_dir:
            self.template_env = Environment(
                loader=FileSystemLoader(config.email_template_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )
        else:
            self.template_env = None
            
    def _create_smtp_connection(self) -> smtplib.SMTP:
        """
        Create SMTP connection
        
        Returns:
            SMTP connection
        """
        # Create SSL context
        context = ssl.create_default_context()
        
        # Create connection based on SSL usage
        if self.config.smtp_ssl:
            smtp = smtplib.SMTP_SSL(
                self.config.smtp_host,
                self.config.smtp_port,
                context=context
            )
        else:
            smtp = smtplib.SMTP(
                self.config.smtp_host,
                self.config.smtp_port
            )
            if self.config.smtp_tls:
                smtp.starttls(context=context)
                
        # Authenticate if credentials provided
        if self.config.smtp_username and self.config.smtp_password:
            smtp.login(
                self.config.smtp_username,
                self.config.smtp_password
            )
            
        return smtp
        
    def _render_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        Render email template
        
        Args:
            template_name: Template name (without extension)
            context: Template context
            
        Returns:
            Tuple of (html_content, text_content)
        """
        if not self.template_env:
            # Return simple text if no templates
            return None, self._get_default_text(template_name, context)
            
        try:
            # Try to render HTML template
            html_template = self.template_env.get_template(f"{template_name}.html")
            html_content = html_template.render(**context)
        except Exception:
            html_content = None
            
        try:
            # Try to render text template
            text_template = self.template_env.get_template(f"{template_name}.txt")
            text_content = text_template.render(**context)
        except Exception:
            text_content = self._get_default_text(template_name, context)
            
        return html_content, text_content
        
    def _get_default_text(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Get default text content for email
        
        Args:
            template_name: Template name
            context: Template context
            
        Returns:
            Default text content
        """
        defaults = {
            "verify_email": f"Please verify your email by clicking: {context.get('verify_url', '')}",
            "reset_password": f"Reset your password by clicking: {context.get('reset_url', '')}",
            "2fa_enabled": "Two-factor authentication has been enabled on your account.",
            "2fa_disabled": "Two-factor authentication has been disabled on your account.",
            "passkey_added": f"A new passkey '{context.get('passkey_name', 'Unknown')}' has been added to your account.",
            "security_alert": f"Security alert: {context.get('alert_message', 'Unknown activity detected')}",
            "welcome": f"Welcome to {self.config.app_name}!"
        }
        
        return defaults.get(template_name, "Email notification from " + self.config.app_name)
        
    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None
    ) -> bool:
        """
        Send email using template
        
        Args:
            to_email: Recipient email
            subject: Email subject
            template_name: Template name
            context: Template context
            cc: CC recipients
            bcc: BCC recipients
            
        Returns:
            True if sent successfully
        """
        try:
            # Add common context
            context.update({
                "app_name": self.config.app_name,
                "app_url": self.config.app_url,
                "support_email": self.config.support_email,
                "year": datetime.utcnow().year
            })
            
            # Render template
            html_content, text_content = self._render_template(template_name, context)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config.email_from
            msg['To'] = to_email
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            if bcc:
                msg['Bcc'] = ', '.join(bcc)
                
            # Add text part
            text_part = MIMEText(text_content, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if available
            if html_content:
                html_part = MIMEText(html_content, 'html')
                msg.attach(html_part)
                
            # Send email
            with self._create_smtp_connection() as smtp:
                recipients = [to_email]
                if cc:
                    recipients.extend(cc)
                if bcc:
                    recipients.extend(bcc)
                    
                smtp.send_message(msg, to_addrs=recipients)
                
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
            
    async def send_verification_email(
        self,
        user_email: str,
        user_name: Optional[str] = None
    ) -> bool:
        """
        Send email verification
        
        Args:
            user_email: User email
            user_name: User's name
            
        Returns:
            True if sent successfully
        """
        # Generate verification token
        token = generate_email_verification_token(
            user_email,
            self.config.jwt_secret
        )
        
        # Build verification URL
        verify_url = f"{self.config.app_url}/auth/verify-email/{token}"
        
        # Send email
        success = await self.send_email(
            to_email=user_email,
            subject=f"Verify your email for {self.config.app_name}",
            template_name="verify_email",
            context={
                "user_name": user_name or user_email,
                "verify_url": verify_url,
                "expires_in": "24 hours"
            }
        )
        
        if success:
            await auth_events.emit("email_verification_sent", {
                "email": user_email
            })
            
        return success
        
    async def send_password_reset_email(
        self,
        user_email: str,
        user_name: Optional[str] = None
    ) -> bool:
        """
        Send password reset email
        
        Args:
            user_email: User email
            user_name: User's name
            
        Returns:
            True if sent successfully
        """
        # Generate reset token
        token = generate_password_reset_token(
            user_email,
            self.config.jwt_secret
        )
        
        # Build reset URL
        reset_url = f"{self.config.app_url}/auth/reset-password/{token}"
        
        # Send email
        success = await self.send_email(
            to_email=user_email,
            subject=f"Reset your password for {self.config.app_name}",
            template_name="reset_password",
            context={
                "user_name": user_name or user_email,
                "reset_url": reset_url,
                "expires_in": "1 hour"
            }
        )
        
        if success:
            await auth_events.emit("password_reset_email_sent", {
                "email": user_email
            })
            
        return success
        
    async def send_2fa_enabled_email(
        self,
        user_email: str,
        user_name: Optional[str] = None,
        device_info: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send 2FA enabled notification
        
        Args:
            user_email: User email
            user_name: User's name
            device_info: Device information
            
        Returns:
            True if sent successfully
        """
        return await self.send_email(
            to_email=user_email,
            subject=f"Two-factor authentication enabled on {self.config.app_name}",
            template_name="2fa_enabled",
            context={
                "user_name": user_name or user_email,
                "enabled_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                "device_info": device_info
            }
        )
        
    async def send_2fa_disabled_email(
        self,
        user_email: str,
        user_name: Optional[str] = None,
        device_info: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send 2FA disabled notification
        
        Args:
            user_email: User email
            user_name: User's name
            device_info: Device information
            
        Returns:
            True if sent successfully
        """
        return await self.send_email(
            to_email=user_email,
            subject=f"Two-factor authentication disabled on {self.config.app_name}",
            template_name="2fa_disabled",
            context={
                "user_name": user_name or user_email,
                "disabled_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                "device_info": device_info
            }
        )
        
    async def send_passkey_added_email(
        self,
        user_email: str,
        passkey_name: str,
        user_name: Optional[str] = None,
        device_info: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send passkey added notification
        
        Args:
            user_email: User email
            passkey_name: Passkey name
            user_name: User's name
            device_info: Device information
            
        Returns:
            True if sent successfully
        """
        return await self.send_email(
            to_email=user_email,
            subject=f"New passkey added to your {self.config.app_name} account",
            template_name="passkey_added",
            context={
                "user_name": user_name or user_email,
                "passkey_name": passkey_name,
                "added_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                "device_info": device_info
            }
        )
        
    async def send_security_alert_email(
        self,
        user_email: str,
        alert_type: str,
        alert_message: str,
        user_name: Optional[str] = None,
        device_info: Optional[Dict[str, str]] = None,
        action_url: Optional[str] = None
    ) -> bool:
        """
        Send security alert email
        
        Args:
            user_email: User email
            alert_type: Type of alert
            alert_message: Alert message
            user_name: User's name
            device_info: Device information
            action_url: URL for user action
            
        Returns:
            True if sent successfully
        """
        return await self.send_email(
            to_email=user_email,
            subject=f"Security alert for your {self.config.app_name} account",
            template_name="security_alert",
            context={
                "user_name": user_name or user_email,
                "alert_type": alert_type,
                "alert_message": alert_message,
                "alert_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                "device_info": device_info,
                "action_url": action_url or f"{self.config.app_url}/account/security"
            }
        )
        
    async def send_welcome_email(
        self,
        user_email: str,
        user_name: Optional[str] = None,
        verification_required: bool = False
    ) -> bool:
        """
        Send welcome email to new user
        
        Args:
            user_email: User email
            user_name: User's name
            verification_required: Whether email verification is required
            
        Returns:
            True if sent successfully
        """
        context = {
            "user_name": user_name or user_email,
            "getting_started_url": f"{self.config.app_url}/getting-started",
            "help_url": f"{self.config.app_url}/help",
            "verification_required": verification_required
        }
        
        if verification_required:
            # Include verification token
            token = generate_email_verification_token(
                user_email,
                self.config.jwt_secret
            )
            context["verify_url"] = f"{self.config.app_url}/auth/verify-email/{token}"
            
        return await self.send_email(
            to_email=user_email,
            subject=f"Welcome to {self.config.app_name}!",
            template_name="welcome",
            context=context
        )