"""Model management API routes"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from mcli.ml.api.schemas import ModelCreate, ModelMetrics, ModelResponse, ModelUpdate
from mcli.ml.auth import Permission, get_current_active_user, require_role
from mcli.ml.cache import cached
from mcli.ml.database.models import Model, ModelStatus, User, UserRole
from mcli.ml.database.session import get_async_db, get_db
from mcli.ml.tasks import train_model_task

router = APIRouter()


@router.get("/", response_model=List[ModelResponse])
@cached(expire=300)
async def list_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    status: Optional[ModelStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all available models"""
    query = db.query(Model)

    if status:
        query = query.filter(Model.status == status)

    models = query.offset(skip).limit(limit).all()
    return [ModelResponse.from_orm(m) for m in models]


@router.get("/{model_id}", response_model=ModelResponse)
@cached(expire=60)
async def get_model(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get specific model details"""
    model = db.query(Model).filter(Model.id == model_id).first()

    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    return ModelResponse.from_orm(model)


@router.post("/", response_model=ModelResponse)
async def create_model(
    model_data: ModelCreate,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Create a new model"""
    model = Model(
        **model_data.dict(), created_by=current_user.username, status=ModelStatus.TRAINING
    )

    db.add(model)
    db.commit()
    db.refresh(model)

    # Trigger training task
    train_model_task.delay(str(model.id))

    return ModelResponse.from_orm(model)


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: UUID,
    updates: ModelUpdate,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Update model metadata"""
    model = db.query(Model).filter(Model.id == model_id).first()

    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    for field, value in updates.dict(exclude_unset=True).items():
        setattr(model, field, value)

    model.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(model)

    return ModelResponse.from_orm(model)


@router.post("/{model_id}/deploy")
async def deploy_model(
    model_id: UUID,
    endpoint: Optional[str] = None,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Deploy model to production"""
    model = db.query(Model).filter(Model.id == model_id).first()

    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    if model.status != ModelStatus.TRAINED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model must be trained before deployment",
        )

    # Deploy model (in real implementation, this would deploy to serving infrastructure)
    model.status = ModelStatus.DEPLOYED
    model.deployed_at = datetime.utcnow()
    model.deployment_endpoint = endpoint or f"https://api.mcli-ml.com/models/{model_id}/predict"

    db.commit()

    return {"message": "Model deployed successfully", "endpoint": model.deployment_endpoint}


@router.post("/{model_id}/archive")
async def archive_model(
    model_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Archive a model"""
    model = db.query(Model).filter(Model.id == model_id).first()

    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    model.status = ModelStatus.ARCHIVED
    db.commit()

    return {"message": "Model archived successfully"}


@router.get("/{model_id}/metrics", response_model=ModelMetrics)
@cached(expire=60)
async def get_model_metrics(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get model performance metrics"""
    model = db.query(Model).filter(Model.id == model_id).first()

    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    return ModelMetrics(
        model_id=model.id,
        train_accuracy=model.train_accuracy,
        val_accuracy=model.val_accuracy,
        test_accuracy=model.test_accuracy,
        train_loss=model.train_loss,
        val_loss=model.val_loss,
        test_loss=model.test_loss,
        additional_metrics=model.metrics or {},
    )


@router.post("/{model_id}/retrain")
async def retrain_model(
    model_id: UUID,
    hyperparameters: Optional[dict] = None,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrain an existing model"""
    model = db.query(Model).filter(Model.id == model_id).first()

    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    # Update hyperparameters if provided
    if hyperparameters:
        model.hyperparameters = hyperparameters

    model.status = ModelStatus.TRAINING
    db.commit()

    # Trigger retraining task
    train_model_task.delay(str(model.id), retrain=True)

    return {"message": "Model retraining started", "model_id": str(model.id)}


@router.post("/{model_id}/upload")
async def upload_model_artifact(
    model_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Upload model artifact file"""
    model = db.query(Model).filter(Model.id == model_id).first()

    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    # Save file (in real implementation, save to S3 or similar)
    file_path = f"/models/{model_id}/{file.filename}"

    # Update model path
    model.model_path = file_path
    db.commit()

    return {"message": "Model artifact uploaded successfully", "path": file_path}


@router.delete("/{model_id}")
async def delete_model(
    model_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Delete a model"""
    model = db.query(Model).filter(Model.id == model_id).first()

    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    if model.status == ModelStatus.DEPLOYED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete deployed model. Archive it first.",
        )

    db.delete(model)
    db.commit()

    return {"message": "Model deleted successfully"}


@router.get("/{model_id}/download")
async def download_model(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Download model artifact"""
    model = db.query(Model).filter(Model.id == model_id).first()

    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    if not model.model_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Model artifact not available"
        )

    # In real implementation, return file from storage
    return {"download_url": f"https://storage.mcli-ml.com{model.model_path}", "expires_in": 3600}
