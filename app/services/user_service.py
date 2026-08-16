from sqlalchemy.orm import Session

from app.models import User
from app.repo.user_repo import UserRepository
from app.schemas.user import UserProfileUpdate


class UserService:

    @staticmethod
    def update_profile(
        db: Session,
        current_user: User,
        data: UserProfileUpdate,
    ) -> User:
        current_user.full_name = data.full_name

        return UserRepository.update_user(
            db,
            current_user,
        )
