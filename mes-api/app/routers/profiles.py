from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from uuid import UUID
import logging
from app.database import get_db
from app.schemas.profile import Profile, ProfileCreate, ProfileUpdate
from app.crud import profile

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[Profile])
def list_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    logger.info(f"Listing profiles: skip={skip}, limit={limit}")
    return profile.get_profiles(db, skip=skip, limit=limit)


@router.get("/{profile_id}", response_model=Profile)
def get_profile(profile_id: UUID, db: Session = Depends(get_db)):
    logger.info(f"Getting profile: {profile_id}")
    profile_data = profile.get_profile(db, profile_id)
    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Profile not found: {profile_id}",
            },
        )
    return profile_data


@router.post("/", response_model=Profile, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: ProfileCreate, response: Response, db: Session = Depends(get_db)
):
    logger.info(f"Creating profile: {profile_data.id}")
    existing = profile.get_profile(db, profile_data.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "duplicate_profile",
                "message": f"Profile already exists: {profile_data.id}",
            },
        )

    try:
        created = profile.create_profile(db, profile_data)
        response.headers["Location"] = f"/api/v1/profiles/{created.id}"
        logger.info(f"Profile created: {created.id}")
        return created
    except IntegrityError as e:
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "integrity_error",
                "message": "Database constraint violation",
            },
        )


@router.patch("/{profile_id}", response_model=Profile)
def update_profile(
    profile_id: UUID, profile_update: ProfileUpdate, db: Session = Depends(get_db)
):
    logger.info(f"Updating profile: {profile_id}")
    try:
        updated = profile.update_profile(db, profile_id, profile_update)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "not_found",
                    "message": f"Profile not found: {profile_id}",
                },
            )
        logger.info(f"Profile updated: {profile_id}")
        return updated
    except IntegrityError as e:
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "integrity_error",
                "message": "Database constraint violation",
            },
        )


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: UUID, db: Session = Depends(get_db)):
    logger.info(f"Deleting profile: {profile_id}")
    deleted = profile.delete_profile(db, profile_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Profile not found: {profile_id}",
            },
        )
    logger.info(f"Profile deleted: {profile_id}")
    return None
