"""
Kitchen courses API endpoints for course management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, SQLModel
from typing import List, Optional
import structlog
import uuid

from app.core.database import get_session
from app.core.dependencies import get_tenant_id
from app.models.kitchen_course import KitchenCourse, CourseType

logger = structlog.get_logger(__name__)
router = APIRouter()


class KitchenCourseResponse(SQLModel):
    """Schema for kitchen course response"""
    id: uuid.UUID
    tenant_id: uuid.UUID
    location_id: uuid.UUID
    station_id: uuid.UUID
    name: str
    course_type: CourseType
    course_number: int
    display_order: int
    color: Optional[str] = None
    icon: Optional[str] = None
    auto_fire_on_confirm: bool = False
    default_prep_time_minutes: Optional[int] = None
    is_active: bool = True
    is_visible_in_menu: bool = True
    created_at: Optional[str] = None


@router.get("/", response_model=List[KitchenCourseResponse])
async def list_courses(
    location_id: Optional[uuid.UUID] = Query(None, description="Filter by location"),
    station_id: Optional[uuid.UUID] = Query(None, description="Filter by station"),
    course_type: Optional[CourseType] = Query(None, description="Filter by course type"),
    active_only: Optional[bool] = Query(True, description="Only return active courses"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: Session = Depends(get_session)
):
    """List kitchen courses"""
    try:
        query = select(KitchenCourse).where(KitchenCourse.tenant_id == tenant_id)

        if location_id:
            query = query.where(KitchenCourse.location_id == location_id)

        if station_id:
            query = query.where(KitchenCourse.station_id == station_id)

        if course_type:
            query = query.where(KitchenCourse.course_type == course_type)

        if active_only:
            query = query.where(KitchenCourse.is_active == True)

        # Sort by course_number, then display_order
        query = query.order_by(KitchenCourse.course_number.asc(), KitchenCourse.display_order.asc())

        courses = session.exec(query).all()
        return courses

    except Exception as e:
        logger.error(f"Error listing courses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list courses"
        )


@router.get("/{course_id}", response_model=KitchenCourseResponse)
async def get_course(
    course_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: Session = Depends(get_session)
):
    """Get course details"""
    try:
        course = session.exec(
            select(KitchenCourse).where(
                KitchenCourse.id == course_id,
                KitchenCourse.tenant_id == tenant_id
            )
        ).first()

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )

        return course

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting course: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get course"
        )
