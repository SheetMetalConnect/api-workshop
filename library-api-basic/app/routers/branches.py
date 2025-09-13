from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.schemas.branch import Branch, BranchCreate, BranchUpdate
from app.crud.branch import (
    get_branches, get_branch, create_branch, update_branch,
    partial_update_branch, delete_branch
)
from app.database import get_db

router = APIRouter()

@router.get("/", response_model=List[Branch], status_code=status.HTTP_200_OK)
def read_branches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_branches(db, skip=skip, limit=limit)

@router.get("/{branch_id}", response_model=Branch, status_code=status.HTTP_200_OK)
def read_branch(branch_id: int, db: Session = Depends(get_db)):
    branch = get_branch(db, branch_id)
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    return branch

@router.post("/", response_model=Branch, status_code=status.HTTP_201_CREATED)
def create_new_branch(branch: BranchCreate, db: Session = Depends(get_db)):
    return create_branch(db, branch)

@router.put("/{branch_id}", response_model=Branch, status_code=status.HTTP_200_OK)
def update_existing_branch(branch_id: int, branch: BranchUpdate, db: Session = Depends(get_db)):
    updated_branch = update_branch(db, branch_id, branch)
    if not updated_branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    return updated_branch

@router.patch("/{branch_id}", response_model=Branch, status_code=status.HTTP_200_OK)
def partial_update_existing_branch(branch_id: int, branch_data: Dict[str, Any], db: Session = Depends(get_db)):
    updated_branch = partial_update_branch(db, branch_id, branch_data)
    if not updated_branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    return updated_branch

@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_branch(branch_id: int, db: Session = Depends(get_db)):
    deleted_branch = delete_branch(db, branch_id)
    if not deleted_branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")