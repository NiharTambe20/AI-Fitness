from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.user import UserCreate, UserResponse
from backend.services.workout_service import workout_service

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create a new User Profile")
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create a new User Profile")
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Registers or creates a new user profile.
    """
    return workout_service.create_user(db, user_in)

@router.get("", response_model=List[UserResponse], summary="List all Users")
@router.get("/", response_model=List[UserResponse], summary="List all Users")
def list_users(db: Session = Depends(get_db)):
    """
    Retrieves all registered user profiles.
    """
    return workout_service.get_users(db)

@router.get("/{user_id}", response_model=UserResponse, summary="Get User Profile by ID")
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieves user profile details by ID.
    """
    user = workout_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found.")
    return user
