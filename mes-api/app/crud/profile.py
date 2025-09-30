from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from uuid import UUID
from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileUpdate


def get_profiles(db: Session, skip: int = 0, limit: int = 100) -> List[Profile]:
    return db.query(Profile).order_by(Profile.email).offset(skip).limit(limit).all()


def get_profile(db: Session, profile_id: UUID) -> Optional[Profile]:
    return db.query(Profile).filter(Profile.id == profile_id).first()


def get_profile_by_email(db: Session, email: str) -> Optional[Profile]:
    return db.query(Profile).filter(Profile.email == email).first()


def create_profile(db: Session, profile: ProfileCreate) -> Profile:
    try:
        db_profile = Profile(**profile.model_dump())
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        return db_profile
    except IntegrityError:
        db.rollback()
        raise


def update_profile(
    db: Session, profile_id: UUID, profile_update: ProfileUpdate
) -> Optional[Profile]:
    db_profile = get_profile(db, profile_id)
    if not db_profile:
        return None

    update_data = profile_update.model_dump(exclude_unset=True)

    try:
        for field, value in update_data.items():
            setattr(db_profile, field, value)

        db.commit()
        db.refresh(db_profile)
        return db_profile
    except IntegrityError:
        db.rollback()
        raise


def delete_profile(db: Session, profile_id: UUID) -> bool:
    db_profile = get_profile(db, profile_id)
    if not db_profile:
        return False

    try:
        db.delete(db_profile)
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        raise
