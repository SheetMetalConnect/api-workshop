from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.schemas.book import Book, BookCreate, BookUpdate
from app.crud.book import (
    get_books, get_book, create_book, update_book,
    partial_update_book, delete_book
)
from app.database import get_db

router = APIRouter()

@router.get("/", response_model=List[Book], status_code=status.HTTP_200_OK)
def read_books(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_books(db, skip=skip, limit=limit)

@router.get("/{book_id}", response_model=Book, status_code=status.HTTP_200_OK)
def read_book(book_id: int, db: Session = Depends(get_db)):
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book

@router.post("/", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_new_book(book: BookCreate, db: Session = Depends(get_db)):
    return create_book(db, book)

@router.put("/{book_id}", response_model=Book, status_code=status.HTTP_200_OK)
def update_existing_book(book_id: int, book: BookUpdate, db: Session = Depends(get_db)):
    updated_book = update_book(db, book_id, book)
    if not updated_book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return updated_book

@router.patch("/{book_id}", response_model=Book, status_code=status.HTTP_200_OK)
def partial_update_existing_book(book_id: int, book_data: Dict[str, Any], db: Session = Depends(get_db)):
    updated_book = partial_update_book(db, book_id, book_data)
    if not updated_book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return updated_book

@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_book(book_id: int, db: Session = Depends(get_db)):
    deleted_book = delete_book(db, book_id)
    if not deleted_book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")