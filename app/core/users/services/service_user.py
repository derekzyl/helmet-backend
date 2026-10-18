from typing import List, Optional

from fastapi import HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.models.model_token import TokenModel

# Import your RBAC models (assuming they're in the same module or adjust imports)
from app.core.roles.models import (
    AttributePermissionModel,
    PermissionModel,
    PolicyRuleModel,
    PolicyRulePermissionModel,
    RoleModel,
    RolePermissionModel,
    UserAttributeModel,
    UserRoleModel,
)
from app.core.users.models.model_user import UserModel
from app.core.users.types.type_user import CreateUserData, UpdateUserData, UserTypeEnum
from app.utils.crud.migration_helper import HybridCrudService as CrudService
from app.utils.crud.types_crud import response_message
from app.utils.logger.log import logs
from app.utils.password_hash import PassHash


class UserService:
    def __init__(self, db: AsyncSession, current_user_id: Optional[str] = None) -> None:
        self.crud_service = CrudService(db=db, model=UserModel, current_user_id=current_user_id) # type: ignore
        self.db = db
        self.current_user_id = current_user_id

    async def create_user(self, user_data: CreateUserData):
        hasher =  PassHash()
        """Create a new user"""
        try:
            # Check if user with email already exists
            existing_user_query = select(UserModel).where(
                (UserModel.email).ilike(str(user_data.get("email")).lower().strip())
            )
            existing_user_result = await self.db.execute(existing_user_query)
            existing_user = existing_user_result.scalar_one_or_none()

            if existing_user:
                raise HTTPException(
                    status_code=400,
                    detail=response_message(
                        error="Email already exists",
                        success_status=False,
                        message="A user with this email already exists",
                    ),
                )

            # Create new user instance
            user_type_value = user_data.get("user_type") or UserTypeEnum.USER.value
            if isinstance(user_type_value, UserTypeEnum):
                user_type_value = user_type_value.value
            
            new_user = UserModel(
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                email=str(user_data.get("email")).lower().strip(),
                password=hasher.hash_me(user_data.get(
                    "password"
                )),  
                user_type=user_type_value,
                privacy_policy_accepted=user_data.get("privacy_policy_accepted", True),
                privacy_policy_accepted_at=user_data.get("privacy_policy_accepted_at"),
            )

            # Optional attributes
            gender_value = user_data.get("gender")
            if gender_value:
                new_user.gender = gender_value  # type: ignore

            allow_login_value = user_data.get("allow_login")
            if allow_login_value is not None:
                new_user.allow_login = bool(allow_login_value)  # type: ignore

            username_value = user_data.get("username")
            if username_value:
                new_user.username = username_value  # type: ignore

            name_value = user_data.get("name")
            if name_value:
                new_user.name = name_value  # type: ignore
            elif new_user.first_name and new_user.last_name:
                new_user.name = f"{new_user.first_name} {new_user.last_name}"

            # Add to database
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)

            return new_user

        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to create user",
                ),
            )

    async def get_user_by_id(self, user_id: str):
        try:
            user = await self.crud_service.get_one({"id": user_id})
            return user
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=response_message(
                    error=e, success_status=False, message="User not found"
                ),
            )

    async def get_users(self, query: dict, filter: dict):
        try:
            users = await self.crud_service.get_many(query=query, filter=filter)
            return users
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=response_message(
                    error=e, success_status=False, message="User not found"
                ),
            )

    async def delete_user(self, user_id: str):
        try:
            # Explicit token cleanup for databases without ON DELETE CASCADE on TOKEN.
            await self.db.execute(delete(TokenModel).where(TokenModel.user_id == user_id))
            deleted_user = await self.crud_service.delete({"id": user_id})
            logs.info(f"deleted_user==========>>>: {deleted_user}")
            return deleted_user
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=400,
                detail=response_message(
                    error=e, success_status=False, message="User not deleted"
                ),
            )

    async def get_user(self, data: dict):
        try:
          
            user = await self.crud_service.get_one(data=data)
           
            return user
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=response_message(
                    error=e, success_status=False, message="User not found"
                ),
            )

    async def get_user_by_email(self, email: str):
            """Get a user by their email"""
            try:
                query = select(UserModel).where(UserModel.email.ilike(str(email).lower().strip()))
                result = await self.db.execute(query)
                user = result.scalar_one_or_none()

                if not user:
                    raise HTTPException(
                        status_code=404,
                        detail=response_message(
                            error="User not found",
                            success_status=False,
                            message="User not found",
                        ),
                    )

                return user
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=response_message(
                        error=str(e),
                        success_status=False,
                        message="Failed to retrieve user",
                    ),
                )
    async def retrieve_user_by_id(self, user_id: str):
    
        user = await self.crud_service.get_one({"id": user_id})
        if not user["data"]:
            return None
        return user
    async def retrieve_user_by_email(self, email: str):
        user = await self.crud_service.get_one({"email": email})
        if not user["data"]:
            return None
        return user
       
    async def update_user(self, filter: dict, data: UpdateUserData):
        d = dict(data)
        try:
            dta = await self.crud_service.update(filter=filter, data=d)
            return dta
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=response_message(
                    error=e, success_status=False, message="User not updated"
                ),
            )

    async def get_user_permissions(self, user_id: str) -> List[PermissionModel]:
        """Get all permissions for a user through roles and attributes"""
        try:
            # Get permissions through user roles
            role_permissions_query = (
                select(PermissionModel)
                .join(
                    RolePermissionModel,
                    PermissionModel.id == RolePermissionModel.permission_id,
                )
                .join(RoleModel, RolePermissionModel.role_id == RoleModel.id)
                .join(UserRoleModel, RoleModel.id == UserRoleModel.role_id)
                .where(UserRoleModel.user_id == user_id)
            )

            # Get permissions through user attributes
            attribute_permissions_query = (
                select(PermissionModel)
                .join(
                    AttributePermissionModel,
                    PermissionModel.id == AttributePermissionModel.permission_id,
                )
                .join(
                    UserAttributeModel,
                    AttributePermissionModel.attribute_value_id
                    == UserAttributeModel.attribute_value_id,
                )
                .where(UserAttributeModel.user_id == user_id)
            )

            # Execute queries
            role_permissions_result = await self.db.execute(role_permissions_query)
            attribute_permissions_result = await self.db.execute(
                attribute_permissions_query
            )

            # Combine and deduplicate permissions
            role_permissions = role_permissions_result.scalars().all()
            attribute_permissions = attribute_permissions_result.scalars().all()

            # Use set to remove duplicates, then convert back to list
            all_permissions = list(
                set(list(role_permissions) + list(attribute_permissions))
            )

            return all_permissions

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to retrieve user permissions",
                ),
            )

    async def check_user_permission(
        self, user_id: str, required_permission: str, resource: str, action: str
    ) -> bool:
        """Check if user has a specific permission"""
        try:
            # Direct permission check through roles
            role_permission_query = (
                select(PermissionModel)
                .join(
                    RolePermissionModel,
                    PermissionModel.id == RolePermissionModel.permission_id,
                )
                .join(RoleModel, RolePermissionModel.role_id == RoleModel.id)
                .join(UserRoleModel, RoleModel.id == UserRoleModel.role_id)
                .where(
                    UserRoleModel.user_id == user_id,
                    PermissionModel.name == required_permission,
                    PermissionModel.resource == resource,
                    PermissionModel.action == action,
                )
            )

            # Permission check through attributes
            attribute_permission_query = (
                select(PermissionModel)
                .join(
                    AttributePermissionModel,
                    PermissionModel.id == AttributePermissionModel.permission_id,
                )
                .join(
                    UserAttributeModel,
                    AttributePermissionModel.attribute_value_id
                    == UserAttributeModel.attribute_value_id,
                )
                .where(
                    UserAttributeModel.user_id == user_id,
                    PermissionModel.name == required_permission,
                    PermissionModel.resource == resource,
                    PermissionModel.action == action,
                )
            )

            # Check role-based permissions
            role_result = await self.db.execute(role_permission_query)
            role_permission = role_result.scalar_one_or_none()

            # Check attribute-based permissions
            attribute_result = await self.db.execute(attribute_permission_query)
            attribute_permission = attribute_result.scalar_one_or_none()

            return role_permission is not None or attribute_permission is not None

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to check user permission",
                ),
            )

    async def check_policy_rules(self, user_id: str, context: dict|None = None) -> List[str]:
        """
        Check policy rules for a user and return allowed permissions
        This is a basic implementation - you'll need to implement condition evaluation
        based on your specific policy rule format
        """
        try:
            # Get all policy rules that affect permissions
            policy_query = (
                select(PolicyRuleModel, PermissionModel)
                .join(
                    PolicyRulePermissionModel,
                    PolicyRuleModel.id == PolicyRulePermissionModel.policy_rule_id,
                )
                .join(
                    PermissionModel,
                    PolicyRulePermissionModel.permission_id == PermissionModel.id,
                )
            )

            result = await self.db.execute(policy_query)
            policy_permissions = result.all()

            allowed_permissions = []

            for policy_rule, permission in policy_permissions:
                # Here you would implement your condition evaluation logic
                # This is a placeholder - implement based on your condition format
                if self._evaluate_policy_condition(
                    policy_rule.condition, user_id, context
                ):
                    if policy_rule.effect == "ALLOW":
                        allowed_permissions.append(
                            f"{permission.resource}:{permission.action}"
                        )
                    # Handle DENY logic as needed

            return allowed_permissions

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to evaluate policy rules",
                ),
            )

    def _evaluate_policy_condition(
        self, condition: str, user_id: str, context: dict|None = None
    ) -> bool:
        """
        Evaluate policy rule condition - implement based on your condition format
        This is a placeholder implementation
        """
        # TODO: Implement condition evaluation based on your specific format
        # This could involve parsing JSON conditions, evaluating expressions, etc.
        return True  # Placeholder

    @staticmethod
    def get_logged_in_user(request: Request):
        """Get the logged-in user from request state"""
  
        user = getattr(request.state, "user", None)
        

        if not user:
            raise HTTPException(
                status_code=401,
                detail=response_message(
                    error="User not authorized",
                    success_status=False,
                    message="User not authorized",
                ),
            )

        return user

    async def get_logged_in_user_with_permissions(
        self,
        request: Request,
        required_permission: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
    ):
        """
        Get logged-in user and optionally check for specific permissions

        Args:
            request: FastAPI request object
            required_permission: Name of the permission to check
            resource: Resource the permission applies to
            action: Action the permission allows

        Returns:
            UserModel: The authenticated user

        Raises:
            HTTPException: If user is not authenticated or lacks required permissions
        """
        # Get the logged-in user
        user = self.get_logged_in_user(request)

        # If no permission check is required, return the user
        if not required_permission or not resource or not action:
            return user

        # Check if user has the required permission
        has_permission = await self.check_user_permission(
            user_id=user.id,
            required_permission=required_permission,
            resource=resource,
            action=action,
        )

        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail=response_message(
                    error="Insufficient permissions",
                    success_status=False,
                    message=f"User lacks permission '{required_permission}' for resource '{resource}' and action '{action}'",
                ),
            )

        return user

    async def require_permission(
        self, request: Request, permission_name: str, resource: str, action: str
    ):
        """
        Decorator-friendly method to require specific permissions

        Usage in your route handlers:
        user = await user_service.require_permission(
            request, "manage_users", "users", "create"
        )
        """
        return await self.get_logged_in_user_with_permissions(
            request=request,
            required_permission=permission_name,
            resource=resource,
            action=action,
        )
