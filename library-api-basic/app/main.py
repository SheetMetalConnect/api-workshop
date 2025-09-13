from fastapi import FastAPI
from app.database import engine
from app.models import author, book, branch, library_system, loan, patron  # Updated import
from app.routers import authors, books, branches, library_system, loans, patrons  # Updated import

app = FastAPI(title="Public Library API")

# Create all tables
author.Base.metadata.create_all(bind=engine)  # Still works as Base is shared

app.include_router(authors.router, prefix="/authors", tags=["authors"])
app.include_router(books.router, prefix="/books", tags=["books"])
app.include_router(branches.router, prefix="/branches", tags=["branches"])
app.include_router(library_system.router, prefix="/library-system", tags=["library-system"])  # Updated
app.include_router(loans.router, prefix="/loans", tags=["loans"])
app.include_router(patrons.router, prefix="/patrons", tags=["patrons"])