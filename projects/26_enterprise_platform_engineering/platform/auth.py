"""
Authentication & Authorization Module
Handles user authentication, JWT tokens, and RBAC
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, DateTime, JSON, Text, Boolean, Integer
import uuid
import secrets

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "postgresql+asyncpg://platform:platform@platform-postgres:5432/platform"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Security settings
SECRET_KEY = "your-secret-key-here-change-in-production"  # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")


# ============================================================================
# Database Models
# ============================================================================

class UserModel(Base):
    """User database model."""
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    roles = Column(JSON, default=list)  # List of roles
    teams = Column(JSON, default=list)  # List of teams
    permissions = Column(JSON, default=dict)  # Custom permissions
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RefreshTokenModel(Base):
    """Refresh token database model."""
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RoleModel(Base):
    """Role database model."""
    __tablename__ = "roles"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    permissions = Column(JSON, default=list)  # List of permissions
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# Pydantic Models
# ============================================================================

class User(BaseModel):
    """User model."""
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    roles: List[str]
    teams: List[str]
    permissions: Dict[str, Any]
    is_active: bool
    is_superuser: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    """User creation request."""
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    roles: List[str] = []
    teams: List[str] = []


class UserUpdate(BaseModel):
    """User update request."""
    email: Optional[str] = None
    full_name: Optional[str] = None
    roles: Optional[List[str]] = None
    teams: Optional[List[str]] = None
    is_active: Optional[bool] = None


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class TokenData(BaseModel):
    """Token data model."""
    username: str
    roles: List[str] = []
    permissions: Dict[str, Any] = {}


# ============================================================================
# Authentication Service
# ============================================================================

class AuthenticationService:
    """Authentication and authorization service."""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.roles: Dict[str, RoleModel] = {}

    async def initialize(self):
        """Initialize authentication service."""
        logger.info("Initializing authentication service...")

        # Create database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Load users from database
        await self._load_users()

        # Load roles from database
        await self._load_roles()

        # Create default admin user if no users exist
        if not self.users:
            await self._create_default_admin()

        logger.info(f"Authentication service initialized with {len(self.users)} users")

    async def _load_users(self):
        """Load users from database."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(select(UserModel))
            users = result.scalars().all()

            for user in users:
                self.users[user.id] = User(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    full_name=user.full_name,
                    roles=user.roles or [],
                    teams=user.teams or [],
                    permissions=user.permissions or {},
                    is_active=user.is_active,
                    is_superuser=user.is_superuser,
                    last_login=user.last_login,
                    created_at=user.created_at,
                    updated_at=user.updated_at
                )

    async def _load_roles(self):
        """Load roles from database."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(select(RoleModel))
            roles = result.scalars().all()

            for role in roles:
                self.roles[role.id] = role

    async def _create_default_admin(self):
        """Create default admin user."""
        admin_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Hash password
        hashed_password = pwd_context.hash("admin123")

        # Create user
        async with AsyncSessionLocal() as session:
            user_model = UserModel(
                id=admin_id,
                username="admin",
                email="admin@platform.local",
                hashed_password=hashed_password,
                full_name="Platform Administrator",
                roles=["platform-admin"],
                teams=["platform"],
                is_active=True,
                is_superuser=True,
                created_at=now,
                updated_at=now
            )
            session.add(user_model)
            await session.commit()

        # Add to cache
        self.users[admin_id] = User(
            id=admin_id,
            username="admin",
            email="admin@platform.local",
            full_name="Platform Administrator",
            roles=["platform-admin"],
            teams=["platform"],
            is_active=True,
            is_superuser=True,
            created_at=now,
            updated_at=now
        )

        logger.info("Created default admin user: admin / admin123")
        return self.users[admin_id]

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            User if authenticated, None otherwise
        """
        # Find user by username
        user = next((u for u in self.users.values() if u.username == username), None)
        if not user:
            logger.warning(f"Authentication failed: user {username} not found")
            return None

        # Verify password
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(UserModel).where(UserModel.id == user.id)
            )
            user_model = result.scalar_one_or_none()

            if not user_model:
                return None

            if not pwd_context.verify(password, user_model.hashed_password):
                logger.warning(f"Authentication failed: invalid password for {username}")
                return None

            # Update last login
            user_model.last_login = datetime.utcnow()
            await session.commit()

            # Update cache
            user.last_login = datetime.utcnow()

        logger.info(f"User authenticated: {username}")
        return user

    async def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User or None if not found
        """
        return self.users.get(user_id)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User or None if not found
        """
        return next((u for u in self.users.values() if u.username == username), None)

    async def create_user(self, user_create: UserCreate) -> User:
        """
        Create new user.
        
        Args:
            user_create: User creation request
            
        Returns:
            Created user
        """
        user_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Hash password
        hashed_password = pwd_context.hash(user_create.password)

        # Create user
        async with AsyncSessionLocal() as session:
            user_model = UserModel(
                id=user_id,
                username=user_create.username,
                email=user_create.email,
                hashed_password=hashed_password,
                full_name=user_create.full_name,
                roles=user_create.roles,
                teams=user_create.teams,
                is_active=True,
                created_at=now,
                updated_at=now
            )
            session.add(user_model)
            await session.commit()

        # Add to cache
        user = User(
            id=user_id,
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            roles=user_create.roles,
            teams=user_create.teams,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        self.users[user_id] = user

        logger.info(f"Created user: {user_create.username}")
        return user

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.
        
        Args:
            data: Token payload data
            expires_delta: Token expiration time
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        return encoded_jwt

    async def create_refresh_token(self, user_id: str) -> str:
        """
        Create refresh token.
        
        Args:
            user_id: User ID
            
        Returns:
            Refresh token string
        """
        token = secrets.token_urlsafe(64)
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        # Save to database
        async with AsyncSessionLocal() as session:
            token_model = RefreshTokenModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                token=token,
                expires_at=expires_at,
                created_at=datetime.utcnow()
            )
            session.add(token_model)
            await session.commit()

        return token

    async def verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Token data if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            token_type: str = payload.get("type")

            if username is None or token_type != "access":
                return None

            # Get user
            user = await self.get_user_by_username(username)
            if not user or not user.is_active:
                return None

            return TokenData(
                username=user.username,
                roles=user.roles,
                permissions=user.permissions
            )

        except JWTError:
            logger.warning("Token verification failed")
            return None

    async def refresh_access_token(self, refresh_token: str) -> Optional[Token]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            New token pair or None if invalid
        """
        # Find refresh token
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(RefreshTokenModel).where(
                    RefreshTokenModel.token == refresh_token,
                    RefreshTokenModel.expires_at > datetime.utcnow()
                )
            )
            token_model = result.scalar_one_or_none()

            if not token_model:
                return None

            # Get user
            user = await self.get_user(token_model.user_id)
            if not user or not user.is_active:
                return None

            # Create new tokens
            access_token = self.create_access_token(
                data={"sub": user.username, "roles": user.roles}
            )
            new_refresh_token = await self.create_refresh_token(user.id)

            # Delete old refresh token
            await session.delete(token_model)
            await session.commit()

            return Token(
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user=user
            )

    async def get_current_user(
        self,
        token: str = Depends(oauth2_scheme)
    ) -> User:
        """
        Get current user from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Current user
            
        Raises:
            HTTPException: If token is invalid
        """
        token_data = await self.verify_token(token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await self.get_user_by_username(token_data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        return user

    async def get_current_active_user(
        self,
        token: str = Depends(oauth2_scheme)
    ) -> User:
        """
        Get current active user.
        
        Args:
            token: JWT token string
            
        Returns:
            Current active user
            
        Raises:
            HTTPException: If user is inactive
        """
        user = await self.get_current_user(token)
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
        return user

    async def require_permission(
        self,
        token: str,
        permission: str
    ):
        """
        Require specific permission.
        
        Args:
            token: JWT token string
            permission: Required permission
            
        Raises:
            HTTPException: If user lacks permission
        """
        user = await self.get_current_user(token)

        # Check if superuser
        if user.is_superuser:
            return

        # Check if user has permission
        if permission in user.permissions.get("direct", []):
            return

        # Check role-based permissions
        for role in user.roles:
            role_perms = user.permissions.get("roles", {}).get(role, [])
            if permission in role_perms or "*" in role_perms:
                return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission required: {permission}"
        )

    async def require_role(
        self,
        token: str,
        required_roles: List[str]
    ):
        """
        Require one of specified roles.
        
        Args:
            token: JWT token string
            required_roles: List of required roles
            
        Raises:
            HTTPException: If user lacks required role
        """
        user = await self.get_current_user(token)

        # Check if superuser
        if user.is_superuser:
            return

        # Check if user has any of the required roles
        if not any(role in user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_roles}"
            )


# ============================================================================
# Global instance
# ============================================================================

auth_service = AuthenticationService()


async def get_auth_service() -> AuthenticationService:
    """Get authentication service instance."""
    return auth_service